"""Order/checkout pipeline.

Single-transaction flow:
  validate cart → re-check inventory → compute totals → create order + snapshot
  items → atomic conditional stock decrement → payment record → apply coupon →
  clear cart. Any AppError raised before commit rolls everything back.
"""

import secrets
import uuid
from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.cart import Cart
from app.models.coupon import Coupon
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.product import Product, ProductVariant
from app.models.address import Address
from app.models.user import User
from app.schemas.order import CheckoutRequest
from app.services import cart as cart_service
from app.utils.datetime import utcnow


def _new_order_number() -> str:
    stamp = utcnow().strftime("%Y%m%d%H%M%S")
    return f"FS-{stamp}-{secrets.token_hex(2).upper()}"


def _resolve_address(db: Session, user: User, payload: CheckoutRequest, kind: str) -> Address:
    address_id = getattr(payload, f"{kind}_address_id")
    inline = getattr(payload, f"{kind}_address")
    if address_id is not None:
        address = db.get(Address, address_id)
        if address is None or address.user_id != user.id:
            raise AppError(f"Saved {kind} address not found", 404)
        return address
    if inline is not None:
        data = inline.model_dump(exclude_unset=True)
        return _persist_inline(db, user, data)
    raise AppError(f"A {kind} address is required", 400)


def _persist_inline(db: Session, user: User, data: dict) -> Address:
    from app.services.addresses import create_address

    return create_address(db, user, data)


def checkout(db: Session, user: User, payload: CheckoutRequest) -> Order:
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if cart is None or not cart.items:
        raise AppError("Your cart is empty", 400)

    # 1. Validate every line against live inventory
    lines = []
    for item in cart.items:
        product = db.get(Product, item.product_id)
        if product is None or not product.is_active:
            raise AppError("A product in your cart is no longer available", 400)
        variant = db.get(ProductVariant, item.variant_id) if item.variant_id else None
        live_stock = cart_service.stock_available(product, variant)
        if live_stock < item.quantity:
            name = product.name + (f" ({variant.name})" if variant else "")
            raise AppError(f"Not enough stock for {name} — only {live_stock} left", 400)
        lines.append((item, product, variant))

    # 2. Totals
    items_list = list(cart.items)
    totals = cart_service.compute_totals(db, items_list, cart.coupon_code, payload.shipping_method)

    # 3. Addresses (persist inline ones so they land in the address book)
    shipping_address = _resolve_address(db, user, payload, "shipping")
    if payload.billing_same_as_shipping:
        billing_address = shipping_address
    else:
        billing_address = _resolve_address(db, user, payload, "billing")

    # Coupon id (for reporting) when a valid discount applied
    coupon_id = None
    if totals["coupon_code"]:
        coupon_id = db.scalar(select(Coupon.id).where(Coupon.code == totals["coupon_code"]))

    try:
        # 4. Order + snapshot items
        order = Order(
            user_id=user.id,
            order_number=_new_order_number(),
            status="pending" if payload.payment_method == "cod" else "confirmed",
            subtotal=totals["subtotal"],
            discount=totals["discount"],
            shipping_cost=totals["shipping"],
            tax=totals["tax"],
            total=totals["total"],
            coupon_id=coupon_id,
            shipping_address_id=shipping_address.id,
            billing_address_id=billing_address.id,
            shipping_method=payload.shipping_method,
            notes=payload.notes,
        )
        db.add(order)
        db.flush()

        for item, product, variant in lines:
            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    variant_id=item.variant_id,
                    product_name=product.name,
                    variant_name=variant.name if variant else None,
                    sku=variant.sku if variant else product.sku,
                    unit_price=item.unit_price,
                    quantity=item.quantity,
                    total=cart_service.money(Decimal(str(item.unit_price)) * item.quantity),
                )
            )

        # 5. Atomic conditional stock decrement (works on SQLite + PostgreSQL)
        for item, product, variant in lines:
            target = variant if variant is not None else product
            result = db.execute(
                update(type(target))
                .where(type(target).id == target.id, type(target).stock >= item.quantity)
                .values(stock=type(target).stock - item.quantity)
            )
            if result.rowcount == 0:
                raise AppError("Stock changed while checking out — please retry", 409)

        # 6. Payment record (mock provider — always succeeds)
        paid = payload.payment_method == "card_mock"
        db.add(
            Payment(
                order_id=order.id,
                provider="mock",
                method=payload.payment_method,
                amount=Decimal(str(totals["total"])),
                currency="USD",
                status="succeeded" if paid else "pending",
                transaction_id=f"MOCK-{secrets.token_hex(8).upper()}",
            )
        )
        order.payment_status = "paid" if paid else "pending"

        # 7. Coupon usage counter
        if totals["coupon_code"]:
            db.execute(
                update(Coupon)
                .where(Coupon.code == totals["coupon_code"])
                .values(used_count=Coupon.used_count + 1)
            )

        # 8. Clear cart
        for item in items_list:
            db.delete(item)
        cart.coupon_code = None

        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(order)
    return order


def list_orders(db: Session, user: User, page: int = 1, limit: int = 10) -> dict:
    query = select(Order).where(Order.user_id == user.id).order_by(Order.created_at.desc())
    total = len(db.scalars(query).all())
    rows = list(db.scalars(query.offset((page - 1) * limit).limit(limit)).all())
    return {
        "items": rows,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit,
    }


def get_order(db: Session, user: User, order_id: uuid.UUID) -> Order:
    order = db.get(Order, order_id)
    # Owners and admins only
    if order is None or (order.user_id != user.id and user.role.name != "admin"):
        raise AppError("Order not found", 404)
    return order


def order_payload(db: Session, order: Order, detail: bool = False) -> dict:
    payload = {
        "id": order.id,
        "order_number": order.order_number,
        "status": order.status,
        "payment_status": order.payment_status,
        "shipping_status": order.shipping_status,
        "subtotal": float(order.subtotal),
        "discount": float(order.discount),
        "shipping_cost": float(order.shipping_cost),
        "tax": float(order.tax),
        "total": float(order.total),
        "notes": order.notes,
        "created_at": order.created_at,
        "updated_at": order.updated_at,
    }
    if detail:
        payload["items"] = [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "variant_name": item.variant_name,
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total": float(item.total),
            }
            for item in order.items
        ]
        payload["payments"] = [
            {
                "id": payment.id,
                "provider": payment.provider,
                "method": payment.method,
                "amount": float(payment.amount),
                "status": payment.status,
                "transaction_id": payment.transaction_id,
                "created_at": payment.created_at,
            }
            for payment in order.payments
        ]
        # Order ships/bills to addresses (FK only — load them explicitly)
        shipping = db.get(Address, order.shipping_address_id) if order.shipping_address_id else None
        billing = db.get(Address, order.billing_address_id) if order.billing_address_id else None
        payload["shipping_address"] = _address_brief(shipping)
        payload["billing_address"] = _address_brief(billing)
        payload["shipping_method"] = order.shipping_method
    return payload


def _address_brief(address: Address | None) -> dict | None:
    if address is None:
        return None
    return {
        "full_name": address.full_name,
        "phone": address.phone,
        "line1": address.line1,
        "line2": address.line2,
        "city": address.city,
        "state": address.state,
        "postal_code": address.postal_code,
        "country": address.country,
    }

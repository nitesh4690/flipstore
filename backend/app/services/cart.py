"""Shopping cart logic: get-or-create, add/update/remove items, totals with coupons."""

import uuid
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.cart import Cart, CartItem
from app.models.coupon import Coupon
from app.models.product import Product, ProductVariant

# Business rules shared by cart preview and checkout
TAX_RATE = Decimal("0.08")
STANDARD_SHIPPING = Decimal("9.99")
EXPRESS_SHIPPING = Decimal("19.99")
PICKUP_SHIPPING = Decimal("0")
FREE_SHIPPING_THRESHOLD = Decimal("75.00")


def money(value) -> float:
    """Round to 2dp using commercial rounding (matches payment expectations)."""
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_or_create_cart(db: Session, user) -> Cart:
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.flush()
    return cart


def effective_price(product: Product, variant: ProductVariant | None) -> Decimal:
    if variant is not None and variant.price is not None:
        return Decimal(str(variant.price))
    if product.sale_price is not None:
        return Decimal(str(product.sale_price))
    return Decimal(str(product.price))


def stock_available(product: Product, variant: ProductVariant | None) -> int:
    return variant.stock if variant is not None else product.stock


def _load_product(db: Session, product_id: uuid.UUID, variant_id: uuid.UUID | None):
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        raise AppError("Product not found", 404)
    variant = None
    if variant_id is not None:
        variant = db.get(ProductVariant, variant_id)
        if variant is None or variant.product_id != product.id:
            raise AppError("Variant does not belong to this product", 400)
    return product, variant


def add_item(db: Session, user, product_id, variant_id, quantity: int) -> Cart:
    product, variant = _load_product(db, product_id, variant_id)
    cart = get_or_create_cart(db, user)

    stock = stock_available(product, variant)
    if stock <= 0:
        raise AppError("This product is out of stock", 400)

    existing = db.scalar(
        select(CartItem).where(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product.id,
            CartItem.variant_id == variant_id if variant_id is not None else CartItem.variant_id.is_(None),
        )
    )
    new_quantity = (existing.quantity if existing else 0) + quantity
    if new_quantity > stock:
        raise AppError(f"Only {stock} unit(s) available", 400)

    if existing:
        existing.quantity = new_quantity
    else:
        db.add(
            CartItem(
                cart_id=cart.id,
                product_id=product.id,
                variant_id=variant_id,
                unit_price=float(effective_price(product, variant)),
                quantity=new_quantity,
            )
        )
    db.flush()
    return cart


def update_item(db: Session, user, item_id: uuid.UUID, quantity: int) -> Cart:
    item = db.get(CartItem, item_id)
    cart = _user_cart(db, user)
    if item is None or item.cart_id != cart.id:
        raise AppError("Cart item not found", 404)

    product, variant = _load_product(db, item.product_id, item.variant_id)
    stock = stock_available(product, variant)
    if quantity > stock:
        raise AppError(f"Only {stock} unit(s) available", 400)

    item.quantity = quantity
    db.flush()
    return cart


def remove_item(db: Session, user, item_id: uuid.UUID) -> Cart:
    cart = _user_cart(db, user)
    result = db.execute(delete(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id))
    if result.rowcount == 0:
        raise AppError("Cart item not found", 404)
    db.flush()
    return cart


def clear_cart(db: Session, user) -> Cart:
    cart = _user_cart(db, user)
    db.execute(delete(CartItem).where(CartItem.cart_id == cart.id))
    cart.coupon_code = None
    db.flush()
    return cart


def _user_cart(db: Session, user) -> Cart:
    cart = db.scalar(select(Cart).where(Cart.user_id == user.id))
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.flush()
    return cart


def apply_coupon(db: Session, user, code: str | None) -> Cart:
    cart = _user_cart(db, user)
    if code:
        subtotal = cart_subtotal(db, cart)
        coupon = validate_coupon(db, code, subtotal)
        cart.coupon_code = coupon.code
    else:
        cart.coupon_code = None
    db.flush()
    return cart


def validate_coupon(db: Session, code: str, subtotal: float) -> Coupon:
    from app.utils.datetime import utcnow

    coupon = db.scalar(select(Coupon).where(Coupon.code == code.strip().upper()))
    if coupon is None:
        raise AppError("Invalid coupon code", 400)
    if not coupon.is_active:
        raise AppError("This coupon is no longer active", 400)
    now = utcnow()
    if coupon.starts_at is not None and now < coupon.starts_at:
        raise AppError("This coupon is not active yet", 400)
    if coupon.expires_at is not None and now > coupon.expires_at:
        raise AppError("This coupon has expired", 400)
    if coupon.max_uses and coupon.used_count >= coupon.max_uses:
        raise AppError("This coupon has reached its usage limit", 400)
    if subtotal < float(coupon.min_order_amount or 0):
        raise AppError(
            f"A minimum order of {money(coupon.min_order_amount)} is required for this coupon",
            400,
        )
    return coupon


def coupon_discount(db: Session, coupon_code: str | None, subtotal: float) -> tuple[float, str | None]:
    """Returns (discount_amount, valid_coupon_code). Invalid codes count as zero."""
    if not coupon_code:
        return 0.0, None
    try:
        coupon = validate_coupon(db, coupon_code, subtotal)
    except AppError:
        return 0.0, None
    if coupon.discount_type == "percentage":
        amount = Decimal(str(subtotal)) * Decimal(str(coupon.value)) / Decimal("100")
    else:
        amount = Decimal(str(coupon.value))
    if amount > Decimal(str(subtotal)):
        amount = Decimal(str(subtotal))
    return money(amount), coupon.code


def shipping_cost(method: str, after_discount: Decimal) -> Decimal:
    if method == "pickup":
        return PICKUP_SHIPPING
    if method == "express":
        return EXPRESS_SHIPPING
    # standard — free over threshold (measured after discount)
    if after_discount >= FREE_SHIPPING_THRESHOLD:
        return Decimal("0")
    return STANDARD_SHIPPING


def compute_totals(db: Session, items: list[CartItem], coupon_code: str | None, method: str = "standard") -> dict:
    subtotal_d = Decimal("0")
    for item in items:
        subtotal_d += Decimal(str(item.unit_price)) * item.quantity
    subtotal = money(subtotal_d)

    discount, valid_code = coupon_discount(db, coupon_code, subtotal)
    after_discount = Decimal(str(subtotal)) - Decimal(str(discount))

    ship = shipping_cost(method, after_discount)
    tax = money(Decimal(str((after_discount) * TAX_RATE)))
    total = money(after_discount + Decimal(str(ship)) + Decimal(str(tax)))

    return {
        "subtotal": subtotal,
        "discount": discount,
        "shipping": float(ship),
        "tax": tax,
        "total": total,
        "shipping_method": method,
        "coupon_code": valid_code,
        "free_shipping_threshold_met": (after_discount >= FREE_SHIPPING_THRESHOLD) and method == "standard",
    }


def cart_items_payload(db: Session, cart: Cart) -> list[dict]:
    from app.models.product import Product, ProductVariant

    payloads = []
    for item in sorted(cart.items, key=lambda i: i.created_at):
        product = db.get(Product, item.product_id)
        variant = db.get(ProductVariant, item.variant_id) if item.variant_id else None
        if product is None:
            continue
        stock = stock_available(product, variant)
        image = product.primary_image_url
        payloads.append(
            {
                "id": item.id,
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "name": product.name,
                "slug": product.slug,
                "image": image,
                "variant_name": variant.name if variant else None,
                "unit_price": float(item.unit_price),
                "quantity": item.quantity,
                "line_total": money(Decimal(str(item.unit_price)) * item.quantity),
                "stock_available": stock,
                "in_stock": stock > 0,
                "created_at": item.created_at,
            }
        )
    return payloads


def cart_subtotal(db: Session, cart: Cart) -> float:
    return money(sum(Decimal(str(i.unit_price)) * i.quantity for i in cart.items))


def cart_payload(db: Session, cart: Cart, method: str = "standard") -> dict:
    items = cart_items_payload(db, cart)
    subtotal = money(sum(Decimal(str(i["line_total"])) for i in items))
    discount, valid_code = coupon_discount(db, cart.coupon_code, subtotal)
    after_discount = Decimal(str(subtotal)) - Decimal(str(discount))
    ship = shipping_cost(method, after_discount)
    tax = money(after_discount * TAX_RATE)
    total = money(after_discount + Decimal(str(ship)) + Decimal(str(tax)))
    return {
        "items": items,
        "totals": {
            "subtotal": subtotal,
            "discount": discount,
            "shipping": float(ship),
            "tax": tax,
            "total": total,
            "shipping_method": method,
            "coupon_code": valid_code,
            "free_shipping_threshold_met": (after_discount >= FREE_SHIPPING_THRESHOLD)
            and method == "standard",
        },
        "item_count": sum(i["quantity"] for i in items),
    }

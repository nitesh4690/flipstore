"""Admin dashboard business logic: stats, order management, customers.

All endpoints here are guarded by get_current_admin — these functions assume
the caller is already authorized.
"""

import math
import uuid
from datetime import timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppError
from app.models.order import Order
from app.models.product import Product
from app.models.role import Role
from app.models.user import User
from app.schemas.admin import ORDER_STATUSES, AdminOrderUpdate
from app.services import orders as order_service
from app.utils.datetime import as_utc, utcnow

LOW_STOCK_THRESHOLD = 5
RECENT_WINDOW_DAYS = 7


# ---------------------------------------------------------------------------
# Shared payload helpers
# ---------------------------------------------------------------------------
def order_row(db: Session, order: Order, detail: bool = False) -> dict:
    """Order payload + embedded customer summary."""
    payload = order_service.order_payload(db, order, detail=detail)
    user = order.user  # selectinloaded in list queries; lazy-loads otherwise
    payload["customer"] = (
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        if user is not None
        else None
    )
    return payload


def _low_stock_row(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "sku": product.sku,
        "stock": product.stock,
        "price": float(product.price),
    }


def _customer_row(user: User, order_count: int, total_spent: float) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone": user.phone,
        "is_active": user.is_active,
        "created_at": user.created_at,
        "order_count": int(order_count or 0),
        "total_spent": round(float(total_spent or 0), 2),
    }


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------
def dashboard_stats(db: Session) -> dict:
    order_count = db.scalar(select(func.count(Order.id))) or 0
    revenue = (
        db.scalar(
            select(func.coalesce(func.sum(Order.total), 0)).where(Order.status != "cancelled")
        )
        or 0
    )

    by_status = {name: 0 for name in ORDER_STATUSES}
    for name, count in db.execute(
        select(Order.status, func.count(Order.id)).group_by(Order.status)
    ).all():
        by_status[name] = count

    customer_count = (
        db.scalar(
            select(func.count(User.id))
            .join(Role, User.role_id == Role.id)
            .where(Role.name == "customer")
        )
        or 0
    )
    product_count = db.scalar(select(func.count(Product.id))) or 0

    low_stock_count = (
        db.scalar(
            select(func.count(Product.id)).where(
                Product.is_active.is_(True), Product.stock <= LOW_STOCK_THRESHOLD
            )
        )
        or 0
    )
    low_stock = db.scalars(
        select(Product)
        .where(Product.is_active.is_(True), Product.stock <= LOW_STOCK_THRESHOLD)
        .order_by(Product.stock.asc())
        .limit(8)
    ).all()

    # 7-day revenue series — bucketed in Python so SQLite and PostgreSQL agree
    today = as_utc(utcnow()).date()
    start = today - timedelta(days=RECENT_WINDOW_DAYS - 1)
    buckets: dict = {start + timedelta(days=i): 0.0 for i in range(RECENT_WINDOW_DAYS)}
    for order in db.scalars(select(Order).where(Order.status != "cancelled")).all():
        day = as_utc(order.created_at).date()
        if day in buckets:
            buckets[day] += float(order.total)
    revenue_series = [
        {"date": day.isoformat(), "revenue": round(buckets[day], 2)}
        for day in sorted(buckets)
    ]

    recent = db.scalars(
        select(Order)
        .options(selectinload(Order.user))
        .order_by(Order.created_at.desc())
        .limit(5)
    ).all()

    return {
        "revenue": round(float(revenue), 2),
        "order_count": order_count,
        "customer_count": customer_count,
        "product_count": product_count,
        "low_stock_count": low_stock_count,
        "low_stock": [_low_stock_row(p) for p in low_stock],
        "orders_by_status": by_status,
        "revenue_last_7_days": revenue_series,
        "recent_orders": [order_row(db, order) for order in recent],
    }


# ---------------------------------------------------------------------------
# Orders (all customers)
# ---------------------------------------------------------------------------
def list_admin_orders(
    db: Session,
    *,
    status: str | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 10,
) -> dict:
    if status is not None and status not in ORDER_STATUSES:
        raise AppError(f"Invalid order status '{status}'", status_code=400)

    query = select(Order).join(User, Order.user_id == User.id)
    if status:
        query = query.where(Order.status == status)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Order.order_number.ilike(pattern),
                User.email.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(
        query.options(selectinload(Order.user))
        .order_by(Order.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return {
        "items": [order_row(db, order) for order in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if total else 0,
    }


def get_admin_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise AppError("Order not found", status_code=404)
    return order


def update_order(db: Session, order: Order, payload: AdminOrderUpdate) -> Order:
    """Apply provided lifecycle fields (values already validated by Pydantic)."""
    labels = {
        "status": "Order status",
        "payment_status": "Payment status",
        "shipping_status": "Shipping status",
    }
    changes: dict[str, tuple[str, str]] = {}
    for field, value in payload.model_dump(exclude_none=True).items():
        current = getattr(order, field)
        if current != value:
            changes[labels.get(field, field)] = (current, value)
            setattr(order, field, value)
    db.add(order)
    db.commit()
    db.refresh(order)

    # Status-change email (delivery failures are logged, never raised)
    if changes:
        buyer = order.user
        if buyer is not None:
            from app.services import email as email_service

            email_service.send_order_status_update(
                to=buyer.email,
                first_name=buyer.first_name,
                order_number=order.order_number,
                changes=changes,
            )
    return order


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
def _customer_subqueries():
    order_count = (
        select(func.count(Order.id)).where(Order.user_id == User.id).correlate(User).scalar_subquery()
    )
    total_spent = (
        select(func.coalesce(func.sum(Order.total), 0))
        .where(Order.user_id == User.id, Order.status != "cancelled")
        .correlate(User)
        .scalar_subquery()
    )
    return order_count, total_spent


def list_customers(
    db: Session,
    *,
    search: str | None = None,
    page: int = 1,
    limit: int = 10,
) -> dict:
    order_count, total_spent = _customer_subqueries()

    base = select(User).join(Role, User.role_id == Role.id).where(Role.name == "customer")
    if search:
        pattern = f"%{search.strip()}%"
        base = base.where(
            or_(
                User.email.ilike(pattern),
                User.first_name.ilike(pattern),
                User.last_name.ilike(pattern),
            )
        )

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.add_columns(order_count.label("order_count"), total_spent.label("total_spent"))
        .order_by(User.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return {
        "items": [_customer_row(user, count, spent) for user, count, spent in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if total else 0,
    }


def get_customer_detail(db: Session, customer_id: uuid.UUID) -> dict:
    user = db.get(User, customer_id)
    if user is None:
        raise AppError("Customer not found", status_code=404)

    order_count = db.scalar(select(func.count(Order.id)).where(Order.user_id == user.id)) or 0
    total_spent = (
        db.scalar(
            select(func.coalesce(func.sum(Order.total), 0)).where(
                Order.user_id == user.id, Order.status != "cancelled"
            )
        )
        or 0
    )
    recent = db.scalars(
        select(Order)
        .where(Order.user_id == user.id)
        .options(selectinload(Order.user))
        .order_by(Order.created_at.desc())
        .limit(5)
    ).all()

    row = _customer_row(user, order_count, total_spent)
    row["recent_orders"] = [order_row(db, order) for order in recent]
    return row

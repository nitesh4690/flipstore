"""Coupon management (admin CRUD).

Validation and discount math against carts lives in services/cart.py;
order creation snapshots/discounts in services/orders.py.
"""

import math
import uuid

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.coupon import Coupon
from app.models.order import Order
from app.schemas.coupon import CouponCreate


def coupon_payload(coupon: Coupon) -> dict:
    return {
        "id": coupon.id,
        "code": coupon.code,
        "discount_type": coupon.discount_type,
        "value": float(coupon.value),
        "min_order_amount": float(coupon.min_order_amount or 0),
        "max_uses": coupon.max_uses,
        "used_count": coupon.used_count,
        "is_active": coupon.is_active,
        "starts_at": coupon.starts_at,
        "expires_at": coupon.expires_at,
        "created_at": coupon.created_at,
        "updated_at": coupon.updated_at,
    }


def list_coupons(
    db: Session,
    *,
    search: str | None = None,
    page: int = 1,
    limit: int = 10,
) -> dict:
    base = select(Coupon)
    if search:
        pattern = f"%{search.strip()}%"
        base = base.where(Coupon.code.ilike(pattern))

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.order_by(Coupon.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return {
        "items": [coupon_payload(coupon) for coupon in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if total else 0,
    }


def get_coupon(db: Session, coupon_id: uuid.UUID) -> Coupon:
    coupon = db.get(Coupon, coupon_id)
    if coupon is None:
        raise AppError("Coupon not found", status_code=404)
    return coupon


def _code_taken(db: Session, code: str, exclude_id: uuid.UUID | None = None) -> bool:
    query = select(Coupon.id).where(Coupon.code == code)
    if exclude_id is not None:
        query = query.where(Coupon.id != exclude_id)
    return db.scalar(query) is not None


def create_coupon(db: Session, payload: CouponCreate) -> Coupon:
    if _code_taken(db, payload.code):
        raise AppError(f"Coupon {payload.code} already exists", status_code=409)

    coupon = Coupon(**payload.model_dump())
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


def update_coupon(db: Session, coupon: Coupon, payload: CouponCreate) -> Coupon:
    if payload.code != coupon.code and _code_taken(db, payload.code, exclude_id=coupon.id):
        raise AppError(f"Coupon {payload.code} already exists", status_code=409)

    for field, value in payload.model_dump().items():
        setattr(coupon, field, value)
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon


def delete_coupon(db: Session, coupon: Coupon) -> None:
    # Historical orders keep their discount; only the FK reference is cleared.
    db.execute(
        update(Order).where(Order.coupon_id == coupon.id).values(coupon_id=None)
    )
    db.delete(coupon)
    db.commit()

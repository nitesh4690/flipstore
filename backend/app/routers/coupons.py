"""Coupon management endpoints (admin only)."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_admin, get_db
from app.schemas.coupon import CouponCreate
from app.services import coupons as coupon_service
from app.utils.responses import ok

router = APIRouter(prefix="/coupons", tags=["coupons"])


@router.get("", response_model=dict)
def list_coupons(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    _: object = Depends(get_current_admin),
):
    result = coupon_service.list_coupons(db, search=search, page=page, limit=limit)
    return ok(result)


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_coupon(
    payload: CouponCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    coupon = coupon_service.create_coupon(db, payload)
    return ok(coupon_service.coupon_payload(coupon), message="Coupon created")


@router.patch("/{coupon_id}", response_model=dict)
def update_coupon(
    coupon_id: uuid.UUID,
    payload: CouponCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    coupon = coupon_service.get_coupon(db, coupon_id)
    updated = coupon_service.update_coupon(db, coupon, payload)
    return ok(coupon_service.coupon_payload(updated), message="Coupon updated")


@router.delete("/{coupon_id}", response_model=dict)
def delete_coupon(
    coupon_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    coupon = coupon_service.get_coupon(db, coupon_id)
    coupon_service.delete_coupon(db, coupon)
    return ok(None, message="Coupon deleted")

"""Cart endpoints — /api/cart"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_active_user, get_db
from app.schemas.cart import CartItemAdd, CartItemUpdate, CartOut, CouponApply
from app.services import cart as cart_service
from app.utils.responses import ok

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get("", response_model=dict)
def get_cart(
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    cart = cart_service.get_or_create_cart(db, user)
    db.commit()
    return ok(data=cart_service.cart_payload(db, cart))


@router.post("/items", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_item(
    payload: CartItemAdd,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    cart = cart_service.add_item(db, user, payload.product_id, payload.variant_id, payload.quantity)
    db.commit()
    return ok(message="Item added to cart", data=cart_service.cart_payload(db, cart))


@router.put("/items/{item_id}", response_model=dict)
def update_item(
    item_id: uuid.UUID,
    payload: CartItemUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    cart = cart_service.update_item(db, user, item_id, payload.quantity)
    db.commit()
    return ok(message="Cart updated", data=cart_service.cart_payload(db, cart))


@router.delete("/items/{item_id}", response_model=dict)
def remove_item(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    cart = cart_service.remove_item(db, user, item_id)
    db.commit()
    return ok(message="Item removed", data=cart_service.cart_payload(db, cart))


@router.delete("", response_model=dict)
def clear_cart(
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    cart = cart_service.clear_cart(db, user)
    db.commit()
    return ok(message="Cart cleared", data=cart_service.cart_payload(db, cart))


@router.put("/coupon", response_model=dict)
def set_coupon(
    payload: CouponApply,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    cart = cart_service.apply_coupon(db, user, payload.code)
    db.commit()
    message = f"Coupon {cart.coupon_code} applied" if cart.coupon_code else "Coupon removed"
    return ok(message=message, data=cart_service.cart_payload(db, cart))

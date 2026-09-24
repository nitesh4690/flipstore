"""Wishlist endpoints — /api/wishlist"""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_active_user, get_db
from app.schemas.wishlist import WishlistToggle
from app.services import wishlist as wishlist_service
from app.utils.responses import ok

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("", response_model=dict)
def get_wishlist(
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    return ok(data={"items": wishlist_service.list_items(db, user)})


@router.post("/items", response_model=dict, status_code=status.HTTP_201_CREATED)
def add_item(
    payload: WishlistToggle,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    added = wishlist_service.add_item(db, user, payload.product_id)
    db.commit()
    return ok(
        message="Added to wishlist" if added else "Already in wishlist",
        data={"items": wishlist_service.list_items(db, user)},
    )


@router.delete("/items/{product_id}", response_model=dict)
def remove_item(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    removed = wishlist_service.remove_item(db, user, product_id)
    db.commit()
    if not removed:
        return ok(message="Not in wishlist", data={"items": wishlist_service.list_items(db, user)})
    return ok(message="Removed from wishlist", data={"items": wishlist_service.list_items(db, user)})

"""Wishlist logic: add, remove, toggle, list with product snapshots."""

import uuid

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.wishlist import Wishlist, WishlistItem


def get_or_create_wishlist(db: Session, user) -> Wishlist:
    wishlist = db.scalar(select(Wishlist).where(Wishlist.user_id == user.id))
    if wishlist is None:
        wishlist = Wishlist(user_id=user.id)
        db.add(wishlist)
        db.flush()
    return wishlist


def list_items(db: Session, user) -> list[dict]:
    from app.services.products import serialize_item

    wishlist = get_or_create_wishlist(db, user)
    rows = db.scalars(
        select(WishlistItem).where(WishlistItem.wishlist_id == wishlist.id)
    ).all()
    payloads = []
    for row in rows:
        product = db.get(Product, row.product_id)
        if product is None or not product.is_active:
            continue
        payloads.append({"id": row.id, "product": serialize_item(product)})
    return payloads


def add_item(db: Session, user, product_id: uuid.UUID) -> bool:
    """Returns True if added, False if already present."""
    product = db.get(Product, product_id)
    if product is None or not product.is_active:
        from app.core.exceptions import AppError

        raise AppError("Product not found", 404)
    wishlist = get_or_create_wishlist(db, user)
    existing = db.scalar(
        select(WishlistItem).where(
            WishlistItem.wishlist_id == wishlist.id,
            WishlistItem.product_id == product_id,
        )
    )
    if existing is not None:
        return False
    db.add(WishlistItem(wishlist_id=wishlist.id, product_id=product_id))
    db.flush()
    return True


def remove_item(db: Session, user, product_id: uuid.UUID) -> bool:
    """Returns True if removed, False if it wasn't present."""
    wishlist = get_or_create_wishlist(db, user)
    result = db.execute(
        delete(WishlistItem).where(
            WishlistItem.wishlist_id == wishlist.id,
            WishlistItem.product_id == product_id,
        )
    )
    db.flush()
    return result.rowcount > 0


def contains(db: Session, user, product_id: uuid.UUID) -> bool:
    wishlist = db.scalar(select(Wishlist).where(Wishlist.user_id == user.id))
    if wishlist is None:
        return False
    item = db.scalar(
        select(WishlistItem).where(
            WishlistItem.wishlist_id == wishlist.id,
            WishlistItem.product_id == product_id,
        )
    )
    return item is not None

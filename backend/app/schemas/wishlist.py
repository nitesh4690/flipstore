"""Wishlist schemas."""

import uuid

from pydantic import BaseModel, ConfigDict

from app.schemas.product import ProductListItem


class WishlistItemOut(BaseModel):
    id: uuid.UUID
    product: ProductListItem


class WishlistToggle(BaseModel):
    product_id: uuid.UUID

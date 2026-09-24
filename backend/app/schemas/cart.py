"""Shopping cart schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CartItemAdd(BaseModel):
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    quantity: int = Field(default=1, ge=1, le=99)


class CartItemUpdate(BaseModel):
    quantity: int = Field(ge=1, le=99)


class CouponApply(BaseModel):
    code: str | None = Field(default=None, max_length=50)


class CartItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: uuid.UUID | None = None
    name: str
    slug: str
    image: str | None = None
    variant_name: str | None = None
    unit_price: float
    quantity: int
    line_total: float
    stock_available: int
    in_stock: bool
    created_at: datetime | None = None


class CartTotals(BaseModel):
    subtotal: float = 0
    discount: float = 0
    shipping: float = 0
    tax: float = 0
    total: float = 0
    shipping_method: str = "standard"
    coupon_code: str | None = None
    free_shipping_threshold_met: bool = False


class CartOut(BaseModel):
    items: list[CartItemOut] = []
    totals: CartTotals = CartTotals()
    item_count: int = 0

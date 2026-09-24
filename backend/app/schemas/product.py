"""Pydantic schemas for products, images and variants."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Nested outputs
# ---------------------------------------------------------------------------
class ProductImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    url: str
    alt_text: str | None = None
    position: int = 0
    is_primary: bool = False


class ProductVariantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    sku: str
    name: str | None = None
    attributes: dict = {}
    price: float | None = None
    stock: int = 0


# ---------------------------------------------------------------------------
# List item (lightweight — used in grids)
# ---------------------------------------------------------------------------
class ProductListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    sku: str
    price: float
    sale_price: float | None = None
    stock: int = 0
    rating: float = 0
    rating_count: int = 0
    is_active: bool = True
    is_featured: bool = False

    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    category_name: str | None = None
    brand_name: str | None = None
    primary_image_url: str | None = None
    effective_price: float
    discount_percent: int = 0
    in_stock: bool = True

    created_at: datetime


# ---------------------------------------------------------------------------
# Detail (full)
# ---------------------------------------------------------------------------
class ProductDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str = ""
    sku: str
    price: float
    sale_price: float | None = None
    stock: int = 0
    rating: float = 0
    rating_count: int = 0
    is_active: bool = True
    is_featured: bool = False

    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    category_name: str | None = None
    brand_name: str | None = None
    effective_price: float
    discount_percent: int = 0
    in_stock: bool = True

    images: list[ProductImageOut] = []
    variants: list[ProductVariantOut] = []

    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Pagination envelope
# ---------------------------------------------------------------------------
class PaginatedProducts(BaseModel):
    items: list[ProductListItem]
    page: int = 1
    limit: int = 12
    total: int = 0
    total_pages: int = 0


# ---------------------------------------------------------------------------
# Admin write payloads
# ---------------------------------------------------------------------------
class ProductImageIn(BaseModel):
    url: str = Field(max_length=500)
    alt_text: str | None = Field(default=None, max_length=255)
    position: int = Field(default=0, ge=0)
    is_primary: bool = False


class ProductVariantIn(BaseModel):
    sku: str | None = Field(default=None, max_length=100)
    name: str | None = Field(default=None, max_length=120)
    attributes: dict = {}
    price: float | None = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    description: str = ""
    sku: str | None = Field(default=None, max_length=100)
    price: float = Field(gt=0)
    sale_price: float | None = Field(default=None, ge=0)
    stock: int = Field(default=0, ge=0)
    is_active: bool = True
    is_featured: bool = False
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    images: list[ProductImageIn] = []
    variants: list[ProductVariantIn] = []

    @field_validator("sale_price")
    @classmethod
    def _sale_below_price(cls, value: float | None, info) -> float | None:
        price = info.data.get("price")
        if value is not None and price is not None and value > price:
            raise ValueError("sale_price cannot be greater than price")
        return value


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    sku: str | None = Field(default=None, max_length=100)
    price: float | None = Field(default=None, gt=0)
    sale_price: float | None = Field(default=None, ge=0)
    stock: int | None = Field(default=None, ge=0)
    is_active: bool | None = None
    is_featured: bool | None = None
    category_id: uuid.UUID | None = None
    brand_id: uuid.UUID | None = None
    images: list[ProductImageIn] | None = None
    variants: list[ProductVariantIn] | None = None

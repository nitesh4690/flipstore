"""Pydantic schemas for brands."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BrandCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True


class BrandUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    logo_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class BrandOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    logo_url: str | None = None
    is_active: bool = True
    product_count: int = 0
    created_at: datetime

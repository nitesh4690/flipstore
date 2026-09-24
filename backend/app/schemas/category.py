"""Pydantic schemas for categories."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool = True
    parent_id: uuid.UUID | None = None


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    slug: str | None = Field(default=None, max_length=120)
    description: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    parent_id: uuid.UUID | None = None


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    image_url: str | None = None
    is_active: bool = True
    parent_id: uuid.UUID | None = None
    product_count: int = 0
    created_at: datetime


class CategoryTreeNode(CategoryOut):
    children: list["CategoryTreeNode"] = []

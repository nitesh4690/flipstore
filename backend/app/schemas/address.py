"""Address schemas (used by account + checkout)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class AddressPayload(BaseModel):
    label: str = Field(default="Home", max_length=50)
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=30)
    line1: str = Field(min_length=1, max_length=255)
    line2: str | None = Field(default=None, max_length=255)
    city: str = Field(min_length=1, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    postal_code: str = Field(min_length=1, max_length=20)
    country: str = Field(default="India", max_length=100)
    is_default_shipping: bool = False
    is_default_billing: bool = False


class AddressUpdate(AddressPayload):
    label: str | None = Field(default=None, max_length=50)
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    line1: str | None = Field(default=None, min_length=1, max_length=255)
    city: str | None = Field(default=None, min_length=1, max_length=100)
    postal_code: str | None = Field(default=None, min_length=1, max_length=20)
    country: str | None = Field(default=None, max_length=100)


class AddressOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    label: str
    full_name: str
    phone: str | None = None
    line1: str
    line2: str | None = None
    city: str
    state: str | None = None
    postal_code: str
    country: str
    is_default_shipping: bool = False
    is_default_billing: bool = False
    created_at: datetime

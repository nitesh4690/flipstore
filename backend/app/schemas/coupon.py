"""Coupon admin schemas (validation/application lives in services/cart.py)."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

DISCOUNT_TYPES = ("percentage", "fixed")


class CouponCreate(BaseModel):
    """Full coupon payload — used for both create and admin PATCH updates."""

    code: str = Field(max_length=50)
    discount_type: str = "percentage"
    value: float = Field(gt=0)
    min_order_amount: float = Field(default=0, ge=0)
    max_uses: int | None = Field(default=None, ge=1)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    is_active: bool = True

    @field_validator("code")
    @classmethod
    def _normalize_code(cls, value: str) -> str:
        code = value.strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{3,50}", code):
            raise ValueError("Code must be 3–50 letters or numbers (A–Z, 0–9)")
        return code

    @field_validator("discount_type")
    @classmethod
    def _check_type(cls, value: str) -> str:
        if value not in DISCOUNT_TYPES:
            raise ValueError(f"discount_type must be one of {DISCOUNT_TYPES}")
        return value

    @model_validator(mode="after")
    def _cross_validate(self):
        if self.discount_type == "percentage" and self.value > 100:
            raise ValueError("Percentage discounts cannot exceed 100")
        if self.starts_at is not None and self.expires_at is not None:
            if self.expires_at <= self.starts_at:
                raise ValueError("expires_at must be after starts_at")
        return self

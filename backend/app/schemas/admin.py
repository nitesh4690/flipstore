"""Pydantic schemas for admin dashboard endpoints."""

from pydantic import BaseModel, Field, field_validator, model_validator

ORDER_STATUSES = ("pending", "confirmed", "processing", "shipped", "delivered", "cancelled")
PAYMENT_STATUSES = ("pending", "paid", "failed", "refunded")
SHIPPING_STATUSES = ("pending", "shipped", "delivered", "returned")


class AdminOrderUpdate(BaseModel):
    """Partial update for order lifecycle fields (all optional, >= 1 required)."""

    status: str | None = Field(default=None)
    payment_status: str | None = Field(default=None)
    shipping_status: str | None = Field(default=None)

    @field_validator("status")
    @classmethod
    def _valid_status(cls, value: str | None) -> str | None:
        if value is not None and value not in ORDER_STATUSES:
            raise ValueError(f"status must be one of {ORDER_STATUSES}")
        return value

    @field_validator("payment_status")
    @classmethod
    def _valid_payment_status(cls, value: str | None) -> str | None:
        if value is not None and value not in PAYMENT_STATUSES:
            raise ValueError(f"payment_status must be one of {PAYMENT_STATUSES}")
        return value

    @field_validator("shipping_status")
    @classmethod
    def _valid_shipping_status(cls, value: str | None) -> str | None:
        if value is not None and value not in SHIPPING_STATUSES:
            raise ValueError(f"shipping_status must be one of {SHIPPING_STATUSES}")
        return value

    @model_validator(mode="after")
    def _require_at_least_one(self) -> "AdminOrderUpdate":
        if self.status is None and self.payment_status is None and self.shipping_status is None:
            raise ValueError("Provide at least one of status, payment_status, shipping_status")
        return self

"""Order / checkout schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.address import AddressPayload

SHIPPING_METHODS = ("standard", "express", "pickup")
PAYMENT_METHODS = ("card_mock", "cod")


class CardDetails(BaseModel):
    """Card fields sent by the checkout payment step (mock gateway)."""

    number: str = Field(min_length=12, max_length=25)
    expiry: str = Field(pattern=r"^\d{2}/\d{2}$", description="MM/YY")
    cvc: str = Field(pattern=r"^\d{3,4}$")
    holder_name: str | None = Field(default=None, max_length=120)


class CheckoutRequest(BaseModel):
    shipping_method: str = Field(default="standard")
    payment_method: str = Field(default="card_mock")
    billing_same_as_shipping: bool = True
    notes: str | None = Field(default=None, max_length=1000)
    card: CardDetails | None = Field(
        default=None,
        description="Required in the UI for card payments; omitted = legacy mock approval",
    )

    # Provide either a saved address id OR an inline address
    shipping_address_id: uuid.UUID | None = None
    shipping_address: AddressPayload | None = None

    billing_address_id: uuid.UUID | None = None
    billing_address: AddressPayload | None = None

    @model_validator(mode="after")
    def _validate(self):
        if self.shipping_method not in SHIPPING_METHODS:
            raise ValueError(f"shipping_method must be one of {SHIPPING_METHODS}")
        if self.payment_method not in PAYMENT_METHODS:
            raise ValueError(f"payment_method must be one of {PAYMENT_METHODS}")
        if self.shipping_address_id is None and self.shipping_address is None:
            raise ValueError("A shipping address (id or inline) is required")
        if not self.billing_same_as_shipping and self.billing_address_id is None and self.billing_address is None:
            raise ValueError("A billing address (id or inline) is required, or set billing_same_as_shipping")
        return self


class OrderItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID | None = None
    product_name: str
    variant_name: str | None = None
    sku: str
    quantity: int
    unit_price: float
    total: float


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    method: str | None = None
    amount: float
    status: str
    transaction_id: str | None = None
    created_at: datetime


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_number: str
    status: str
    payment_status: str
    shipping_status: str
    subtotal: float
    discount: float
    shipping_cost: float
    tax: float
    total: float
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class OrderDetail(OrderOut):
    items: list[OrderItemOut] = []
    payments: list[PaymentOut] = []


class OrderListOut(BaseModel):
    items: list[OrderOut] = []
    total: int = 0
    page: int = 1
    limit: int = 10
    total_pages: int = 0

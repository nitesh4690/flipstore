"""Order and OrderItem models (prices are snapshots at purchase time)."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, new_uuid


class Order(Base, TimestampMixin):
    __tablename__ = "orders"
    __table_args__ = (
        Index("ix_orders_user_created", "user_id", "created_at"),
        CheckConstraint("subtotal >= 0", name="ck_orders_subtotal_nonneg"),
        CheckConstraint("total >= 0", name="ck_orders_total_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    order_number: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    # Lifecycle statuses (strings for portability; validated in Pydantic schemas)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending", index=True
    )  # pending | confirmed | processing | shipped | delivered | cancelled
    payment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending", index=True
    )  # pending | paid | failed | refunded
    shipping_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )  # pending | shipped | delivered | returned

    # Money breakdown
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    discount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    shipping_cost: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    tax: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")
    total: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0, server_default="0")

    coupon_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True, index=True
    )
    shipping_method: Mapped[str] = mapped_column(
        String(20), nullable=False, default="standard", server_default="standard"
    )  # standard | express | pickup
    shipping_address_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("addresses.id", ondelete="SET NULL"), nullable=True
    )
    billing_address_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("addresses.id", ondelete="SET NULL"), nullable=True
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships -------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="orders")  # noqa: F821
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(  # noqa: F821
        "Payment", back_populates="order", cascade="all, delete-orphan"
    )
    coupon: Mapped["Coupon | None"] = relationship("Coupon")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Order {self.order_number} ({self.status})>"


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_order_items_unit_price_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # SET NULL: keep historical orders even if the catalog entry is removed
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True
    )

    # Immutable snapshots taken at checkout
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)

    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    total: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product | None"] = relationship("Product")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover
        return f"<OrderItem {self.sku} x{self.quantity}>"

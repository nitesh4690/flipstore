"""Shopping cart models (one cart per user, guest carts can attach later)."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, new_uuid


class Cart(Base, TimestampMixin):
    __tablename__ = "carts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    # Nullable + unique: one cart per user; guest carts (user_id = NULL) allowed.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, unique=True, index=True
    )
    # Applied discount code (validated against the coupons table on totals/checkout)
    coupon_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user: Mapped["User | None"] = relationship("User", back_populates="cart")  # noqa: F821
    items: Mapped[list["CartItem"]] = relationship(
        "CartItem", back_populates="cart", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Cart {self.id}>"


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint("cart_id", "product_id", "variant_id", name="uq_cart_items_cart_product_variant"),
        CheckConstraint("quantity > 0", name="ck_cart_items_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_cart_items_unit_price_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    cart_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    variant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    # Price snapshot at add-to-cart time (revalidated at checkout)
    unit_price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    product: Mapped["Product"] = relationship("Product")  # noqa: F821
    variant: Mapped["ProductVariant | None"] = relationship("ProductVariant")  # noqa: F821

    @property
    def line_total(self) -> float:
        return float(self.unit_price) * self.quantity

    def __repr__(self) -> str:  # pragma: no cover
        return f"<CartItem {self.product_id} x{self.quantity}>"

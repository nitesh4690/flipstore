"""Payment records (mock provider now, Stripe/Razorpay in Phase 7)."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, new_uuid


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"
    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_payments_amount_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    order_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True
    )

    provider: Mapped[str] = mapped_column(
        String(30), nullable=False, default="mock", server_default="mock"
    )  # mock | stripe | razorpay
    method: Mapped[str | None] = mapped_column(String(30), nullable=True)  # card | upi | cod ...
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="INR", server_default="INR")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending", index=True
    )  # pending | succeeded | failed | refunded
    transaction_id: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True, index=True)

    order: Mapped["Order"] = relationship("Order", back_populates="payments")  # noqa: F821

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Payment {self.status} {self.amount}>"

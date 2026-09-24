"""Coupon / discount codes."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.base import TimestampMixin, new_uuid


class Coupon(Base, TimestampMixin):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint("value >= 0", name="ck_coupons_value_nonneg"),
        CheckConstraint(
            "value <= 100 OR discount_type = 'fixed'",
            name="ck_coupons_percentage_max_100",
        ),
        CheckConstraint("max_uses IS NULL OR max_uses > 0", name="ck_coupons_max_uses_positive"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)

    discount_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default="percentage", server_default="percentage"
    )  # percentage | fixed
    value: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    min_order_amount: Mapped[float] = mapped_column(
        Numeric(12, 2), nullable=False, default=0, server_default="0"
    )
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def is_usable(self) -> bool:
        from app.utils.datetime import as_utc

        now = datetime.now(timezone.utc)
        if not self.is_active:
            return False
        if self.starts_at and as_utc(self.starts_at) > now:
            return False
        if self.expires_at and as_utc(self.expires_at) < now:
            return False
        if self.max_uses is not None and self.used_count >= self.max_uses:
            return False
        return True

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Coupon {self.code}>"

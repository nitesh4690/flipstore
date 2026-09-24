"""User account model."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, new_uuid


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)

    role_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    # Password reset (hashed token, short-lived; email delivery arrives in Phase 7)
    password_reset_token: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    password_reset_expires: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships -------------------------------------------------------
    role: Mapped["Role"] = relationship("Role", back_populates="users", lazy="selectin")  # noqa: F821
    addresses: Mapped[list["Address"]] = relationship(  # noqa: F821
        "Address", back_populates="user", cascade="all, delete-orphan"
    )
    orders: Mapped[list["Order"]] = relationship("Order", back_populates="user")  # noqa: F821
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review", back_populates="user", cascade="all, delete-orphan"
    )
    cart: Mapped["Cart | None"] = relationship(  # noqa: F821
        "Cart", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    wishlist: Mapped["Wishlist | None"] = relationship(  # noqa: F821
        "Wishlist", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    @property
    def role_name(self) -> str:
        """Role name string used in JWTs and API responses."""
        return self.role.name if self.role else "customer"

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User {self.email}>"

"""Product, ProductImage and ProductVariant models."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
    Numeric,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin, new_uuid


class Product(Base, TimestampMixin):
    __tablename__ = "products"
    __table_args__ = (
        Index("ix_products_category_active", "category_id", "is_active"),
        Index("ix_products_brand_active", "brand_id", "is_active"),
        CheckConstraint("price >= 0", name="ck_products_price_nonneg"),
        CheckConstraint("sale_price IS NULL OR sale_price >= 0", name="ck_products_sale_price_nonneg"),
        CheckConstraint("sale_price IS NULL OR sale_price <= price", name="ck_products_sale_below_price"),
        CheckConstraint("stock >= 0", name="ck_products_stock_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(260), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)

    price: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    sale_price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    is_featured: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    # Denormalized rating cache (recalculated when reviews change)
    rating: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False, default=0, server_default="0")
    rating_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
    )
    brand_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("brands.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Relationships -------------------------------------------------------
    category: Mapped["Category | None"] = relationship("Category", back_populates="products")  # noqa: F821
    brand: Mapped["Brand | None"] = relationship("Brand", back_populates="products")  # noqa: F821
    images: Mapped[list["ProductImage"]] = relationship(
        "ProductImage",
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.position",
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    reviews: Mapped[list["Review"]] = relationship(  # noqa: F821
        "Review", back_populates="product", cascade="all, delete-orphan"
    )

    @property
    def effective_price(self) -> float:
        """Price actually charged (sale price when active)."""
        if self.sale_price is not None and self.sale_price < self.price:
            return float(self.sale_price)
        return float(self.price)

    @property
    def discount_percent(self) -> int:
        """Whole-percent discount when a sale price is active, else 0."""
        if self.sale_price is None or self.sale_price >= self.price:
            return 0
        return round((1 - float(self.sale_price) / float(self.price)) * 100)

    @property
    def in_stock(self) -> bool:
        return self.stock > 0

    @property
    def primary_image_url(self) -> str | None:
        for image in self.images:
            if image.is_primary:
                return image.url
        return self.images[0].url if self.images else None

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None

    @property
    def brand_name(self) -> str | None:
        return self.brand.name if self.brand else None

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Product {self.slug}>"


class ProductImage(Base):
    __tablename__ = "product_images"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship("Product", back_populates="images")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProductImage {self.url}>"


class ProductVariant(Base, TimestampMixin):
    """A purchasable combination of attributes (size/color/storage/weight)."""

    __tablename__ = "product_variants"
    __table_args__ = (
        CheckConstraint("stock >= 0", name="ck_variants_stock_nonneg"),
        CheckConstraint("price IS NULL OR price >= 0", name="ck_variants_price_nonneg"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=new_uuid)
    product_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)  # e.g. "Large / Red"

    # {"size": "L", "color": "Red", "storage": "256GB", "weight": "200g"}
    attributes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict, server_default="{}")

    price: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)  # overrides product price
    stock: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    product: Mapped["Product"] = relationship("Product", back_populates="variants")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ProductVariant {self.sku}>"

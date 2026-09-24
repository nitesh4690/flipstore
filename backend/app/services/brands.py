"""Brand business logic."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.brand import Brand
from app.models.product import Product
from app.schemas.brand import BrandCreate, BrandUpdate
from app.utils.text import slugify


def _unique_slug(db: Session, base: str, exclude_id: uuid.UUID | None = None) -> str:
    slug = slugify(base)
    candidate, counter = slug, 2
    while True:
        query = select(Brand.id).where(Brand.slug == candidate)
        if exclude_id is not None:
            query = query.where(Brand.id != exclude_id)
        if db.scalar(query) is None:
            return candidate
        candidate = f"{slug}-{counter}"
        counter += 1


def list_brands(db: Session, *, include_inactive: bool = False) -> list[dict]:
    query = select(Brand)
    if not include_inactive:
        query = query.where(Brand.is_active.is_(True))
    brands = db.scalars(query.order_by(Brand.name)).all()

    counts = dict(
        db.execute(
            select(Product.brand_id, func.count())
            .where(Product.is_active.is_(True), Product.brand_id.is_not(None))
            .group_by(Product.brand_id)
        ).all()
    )
    return [
        {
            "id": b.id,
            "name": b.name,
            "slug": b.slug,
            "logo_url": b.logo_url,
            "is_active": b.is_active,
            "product_count": counts.get(b.id, 0),
            "created_at": b.created_at,
        }
        for b in brands
    ]


def get_brand(db: Session, identifier: str) -> Brand:
    query = select(Brand)
    try:
        query = query.where(Brand.id == uuid.UUID(identifier))
    except ValueError:
        query = query.where(Brand.slug == identifier)
    brand = db.scalar(query)
    if brand is None:
        raise AppError("Brand not found", status_code=404)
    return brand


def create_brand(db: Session, payload: BrandCreate) -> Brand:
    brand = Brand(
        name=payload.name.strip(),
        slug=_unique_slug(db, payload.slug or payload.name),
        logo_url=payload.logo_url,
        is_active=payload.is_active,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


def update_brand(db: Session, brand: Brand, payload: BrandUpdate) -> Brand:
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"]:
        brand.name = data["name"].strip()
    if "slug" in data and data["slug"]:
        brand.slug = _unique_slug(db, data["slug"], exclude_id=brand.id)
    for field in ("logo_url", "is_active"):
        if field in data:
            setattr(brand, field, data[field])
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return brand


def delete_brand(db: Session, brand: Brand) -> None:
    db.delete(brand)
    db.commit()

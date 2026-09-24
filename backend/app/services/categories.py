"""Category business logic (flat list, tree, CRUD)."""

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryTreeNode, CategoryUpdate
from app.utils.text import slugify


def _product_counts(db: Session) -> dict[uuid.UUID, int]:
    rows = db.execute(
        select(Product.category_id, func.count())
        .where(Product.is_active.is_(True), Product.category_id.is_not(None))
        .group_by(Product.category_id)
    ).all()
    return {category_id: count for category_id, count in rows}


def _unique_slug(db: Session, base: str, exclude_id: uuid.UUID | None = None) -> str:
    slug = slugify(base)
    candidate, counter = slug, 2
    while True:
        query = select(Category.id).where(Category.slug == candidate)
        if exclude_id is not None:
            query = query.where(Category.id != exclude_id)
        if db.scalar(query) is None:
            return candidate
        candidate = f"{slug}-{counter}"
        counter += 1


def list_categories(db: Session, *, include_inactive: bool = False) -> list[dict]:
    query = select(Category)
    if not include_inactive:
        query = query.where(Category.is_active.is_(True))
    categories = db.scalars(query.order_by(Category.name)).all()

    counts = _product_counts(db)
    return [
        {
            "id": c.id,
            "name": c.name,
            "slug": c.slug,
            "description": c.description,
            "image_url": c.image_url,
            "is_active": c.is_active,
            "parent_id": c.parent_id,
            "product_count": counts.get(c.id, 0),
            "created_at": c.created_at,
        }
        for c in categories
    ]


def category_tree(db: Session, *, include_inactive: bool = False) -> list[CategoryTreeNode]:
    flat = list_categories(db, include_inactive=include_inactive)
    nodes = {row["id"]: CategoryTreeNode(**row) for row in flat}
    roots: list[CategoryTreeNode] = []
    for node in nodes.values():
        if node.parent_id and node.parent_id in nodes:
            nodes[node.parent_id].children.append(node)
        else:
            roots.append(node)
    return roots


def get_category(db: Session, identifier: str) -> Category:
    query = select(Category)
    try:
        query = query.where(Category.id == uuid.UUID(identifier))
    except ValueError:
        query = query.where(Category.slug == identifier)
    category = db.scalar(query)
    if category is None:
        raise AppError("Category not found", status_code=404)
    return category


def create_category(db: Session, payload: CategoryCreate) -> Category:
    if payload.parent_id is not None and db.get(Category, payload.parent_id) is None:
        raise AppError("Parent category not found", status_code=404)

    category = Category(
        name=payload.name.strip(),
        slug=_unique_slug(db, payload.slug or payload.name),
        description=payload.description,
        image_url=payload.image_url,
        is_active=payload.is_active,
        parent_id=payload.parent_id,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category: Category, payload: CategoryUpdate) -> Category:
    data = payload.model_dump(exclude_unset=True)

    if "parent_id" in data and data["parent_id"] is not None:
        if data["parent_id"] == category.id:
            raise AppError("A category cannot be its own parent", status_code=400)
        if db.get(Category, data["parent_id"]) is None:
            raise AppError("Parent category not found", status_code=404)

    if "name" in data and data["name"]:
        category.name = data["name"].strip()
    if "slug" in data and data["slug"]:
        category.slug = _unique_slug(db, data["slug"], exclude_id=category.id)

    for field in ("description", "image_url", "is_active", "parent_id"):
        if field in data:
            setattr(category, field, data[field])

    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def delete_category(db: Session, category: Category) -> None:
    """Delete a category (products/subcategories are unlinked via SET NULL)."""
    db.delete(category)
    db.commit()

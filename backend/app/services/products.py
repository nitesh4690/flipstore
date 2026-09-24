"""Product catalog business logic (listing, CRUD, related products)."""

import math
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppError
from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product, ProductImage, ProductVariant
from app.schemas.product import (
    PaginatedProducts,
    ProductCreate,
    ProductDetail,
    ProductListItem,
    ProductUpdate,
)
from app.utils.text import slugify, unique_sku

# Reusable "price actually charged" expression (sale price when present)
def _effective_price():
    return func.coalesce(Product.sale_price, Product.price)


SORT_EXPRESSIONS = {
    "price_asc": lambda: _effective_price().asc(),
    "price_desc": lambda: _effective_price().desc(),
    "newest": lambda: Product.created_at.desc(),
    "oldest": lambda: Product.created_at.asc(),
    "rating": lambda: Product.rating.desc(),
    "popular": lambda: Product.rating_count.desc(),
    "name_asc": lambda: Product.name.asc(),
    "name_desc": lambda: Product.name.desc(),
}

_SORT_OPTIONS = tuple(SORT_EXPRESSIONS)

_LOAD_OPTIONS = (
    selectinload(Product.images),
    selectinload(Product.category),
    selectinload(Product.brand),
    selectinload(Product.variants),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _resolve_category(db: Session, value: str) -> Category | None:
    """Look up a category by UUID or slug; None when no filter requested."""
    if not value:
        return None
    query = select(Category)
    try:
        query = query.where(Category.id == uuid.UUID(value))
    except ValueError:
        query = query.where(Category.slug == value)
    category = db.scalar(query)
    if category is None:
        raise AppError(f"Category not found: {value}", status_code=404)
    return category


def _resolve_brand(db: Session, value: str) -> Brand | None:
    if not value:
        return None
    query = select(Brand)
    try:
        query = query.where(Brand.id == uuid.UUID(value))
    except ValueError:
        query = query.where(Brand.slug == value)
    brand = db.scalar(query)
    if brand is None:
        raise AppError(f"Brand not found: {value}", status_code=404)
    return brand


def _unique_slug(db: Session, base: str, exclude_id: uuid.UUID | None = None) -> str:
    """Slugify and de-duplicate against existing products."""
    slug = slugify(base)
    candidate = slug
    counter = 2
    while True:
        query = select(Product.id).where(Product.slug == candidate)
        if exclude_id is not None:
            query = query.where(Product.id != exclude_id)
        if db.scalar(query) is None:
            return candidate
        candidate = f"{slug}-{counter}"
        counter += 1


def _ensure_unique_sku(db: Session, sku: str, exclude_id: uuid.UUID | None = None) -> None:
    query = select(Product.id).where(Product.sku == sku)
    if exclude_id is not None:
        query = query.where(Product.id != exclude_id)
    if db.scalar(query) is not None:
        raise AppError(f"SKU already exists: {sku}", status_code=409)


def serialize_item(product: Product) -> dict:
    return ProductListItem.model_validate(product).model_dump()


def serialize_detail(product: Product) -> dict:
    return ProductDetail.model_validate(product).model_dump()


# ---------------------------------------------------------------------------
# Public queries
# ---------------------------------------------------------------------------
def list_products(
    db: Session,
    *,
    search: str | None = None,
    category: str | None = None,
    brand: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    min_rating: float | None = None,
    in_stock: bool | None = None,
    is_featured: bool | None = None,
    sort: str = "newest",
    page: int = 1,
    limit: int = 12,
    include_inactive: bool = False,
) -> PaginatedProducts:
    """Search/filter/sort/paginate the catalog (public = active products only)."""
    if sort not in SORT_EXPRESSIONS:
        raise AppError(
            f"Invalid sort '{sort}'. Options: {', '.join(_SORT_OPTIONS)}",
            status_code=400,
        )
    if min_price is not None and max_price is not None and min_price > max_price:
        raise AppError("min_price cannot be greater than max_price", status_code=400)

    filters = []
    if not include_inactive:
        filters.append(Product.is_active.is_(True))

    if search:
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                Product.name.ilike(pattern),
                Product.description.ilike(pattern),
                Product.sku.ilike(pattern),
            )
        )

    category_row = _resolve_category(db, category) if category else None
    if category_row is not None:
        filters.append(Product.category_id == category_row.id)

    brand_row = _resolve_brand(db, brand) if brand else None
    if brand_row is not None:
        filters.append(Product.brand_id == brand_row.id)

    if min_price is not None:
        filters.append(_effective_price() >= min_price)
    if max_price is not None:
        filters.append(_effective_price() <= max_price)
    if min_rating is not None:
        filters.append(Product.rating >= min_rating)
    if in_stock is not None:
        filters.append(Product.stock > 0 if in_stock else Product.stock == 0)
    if is_featured is not None:
        filters.append(Product.is_featured.is_(is_featured))

    total = db.scalar(select(func.count()).select_from(Product).where(*filters)) or 0
    total_pages = math.ceil(total / limit) if total else 0

    rows = db.scalars(
        select(Product)
        .where(*filters)
        .order_by(SORT_EXPRESSIONS[sort]())
        .offset((page - 1) * limit)
        .limit(limit)
        .options(*_LOAD_OPTIONS)
    ).all()

    return PaginatedProducts(
        items=[ProductListItem.model_validate(row) for row in rows],
        page=page,
        limit=limit,
        total=total,
        total_pages=total_pages,
    )


def get_product(db: Session, identifier: str) -> Product:
    """Fetch a product by UUID or slug (404 when missing)."""
    query = select(Product).options(*_LOAD_OPTIONS)
    try:
        query = query.where(Product.id == uuid.UUID(identifier))
    except ValueError:
        query = query.where(Product.slug == identifier)

    product = db.scalar(query)
    if product is None:
        raise AppError("Product not found", status_code=404)
    return product


def related_products(db: Session, product: Product, limit: int = 4) -> list[Product]:
    """Same-category products (fall back to same brand), best rated first."""
    query = (
        select(Product)
        .where(Product.is_active.is_(True), Product.id != product.id)
        .options(*_LOAD_OPTIONS)
        .order_by(Product.rating.desc(), Product.rating_count.desc())
        .limit(limit)
    )
    if product.category_id:
        query = query.where(Product.category_id == product.category_id)
    elif product.brand_id:
        query = query.where(Product.brand_id == product.brand_id)
    return list(db.scalars(query).all())


def products_by_flag(
    db: Session,
    flag: str,
    limit: int = 8,
) -> list[Product]:
    """Home-page collections: featured / newest / best-sellers."""
    base = select(Product).where(Product.is_active.is_(True)).options(*_LOAD_OPTIONS)

    if flag == "featured":
        base = base.where(Product.is_featured.is_(True)).order_by(Product.created_at.desc())
    elif flag == "newest":
        base = base.order_by(Product.created_at.desc())
    elif flag == "best_sellers":
        # Popularity proxy until real order data exists (Phase 5+)
        base = base.order_by(Product.rating_count.desc(), Product.rating.desc())
    else:
        raise AppError(f"Unknown collection: {flag}", status_code=400)

    return list(db.scalars(base.limit(limit)).all())


# ---------------------------------------------------------------------------
# Admin CRUD
# ---------------------------------------------------------------------------
def create_product(db: Session, payload: ProductCreate) -> Product:
    if payload.sku:
        _ensure_unique_sku(db, payload.sku)

    product = Product(
        name=payload.name.strip(),
        slug=_unique_slug(db, payload.name),
        description=payload.description or "",
        sku=payload.sku or unique_sku(),
        price=payload.price,
        sale_price=payload.sale_price,
        stock=payload.stock,
        is_active=payload.is_active,
        is_featured=payload.is_featured,
        category_id=payload.category_id,
        brand_id=payload.brand_id,
    )
    db.add(product)
    db.flush()

    for index, image in enumerate(payload.images):
        db.add(
            ProductImage(
                product_id=product.id,
                url=image.url,
                alt_text=image.alt_text,
                position=image.position or index,
                is_primary=image.is_primary,
            )
        )
    for variant in payload.variants:
        db.add(
            ProductVariant(
                product_id=product.id,
                sku=variant.sku or unique_sku(prefix="VAR"),
                name=variant.name,
                attributes=variant.attributes,
                price=variant.price,
                stock=variant.stock,
            )
        )

    db.commit()
    return get_product(db, str(product.id))


def update_product(db: Session, product: Product, payload: ProductUpdate) -> Product:
    data = payload.model_dump(exclude_unset=True)

    # Images/variants are replaced wholesale when provided
    new_images = data.pop("images", None)
    new_variants = data.pop("variants", None)

    if "sku" in data and data["sku"]:
        _ensure_unique_sku(db, data["sku"], exclude_id=product.id)
    if "name" in data and data["name"]:
        product.slug = _unique_slug(db, data["name"], exclude_id=product.id)
        product.name = data["name"].strip()

    final_price = data.get("price", float(product.price))
    final_sale = data.get("sale_price", product.sale_price)
    if final_sale is not None and final_sale > final_price:
        raise AppError("sale_price cannot be greater than price", status_code=400)

    for field in (
        "description",
        "sku",
        "price",
        "sale_price",
        "stock",
        "is_active",
        "is_featured",
        "category_id",
        "brand_id",
    ):
        if field in data:
            setattr(product, field, data[field])

    if new_images is not None:
        product.images.clear()
        for index, image in enumerate(new_images):
            product.images.append(
                ProductImage(
                    url=image["url"],
                    alt_text=image.get("alt_text"),
                    position=image.get("position") or index,
                    is_primary=image.get("is_primary", False),
                )
            )

    if new_variants is not None:
        product.variants.clear()
        for variant in new_variants:
            product.variants.append(
                ProductVariant(
                    sku=variant.get("sku") or unique_sku(prefix="VAR"),
                    name=variant.get("name"),
                    attributes=variant.get("attributes") or {},
                    price=variant.get("price"),
                    stock=variant.get("stock", 0),
                )
            )

    db.add(product)
    db.commit()
    return get_product(db, str(product.id))


def delete_product(db: Session, product: Product) -> None:
    """Hard delete (order items keep snapshots; FKs fall back to SET NULL)."""
    db.delete(product)
    db.commit()

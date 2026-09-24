"""Product endpoints: public browsing + admin CRUD."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_admin, get_db
from app.schemas.product import ProductCreate, ProductUpdate
from app.services import products as product_service
from app.utils.responses import ok

router = APIRouter(prefix="/products", tags=["Products"])


# ---------------------------------------------------------------------------
# Public browsing
# ---------------------------------------------------------------------------
@router.get("", response_model=dict)
def list_products(
    db: Session = Depends(get_db),
    search: str | None = Query(default=None, max_length=200, description="Keyword match on name/description/SKU"),
    category: str | None = Query(default=None, description="Category UUID or slug"),
    brand: str | None = Query(default=None, description="Brand UUID or slug"),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_rating: float | None = Query(default=None, ge=0, le=5),
    in_stock: bool | None = Query(default=None),
    is_featured: bool | None = Query(default=None),
    sort: str = Query(
        default="newest",
        description="price_asc | price_desc | newest | oldest | rating | popular | name_asc | name_desc",
    ),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=50),
):
    """Search/filter/sort/paginate the product catalog."""
    result = product_service.list_products(
        db,
        search=search,
        category=category,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
        in_stock=in_stock,
        is_featured=is_featured,
        sort=sort,
        page=page,
        limit=limit,
    )
    return ok(result.model_dump())


# Home-page collections (declared before /{identifier} to avoid shadowing)
@router.get("/featured", response_model=dict)
def featured_products(db: Session = Depends(get_db), limit: int = Query(default=8, ge=1, le=24)):
    items = product_service.products_by_flag(db, "featured", limit)
    return ok([product_service.serialize_item(p) for p in items])


@router.get("/new-arrivals", response_model=dict)
def new_arrivals(db: Session = Depends(get_db), limit: int = Query(default=8, ge=1, le=24)):
    items = product_service.products_by_flag(db, "newest", limit)
    return ok([product_service.serialize_item(p) for p in items])


@router.get("/best-sellers", response_model=dict)
def best_sellers(db: Session = Depends(get_db), limit: int = Query(default=8, ge=1, le=24)):
    items = product_service.products_by_flag(db, "best_sellers", limit)
    return ok([product_service.serialize_item(p) for p in items])


@router.get("/{identifier}", response_model=dict)
def get_product(identifier: str, db: Session = Depends(get_db)):
    """Product detail by UUID or slug (includes images + variants)."""
    product = product_service.get_product(db, identifier)
    return ok(product_service.serialize_detail(product))


@router.get("/{identifier}/related", response_model=dict)
def get_related_products(
    identifier: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=4, ge=1, le=12),
):
    product = product_service.get_product(db, identifier)
    items = product_service.related_products(db, product, limit)
    return ok([product_service.serialize_item(p) for p in items])


# ---------------------------------------------------------------------------
# Admin CRUD
# ---------------------------------------------------------------------------
@router.post("", status_code=201, response_model=dict)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    product = product_service.create_product(db, payload)
    return ok(product_service.serialize_detail(product), message="Product created")


@router.put("/{product_id}", response_model=dict)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    product = product_service.get_product(db, product_id)
    updated = product_service.update_product(db, product, payload)
    return ok(product_service.serialize_detail(updated), message="Product updated")


@router.delete("/{product_id}", response_model=dict)
def delete_product(
    product_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    product = product_service.get_product(db, product_id)
    product_service.delete_product(db, product)
    return ok(None, message="Product deleted")

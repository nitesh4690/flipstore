"""Category endpoints: public browsing + admin CRUD."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_admin, get_db
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.services import categories as category_service
from app.utils.responses import ok

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("", response_model=dict)
def list_categories(
    db: Session = Depends(get_db),
    tree: bool = Query(default=False, description="Return nested tree instead of flat list"),
    include_inactive: bool = Query(default=False),
):
    if tree:
        nodes = category_service.category_tree(db, include_inactive=include_inactive)
        return ok([node.model_dump() for node in nodes])
    return ok(category_service.list_categories(db, include_inactive=include_inactive))


@router.get("/{identifier}", response_model=dict)
def get_category(identifier: str, db: Session = Depends(get_db)):
    category = category_service.get_category(db, identifier)
    return ok(
        {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "image_url": category.image_url,
            "is_active": category.is_active,
            "parent_id": category.parent_id,
            "created_at": category.created_at,
        }
    )


@router.post("", status_code=201, response_model=dict)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    category = category_service.create_category(db, payload)
    return ok({"id": category.id, "slug": category.slug, "name": category.name}, message="Category created")


@router.put("/{category_id}", response_model=dict)
def update_category(
    category_id: str,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    category = category_service.get_category(db, category_id)
    updated = category_service.update_category(db, category, payload)
    return ok({"id": updated.id, "slug": updated.slug, "name": updated.name}, message="Category updated")


@router.delete("/{category_id}", response_model=dict)
def delete_category(
    category_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    category = category_service.get_category(db, category_id)
    category_service.delete_category(db, category)
    return ok(None, message="Category deleted")

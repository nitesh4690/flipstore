"""Brand endpoints: public list + admin CRUD."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_admin, get_db
from app.schemas.brand import BrandCreate, BrandUpdate
from app.services import brands as brand_service
from app.utils.responses import ok

router = APIRouter(prefix="/brands", tags=["Brands"])


@router.get("", response_model=dict)
def list_brands(db: Session = Depends(get_db), include_inactive: bool = False):
    return ok(brand_service.list_brands(db, include_inactive=include_inactive))


@router.get("/{identifier}", response_model=dict)
def get_brand(identifier: str, db: Session = Depends(get_db)):
    brand = brand_service.get_brand(db, identifier)
    return ok(
        {
            "id": brand.id,
            "name": brand.name,
            "slug": brand.slug,
            "logo_url": brand.logo_url,
            "is_active": brand.is_active,
            "created_at": brand.created_at,
        }
    )


@router.post("", status_code=201, response_model=dict)
def create_brand(
    payload: BrandCreate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    brand = brand_service.create_brand(db, payload)
    return ok({"id": brand.id, "slug": brand.slug, "name": brand.name}, message="Brand created")


@router.put("/{brand_id}", response_model=dict)
def update_brand(
    brand_id: str,
    payload: BrandUpdate,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    brand = brand_service.get_brand(db, brand_id)
    updated = brand_service.update_brand(db, brand, payload)
    return ok({"id": updated.id, "slug": updated.slug, "name": updated.name}, message="Brand updated")


@router.delete("/{brand_id}", response_model=dict)
def delete_brand(
    brand_id: str,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    brand = brand_service.get_brand(db, brand_id)
    brand_service.delete_brand(db, brand)
    return ok(None, message="Brand deleted")

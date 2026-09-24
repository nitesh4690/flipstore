"""Admin-only endpoints: dashboard stats, products, orders, customers."""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_current_admin, get_db
from app.models.user import User
from app.schemas.admin import AdminOrderUpdate
from app.services import admin as admin_service
from app.services import products as product_service
from app.utils.responses import ok

router = APIRouter(prefix="/admin", tags=["Admin"])

_admin = Depends(get_current_admin)
_db = Depends(get_db)


@router.get("/ping", response_model=dict)
def admin_ping(admin: User = Depends(get_current_admin)):
    """Guarded probe proving RBAC works: customers receive 403."""
    return ok({"email": admin.email, "role": admin.role_name}, message="Admin access OK")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/stats", response_model=dict)
def dashboard_stats(db: Session = _db, admin: User = _admin):
    """KPIs: revenue, orders, customers, products, low stock, 7-day series."""
    return ok(admin_service.dashboard_stats(db), message="Dashboard stats")


# ---------------------------------------------------------------------------
# Products (admin sees inactive rows too; CRUD lives on /api/products)
# ---------------------------------------------------------------------------
@router.get("/products", response_model=dict)
def admin_products(
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = _db,
    admin: User = _admin,
):
    result = product_service.list_products(
        db, search=search, page=page, limit=limit, include_inactive=True
    )
    return ok(result.model_dump())


# ---------------------------------------------------------------------------
# Orders (across all customers)
# ---------------------------------------------------------------------------
@router.get("/orders", response_model=dict)
def admin_orders(
    status: str | None = Query(default=None, description="Filter by lifecycle status"),
    search: str | None = Query(default=None, max_length=200, description="Order # or customer"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = _db,
    admin: User = _admin,
):
    result = admin_service.list_admin_orders(
        db, status=status, search=search, page=page, limit=limit
    )
    return ok(result)


@router.get("/orders/{order_id}", response_model=dict)
def admin_order_detail(
    order_id: uuid.UUID,
    db: Session = _db,
    admin: User = _admin,
):
    order = admin_service.get_admin_order(db, order_id)
    return ok(admin_service.order_row(db, order, detail=True))


@router.patch("/orders/{order_id}", response_model=dict)
def admin_update_order(
    order_id: uuid.UUID,
    payload: AdminOrderUpdate,
    db: Session = _db,
    admin: User = _admin,
):
    order = admin_service.get_admin_order(db, order_id)
    updated = admin_service.update_order(db, order, payload)
    return ok(admin_service.order_row(db, updated, detail=True), message="Order updated")


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
@router.get("/customers", response_model=dict)
def admin_customers(
    search: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = _db,
    admin: User = _admin,
):
    return ok(admin_service.list_customers(db, search=search, page=page, limit=limit))


@router.get("/customers/{customer_id}", response_model=dict)
def admin_customer_detail(
    customer_id: uuid.UUID,
    db: Session = _db,
    admin: User = _admin,
):
    return ok(admin_service.get_customer_detail(db, customer_id))

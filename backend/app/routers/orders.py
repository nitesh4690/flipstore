"""Order endpoints — /api/orders (checkout + order history)."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_active_user, get_db
from app.schemas.order import CheckoutRequest
from app.services import orders as order_service
from app.utils.responses import ok

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def place_order(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    order = order_service.checkout(db, user, payload)
    return ok(message="Order placed successfully", data=order_service.order_payload(db, order, detail=True))


@router.get("", response_model=dict)
def list_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    result = order_service.list_orders(db, user, page=page, limit=limit)
    return ok(
        data={
            "items": [order_service.order_payload(db, order) for order in result["items"]],
            "total": result["total"],
            "page": result["page"],
            "limit": result["limit"],
            "total_pages": result["total_pages"],
        }
    )


@router.get("/{order_id}", response_model=dict)
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    order = order_service.get_order(db, user, order_id)
    return ok(data=order_service.order_payload(db, order, detail=True))

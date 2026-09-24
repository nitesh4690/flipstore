"""Payment endpoints — view your payment records, admin refunds."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_active_user, get_current_admin, get_db
from app.models.payment import Payment
from app.services import payments as payment_service
from app.utils.responses import ok

router = APIRouter(prefix="/payments", tags=["payments"])


@router.get("/{payment_id}", response_model=dict)
def get_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    """Payment detail for the order owner (admins can view any)."""
    payment = payment_service.get_payment(db, payment_id, viewer=user)
    return ok(payment_service.payment_payload(payment))


@router.post("/{payment_id}/refund", response_model=dict)
def refund_payment(
    payment_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: object = Depends(get_current_admin),
):
    payment = payment_service.get_payment(db, payment_id)
    refunded = payment_service.refund_payment(db, payment)
    return ok(
        payment_service.payment_payload(refunded),
        message="Payment refunded",
    )

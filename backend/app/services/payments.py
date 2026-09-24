"""Payment gateway abstraction — mock provider now, Stripe driver later.

The mock gateway mimics a real card processor so checkout exercises the same
success/decline paths production code will take:

    4242 4242 4242 4242  — succeeds (any other Luhn-valid number succeeds)
    4000 0000 0000 0002  — declined            (AppError 402)
    4000 0000 0000 9995  — insufficient funds  (AppError 402)

Malformed numbers/expiry/CVC raise AppError(400) before anything is persisted.
"""

import secrets

from app.core.config import settings
from app.core.exceptions import AppError
from app.models.payment import Payment
from app.schemas.order import CardDetails

DECLINE_CARDS = {
    "4000000000000002": "Your card was declined",
    "4000000000009995": "Insufficient funds on this card",
}


def _digits(number: str) -> str:
    return "".join(char for char in number if char.isdigit())


def luhn_valid(number: str) -> bool:
    """Standard Luhn checksum (validates 13–19 digit card numbers)."""
    digits = _digits(number)
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for index, char in enumerate(reversed(digits)):
        value = int(char)
        if index % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def _check_expiry(expiry: str) -> None:
    month_str, year_str = expiry.split("/")
    month, year = int(month_str), 2000 + int(year_str)
    if not 1 <= month <= 12:
        raise AppError("Card expiry month must be between 01 and 12", status_code=400)

    from datetime import datetime

    now = datetime.now()
    if (year, month) < (now.year, now.month):
        raise AppError("This card has expired", status_code=400)


def authorize_card(card: CardDetails | None) -> dict:
    """Run the (mock) gateway for a card payment.

    Returns {"status": "succeeded", "transaction_id": "MOCK-..."}.
    Raises AppError(400/402) for invalid or declined cards.
    `card=None` keeps the legacy always-succeed path for API clients that
    don't send card details yet (Phase 5 behaviour).
    """
    provider = settings.PAYMENT_PROVIDER.strip().lower()
    if provider != "mock":
        raise AppError(f"Payment provider '{provider}' is not available yet", status_code=501)

    if card is None:
        # Legacy path — no card details provided, mock gateway approves.
        return {"status": "succeeded", "transaction_id": _transaction_id()}

    number = _digits(card.number)
    if not 13 <= len(number) <= 19:
        raise AppError("Card number must be 13–19 digits", status_code=400)
    if not luhn_valid(number):
        raise AppError("That card number is invalid", status_code=400)

    _check_expiry(card.expiry)

    decline = DECLINE_CARDS.get(number)
    if decline:
        raise AppError(decline, status_code=402)

    return {"status": "succeeded", "transaction_id": _transaction_id()}


def _transaction_id() -> str:
    return f"MOCK-{secrets.token_hex(8).upper()}"


# ---------------------------------------------------------------------------
# Refunds + serialization
# ---------------------------------------------------------------------------
def payment_payload(payment: Payment) -> dict:
    return {
        "id": payment.id,
        "order_id": payment.order_id,
        "provider": payment.provider,
        "method": payment.method,
        "amount": float(payment.amount),
        "currency": payment.currency,
        "status": payment.status,
        "transaction_id": payment.transaction_id,
        "created_at": payment.created_at,
    }


def get_payment(db, payment_id, viewer=None) -> Payment:
    """Fetch a payment; when `viewer` is given, restrict to their own orders
    (admins pass viewer=None and see everything). 404 rather than 403 for
    foreign payments so IDs don't leak."""
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise AppError("Payment not found", status_code=404)
    if viewer is not None and viewer.role_name != "admin":
        order = payment.order
        if order is None or order.user_id != viewer.id:
            raise AppError("Payment not found", status_code=404)
    return payment


def refund_payment(db, payment: Payment) -> Payment:
    """Refund a succeeded payment and mark the order's payment refunded."""
    if payment.status == "refunded":
        raise AppError("This payment has already been refunded", status_code=409)
    if payment.status != "succeeded":
        raise AppError("Only succeeded payments can be refunded", status_code=409)

    payment.status = "refunded"
    order = payment.order
    if order is not None:
        order.payment_status = "refunded"
        db.add(order)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

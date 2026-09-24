"""Phase 7 tests: mock payment gateway (card authorization, refunds)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.models.user import User

_auth_counter = 0

VALID_CARD = {"number": "4242 4242 4242 4242", "expiry": "12/34", "cvc": "123"}
DECLINE_CARD = {"number": "4000 0000 0000 0002", "expiry": "12/34", "cvc": "123"}
NO_FUNDS_CARD = {"number": "4000 0000 0000 9995", "expiry": "12/34", "cvc": "123"}

ADDRESS = {
    "label": "Home",
    "full_name": "Pay W",
    "phone": "+1 555 0108",
    "line1": "8 Payment Place",
    "city": "Paytown",
    "state": "PY",
    "postal_code": "80001",
    "country": "USA",
}


@pytest.fixture(scope="module", autouse=True)
def isolate(client: TestClient):
    yield
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.email.like("phase7pay_user%"))).all()
        for user in users:
            for order in db.scalars(select(Order).where(Order.user_id == user.id)).all():
                db.delete(order)  # cascades items + payments
            db.delete(user)
        products = db.scalars(select(Product).where(Product.sku.like("SKU-P7-PAY%"))).all()
        for product in products:
            db.delete(product)
        category = db.scalar(select(Category).where(Category.slug == "p7-payment-category"))
        if category is not None:
            db.delete(category)
        db.commit()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _data(response) -> dict:
    body = response.json()
    assert body["success"] is True, body
    return body["data"]


def _register(client: TestClient) -> tuple[str, str]:
    global _auth_counter
    _auth_counter += 1
    email = f"phase7pay_user{_auth_counter}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "first_name": "Pay",
            "last_name": f"W{_auth_counter}",
            "email": email,
            "password": "Secret123!",
        },
    )
    assert response.status_code in (200, 201), response.text
    return _data(response)["access_token"], email


@pytest.fixture(scope="module")
def product(client: TestClient) -> str:
    with SessionLocal() as db:
        category = Category(name="P7 Payment Category", slug="p7-payment-category")
        db.add(category)
        db.flush()
        row = Product(
            name="Phase Seven Box",
            slug="phase-seven-box",
            description="Payment fixture",
            sku="SKU-P7-PAYBOX",
            price=40.0,
            stock=100,
            is_active=True,
            category_id=category.id,
        )
        db.add(row)
        db.commit()
        return str(row.id)


def _checkout(client: TestClient, token: str, product: str, **extra):
    """Fresh cart (1 item) for this user, then place the order."""
    added = client.post(
        "/api/cart/items",
        json={"product_id": product, "quantity": 1},
        headers=_headers(token),
    )
    assert added.status_code == 201, added.text
    payload = {
        "payment_method": "card_mock",
        "shipping_address": ADDRESS,
        **extra,
    }
    return client.post("/api/orders", json=payload, headers=_headers(token))


# ---------------------------------------------------------------------------
# Gateway outcomes
# ---------------------------------------------------------------------------
def test_valid_card_succeeds(client: TestClient, product: str):
    token, _ = _register(client)
    response = _checkout(client, token, product, card=VALID_CARD)
    assert response.status_code == 201, response.text

    order = _data(response)
    assert order["payment_status"] == "paid"
    payment = order["payments"][0]
    assert payment["status"] == "succeeded"
    assert payment["transaction_id"].startswith("MOCK-")


def test_legacy_checkout_without_card_still_succeeds(client: TestClient, product: str):
    token, _ = _register(client)
    response = _checkout(client, token, product)  # no `card` — Phase 5 behaviour
    assert response.status_code == 201, response.text
    assert _data(response)["payments"][0]["status"] == "succeeded"


def test_cod_payment_stays_pending(client: TestClient, product: str):
    token, _ = _register(client)
    response = _checkout(client, token, product, payment_method="cod")
    assert response.status_code == 201, response.text
    order = _data(response)
    assert order["payment_status"] == "pending"
    assert order["status"] == "pending"
    assert order["payments"][0]["status"] == "pending"


def test_declined_card_blocks_order(client: TestClient, product: str):
    token, _ = _register(client)
    response = _checkout(client, token, product, card=DECLINE_CARD)
    assert response.status_code == 402
    body = response.json()
    assert body["success"] is False
    assert body["message"] == "Your card was declined"

    # Nothing persisted: no order, cart untouched
    orders = _data(client.get("/api/orders", headers=_headers(token)))
    assert orders["total"] == 0
    cart = _data(client.get("/api/cart", headers=_headers(token)))
    assert len(cart["items"]) == 1


def test_insufficient_funds_card_declines(client: TestClient, product: str):
    token, _ = _register(client)
    response = _checkout(client, token, product, card=NO_FUNDS_CARD)
    assert response.status_code == 402
    assert "Insufficient funds" in response.json()["message"]


def test_luhn_invalid_card_rejected(client: TestClient, product: str):
    token, _ = _register(client)
    response = _checkout(
        client, token, product,
        card={"number": "1234 5678 9012 3456", "expiry": "12/34", "cvc": "123"},
    )
    assert response.status_code == 400
    assert "invalid" in response.json()["message"].lower()


def test_expired_card_rejected(client: TestClient, product: str):
    token, _ = _register(client)
    response = _checkout(
        client, token, product,
        card={"number": "4242 4242 4242 4242", "expiry": "01/20", "cvc": "123"},
    )
    assert response.status_code == 400
    assert "expired" in response.json()["message"].lower()


def test_bad_expiry_month_rejected(client: TestClient, product: str):
    token, _ = _register(client)
    response = _checkout(
        client, token, product,
        card={"number": "4242 4242 4242 4242", "expiry": "13/34", "cvc": "123"},
    )
    assert response.status_code == 400
    assert "01 and 12" in response.json()["message"]


def test_malformed_card_fields_fail_schema_validation(client: TestClient, product: str):
    token, _ = _register(client)
    response = _checkout(
        client, token, product,
        card={"number": "4242424242424242", "expiry": "122034", "cvc": "123"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Payment reads + refunds
# ---------------------------------------------------------------------------
def _first_payment_id(client: TestClient, token: str) -> str:
    orders = _data(client.get("/api/orders", headers=_headers(token)))
    detail = _data(client.get(f"/api/orders/{orders['items'][0]['id']}", headers=_headers(token)))
    return detail["payments"][0]["id"]


def test_payment_visibility(client: TestClient, product: str, admin_token: str):
    token, _ = _register(client)
    assert _checkout(client, token, product, card=VALID_CARD).status_code == 201
    payment_id = _first_payment_id(client, token)

    owner = client.get(f"/api/payments/{payment_id}", headers=_headers(token))
    assert owner.status_code == 200
    assert _data(owner)["status"] == "succeeded"

    stranger_token, _ = _register(client)
    stranger = client.get(f"/api/payments/{payment_id}", headers=_headers(stranger_token))
    assert stranger.status_code == 404  # no ID probing

    missing = client.get(f"/api/payments/00000000-0000-0000-0000-000000000000", headers=_headers(token))
    assert missing.status_code == 404

    admin = client.get(f"/api/payments/{payment_id}", headers=_headers(admin_token))
    assert admin.status_code == 200


def test_refund_requires_admin(client: TestClient, product: str):
    token, _ = _register(client)
    assert _checkout(client, token, product, card=VALID_CARD).status_code == 201
    payment_id = _first_payment_id(client, token)
    response = client.post(f"/api/payments/{payment_id}/refund", headers=_headers(token))
    assert response.status_code == 403


def test_admin_refund_flow(client: TestClient, product: str, admin_token: str):
    token, _ = _register(client)
    placed = _checkout(client, token, product, card=VALID_CARD)
    assert placed.status_code == 201
    payment_id = _first_payment_id(client, token)

    refund = client.post(f"/api/payments/{payment_id}/refund", headers=_headers(admin_token))
    assert refund.status_code == 200, refund.text
    assert _data(refund)["status"] == "refunded"
    assert refund.json()["message"] == "Payment refunded"

    # Order's payment status follows the refund
    orders = _data(client.get("/api/orders", headers=_headers(token)))
    detail = _data(client.get(f"/api/orders/{orders['items'][0]['id']}", headers=_headers(token)))
    assert detail["payment_status"] == "refunded"

    # Idempotency guard
    again = client.post(f"/api/payments/{payment_id}/refund", headers=_headers(admin_token))
    assert again.status_code == 409


def test_cannot_refund_pending_cod_payment(
    client: TestClient, product: str, admin_token: str
):
    token, _ = _register(client)
    assert _checkout(client, token, product, payment_method="cod").status_code == 201
    payment_id = _first_payment_id(client, token)
    response = client.post(f"/api/payments/{payment_id}/refund", headers=_headers(admin_token))
    assert response.status_code == 409
    assert "succeeded" in response.json()["message"]

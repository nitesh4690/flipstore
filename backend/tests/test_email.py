"""Phase 7 tests: transactional emails (welcome, confirmation, status change)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.models.user import User
from app.services import email as email_service

_auth_counter = 0

ADDRESS = {
    "label": "Home",
    "full_name": "Mail W",
    "phone": "+1 555 0110",
    "line1": "10 Email Avenue",
    "city": "Mailtown",
    "state": "EM",
    "postal_code": "10001",
    "country": "USA",
}


@pytest.fixture(scope="module", autouse=True)
def isolate(client: TestClient):
    yield
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.email.like("phase7eml_user%"))).all()
        for user in users:
            for order in db.scalars(select(Order).where(Order.user_id == user.id)).all():
                db.delete(order)
            db.delete(user)
        products = db.scalars(select(Product).where(Product.sku.like("SKU-P7-EML%"))).all()
        for product in products:
            db.delete(product)
        category = db.scalar(select(Category).where(Category.slug == "p7-email-category"))
        if category is not None:
            db.delete(category)
        db.commit()


@pytest.fixture(autouse=True)
def clean_outbox():
    email_service.clear_outbox()
    yield
    email_service.clear_outbox()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _data(response) -> dict:
    body = response.json()
    assert body["success"] is True, body
    return body["data"]


def _register(client: TestClient) -> tuple[str, str]:
    global _auth_counter
    _auth_counter += 1
    email = f"phase7eml_user{_auth_counter}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "first_name": "Mail",
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
        category = Category(name="P7 Email Category", slug="p7-email-category")
        db.add(category)
        db.flush()
        row = Product(
            name="Phase Seven Parcel",
            slug="phase-seven-parcel",
            description="Email fixture",
            sku="SKU-P7-EMLBOX",
            price=30.0,
            stock=60,
            is_active=True,
            category_id=category.id,
        )
        db.add(row)
        db.commit()
        return str(row.id)


def _messages_to(recipient: str) -> list[dict]:
    return [message for message in email_service.get_outbox() if message["to"] == recipient]


# ---------------------------------------------------------------------------
# Sends
# ---------------------------------------------------------------------------
def test_registration_sends_welcome_email(client: TestClient):
    token, email = _register(client)
    assert token

    messages = _messages_to(email)
    assert len(messages) == 1
    welcome = messages[0]
    assert welcome["subject"].startswith("Welcome to FlipStore")
    assert "Mail" in welcome["subject"]
    assert settings.EMAIL_FROM in welcome["from"]
    assert "Start shopping" in welcome["html"]


def test_checkout_sends_order_confirmation(client: TestClient, product: str):
    token, email = _register(client)
    assert client.post(
        "/api/cart/items",
        json={"product_id": product, "quantity": 1},
        headers=_headers(token),
    ).status_code == 201
    placed = client.post(
        "/api/orders",
        json={"payment_method": "cod", "shipping_address": ADDRESS},
        headers=_headers(token),
    )
    assert placed.status_code == 201, placed.text
    order = _data(placed)

    messages = _messages_to(email)
    confirmation = [m for m in messages if order["order_number"] in m["subject"]]
    assert len(confirmation) == 1
    assert confirmation[0]["subject"] == f"Order {order['order_number']} confirmed"
    assert order["order_number"] in confirmation[0]["text"]
    assert f"${order['total']:,.2f}" in confirmation[0]["text"]


def test_admin_status_change_sends_update_email(
    client: TestClient, product: str, admin_token: str
):
    token, email = _register(client)
    assert client.post(
        "/api/cart/items",
        json={"product_id": product, "quantity": 1},
        headers=_headers(token),
    ).status_code == 201
    placed = client.post(
        "/api/orders",
        json={"payment_method": "cod", "shipping_address": ADDRESS},
        headers=_headers(token),
    )
    assert placed.status_code == 201
    order = _data(placed)
    email_service.clear_outbox()  # focus on the status-change email only

    response = client.patch(
        f"/api/admin/orders/{order['id']}",
        json={"status": "confirmed"},
        headers=_headers(admin_token),
    )
    assert response.status_code == 200, response.text

    messages = _messages_to(email)
    assert len(messages) == 1
    update = messages[0]
    assert update["subject"] == f"Update for order {order['order_number']}"
    assert "Order status" in update["text"]
    assert "pending -> confirmed" in update["text"]


def test_no_status_email_when_nothing_changes(
    client: TestClient, product: str, admin_token: str
):
    token, email = _register(client)
    assert client.post(
        "/api/cart/items",
        json={"product_id": product, "quantity": 1},
        headers=_headers(token),
    ).status_code == 201
    placed = client.post(
        "/api/orders",
        json={"payment_method": "cod", "shipping_address": ADDRESS},
        headers=_headers(token),
    )
    assert placed.status_code == 201
    order = _data(placed)
    email_service.clear_outbox()

    # Same status again -> no changes -> no email
    response = client.patch(
        f"/api/admin/orders/{order['id']}",
        json={"status": order["status"]},
        headers=_headers(admin_token),
    )
    assert response.status_code == 200
    assert _messages_to(email) == []


# ---------------------------------------------------------------------------
# Resilience
# ---------------------------------------------------------------------------
def test_send_email_never_raises(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_BACKEND", "file")
    monkeypatch.setattr(settings, "EMAIL_FILE_PATH", r"N:\does\not\exist\emails.log")

    result = email_service.send_email(
        "someone@example.com", "Doomed", "<p>hello</p>"
    )
    assert result is False  # logged, swallowed — callers are unaffected


def test_html_to_text_fallback():
    text = email_service._html_to_text(
        "<h1>Title</h1><p>Hello <b>world</b></p><br>Bye"
    )
    assert "Title" in text
    assert "Hello world" in text
    assert "Bye" in text
    assert "<p>" not in text

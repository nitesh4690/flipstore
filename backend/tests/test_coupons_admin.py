"""Phase 7 tests: admin coupon management (CRUD, RBAC, validation, usage)."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.order import Order
from app.models.product import Product
from app.models.user import User

_auth_counter = 0

ADDRESS = {
    "label": "Home",
    "full_name": "Coupon W",
    "phone": "+1 555 0109",
    "line1": "9 Coupon Court",
    "city": "Coupontown",
    "state": "CP",
    "postal_code": "90001",
    "country": "USA",
}


@pytest.fixture(scope="module", autouse=True)
def isolate(client: TestClient):
    yield
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.email.like("phase7cpn_user%"))).all()
        for user in users:
            for order in db.scalars(select(Order).where(Order.user_id == user.id)).all():
                db.delete(order)
            db.delete(user)
        products = db.scalars(select(Product).where(Product.sku.like("SKU-P7-CPN%"))).all()
        for product in products:
            db.delete(product)
        category = db.scalar(select(Category).where(Category.slug == "p7-coupon-category"))
        if category is not None:
            db.delete(category)
        db.execute(
            Coupon.__table__.delete().where(
                Coupon.code.in_(["P7TEST", "P7EDIT", "P7CONFLICT", "P7USED"])
            )
        )
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
    email = f"phase7cpn_user{_auth_counter}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "first_name": "Cpn",
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
        category = Category(name="P7 Coupon Category", slug="p7-coupon-category")
        db.add(category)
        db.flush()
        row = Product(
            name="Phase Seven Bundle",
            slug="phase-seven-bundle",
            description="Coupon fixture",
            sku="SKU-P7-CPNBUNDLE",
            price=60.0,
            stock=80,
            is_active=True,
            category_id=category.id,
        )
        db.add(row)
        db.commit()
        return str(row.id)


def _payload(**overrides) -> dict:
    payload = {
        "code": "P7TEST",
        "discount_type": "percentage",
        "value": 10,
        "min_order_amount": 0,
        "max_uses": None,
        "starts_at": None,
        "expires_at": None,
        "is_active": True,
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------
def test_coupons_require_auth(client: TestClient):
    assert client.get("/api/coupons").status_code == 401
    assert client.post("/api/coupons", json=_payload()).status_code == 401


def test_coupons_forbidden_for_customers(client: TestClient):
    token, _ = _register(client)
    assert client.get("/api/coupons", headers=_headers(token)).status_code == 403
    assert (
        client.post("/api/coupons", json=_payload(), headers=_headers(token)).status_code
        == 403
    )


# ---------------------------------------------------------------------------
# Create + validation
# ---------------------------------------------------------------------------
def test_create_coupon_normalizes_code(client: TestClient, admin_token: str):
    response = client.post(
        "/api/coupons",
        json=_payload(code="  p7test "),
        headers=_headers(admin_token),
    )
    assert response.status_code == 201, response.text
    data = _data(response)
    assert data["code"] == "P7TEST"
    assert data["used_count"] == 0
    assert data["is_active"] is True
    assert response.json()["message"] == "Coupon created"


def test_duplicate_code_conflict(client: TestClient, admin_token: str):
    response = client.post(
        "/api/coupons",
        json=_payload(code="P7test"),
        headers=_headers(admin_token),
    )
    assert response.status_code == 409


@pytest.mark.parametrize(
    "overrides",
    [
        {"code": "!bad code"},                       # charset
        {"code": "AB"},                              # too short
        {"value": 0},                                # not > 0
        {"value": 150},                              # percentage cap
        {"discount_type": "bogus"},                  # enum
        {"min_order_amount": -5},                    # negative minimum
        {"max_uses": 0},                             # usage limit must be > 0
        {
            # ISO strings (datetimes aren't JSON-serializable in the client)
            "starts_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(),
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        },                                           # expires before start
    ],
)
def test_create_coupon_validation(client: TestClient, admin_token: str, overrides):
    response = client.post(
        "/api/coupons",
        json=_payload(**overrides),
        headers=_headers(admin_token),
    )
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# List / update / delete
# ---------------------------------------------------------------------------
def test_list_and_search(client: TestClient, admin_token: str):
    listing = _data(client.get("/api/coupons", headers=_headers(admin_token)))
    assert any(item["code"] == "P7TEST" for item in listing["items"])

    search = _data(
        client.get(
            "/api/coupons",
            params={"search": "p7test"},  # search is case-insensitive
            headers=_headers(admin_token),
        )
    )
    assert search["total"] >= 1
    assert all(item["code"] == "P7TEST" for item in search["items"])


def test_update_coupon(client: TestClient, admin_token: str):
    listing = _data(
        client.get(
            "/api/coupons",
            params={"search": "P7TEST"},
            headers=_headers(admin_token),
        )
    )
    coupon_id = listing["items"][0]["id"]

    response = client.patch(
        f"/api/coupons/{coupon_id}",
        json=_payload(
            code="P7EDIT",
            discount_type="fixed",
            value=25,
            min_order_amount=50,
            max_uses=100,
            is_active=False,
        ),
        headers=_headers(admin_token),
    )
    assert response.status_code == 200, response.text
    data = _data(response)
    assert data["code"] == "P7EDIT"
    assert data["discount_type"] == "fixed"
    assert data["value"] == 25
    assert data["max_uses"] == 100
    assert data["is_active"] is False

    # Restore a friendly state for later tests
    client.patch(
        f"/api/coupons/{coupon_id}",
        json=_payload(),
        headers=_headers(admin_token),
    )


def test_update_code_conflict(client: TestClient, admin_token: str):
    # P7CONFLICT already exists; renaming P7TEST to it must 409
    client.post("/api/coupons", json=_payload(code="P7CONFLICT"), headers=_headers(admin_token))
    listing = _data(
        client.get(
            "/api/coupons",
            params={"search": "P7TEST"},
            headers=_headers(admin_token),
        )
    )
    coupon_id = listing["items"][0]["id"]
    response = client.patch(
        f"/api/coupons/{coupon_id}",
        json=_payload(code="p7conflict"),
        headers=_headers(admin_token),
    )
    assert response.status_code == 409


def test_unknown_coupon_404(client: TestClient, admin_token: str):
    fake = str(uuid.uuid4())
    assert (
        client.patch(f"/api/coupons/{fake}", json=_payload(), headers=_headers(admin_token)).status_code
        == 404
    )
    assert client.delete(f"/api/coupons/{fake}", headers=_headers(admin_token)).status_code == 404


def test_checkout_increments_usage_counter(client: TestClient, admin_token: str, product: str):
    client.post("/api/coupons", json=_payload(code="P7USED", value=10), headers=_headers(admin_token))
    token, _ = _register(client)

    assert client.post(
        "/api/cart/items",
        json={"product_id": product, "quantity": 1},
        headers=_headers(token),
    ).status_code == 201
    applied = client.put(
        "/api/cart/coupon",
        json={"code": "P7USED"},
        headers=_headers(token),
    )
    assert applied.status_code == 200, applied.text

    placed = client.post(
        "/api/orders",
        json={"payment_method": "cod", "shipping_address": ADDRESS},
        headers=_headers(token),
    )
    assert placed.status_code == 201, placed.text
    order = _data(placed)
    assert order["discount"] == 6.0  # 10% of $60

    listing = _data(
        client.get(
            "/api/coupons",
            params={"search": "P7USED"},
            headers=_headers(admin_token),
        )
    )
    assert listing["items"][0]["used_count"] == 1


def test_delete_coupon_keeps_existing_orders(client: TestClient, admin_token: str):
    created = _data(
        client.post("/api/coupons", json=_payload(code="P7DEL"), headers=_headers(admin_token))
    )
    response = client.delete(f"/api/coupons/{created['id']}", headers=_headers(admin_token))
    assert response.status_code == 200
    assert response.json()["message"] == "Coupon deleted"

    listing = _data(client.get("/api/coupons", params={"limit": 50}, headers=_headers(admin_token)))
    assert all(item["id"] != created["id"] for item in listing["items"])

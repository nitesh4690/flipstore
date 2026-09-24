"""Phase 6 tests: admin dashboard stats, orders, customers, product listing."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.models.user import User

_auth_counter = 0


@pytest.fixture(scope="module", autouse=True)
def isolate(client: TestClient):
    """Remove everything this module creates so global-count tests stay exact.

    test_products asserts exact catalog totals over the shared session DB, and
    other modules count users/orders — phase-6 data must not outlive this module.
    """
    yield
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.email.like("phase6_user%"))).all()
        for user in users:
            for order in db.scalars(select(Order).where(Order.user_id == user.id)).all():
                db.delete(order)  # cascades items + payments
            db.delete(user)      # cascades cart, wishlist, addresses
        products = db.scalars(select(Product).where(Product.sku.like("SKU-P6-%"))).all()
        for product in products:
            db.delete(product)   # cascades variants, images, reviews
        category = db.scalar(select(Category).where(Category.slug == "p6-admin-category"))
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
    email = f"phase6_user{_auth_counter}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "first_name": "Phase",
            "last_name": f"Six{_auth_counter}",
            "email": email,
            "password": "Secret123!",
        },
    )
    assert response.status_code in (200, 201), response.text
    return _data(response)["access_token"], email


ADDRESS = {
    "label": "Home",
    "full_name": "Phase Six",
    "phone": "+1 555 0106",
    "line1": "6 Admin Street",
    "city": "Admintown",
    "state": "AD",
    "postal_code": "54321",
    "country": "USA",
}


@pytest.fixture(scope="module")
def shop(client: TestClient):
    """One product for building orders in admin tests."""
    with SessionLocal() as db:
        category = Category(name="P6 Admin Category", slug="p6-admin-category")
        db.add(category)
        db.flush()
        product = Product(
            name="Phase Six Widget",
            slug="phase-six-widget",
            description="Used by admin tests",
            sku="SKU-P6-WIDGET",
            price=40.0,
            stock=100,  # plenty for the module's ~8 test orders
            rating=4.0,
            rating_count=5,
            is_active=True,
            category_id=category.id,
        )
        db.add(product)
        db.commit()
        yield {"product": str(product.id)}


def _place_order(client: TestClient, product_id: str, quantity: int = 1) -> tuple[str, dict]:
    token, email = _register(client)
    response = client.post(
        "/api/cart/items",
        json={"product_id": product_id, "quantity": quantity},
        headers=_headers(token),
    )
    assert response.status_code == 201, response.text
    response = client.post(
        "/api/orders",
        json={
            "shipping_address": ADDRESS,
            "shipping_method": "standard",
            "payment_method": "card_mock",
        },
        headers=_headers(token),
    )
    assert response.status_code == 201, response.text
    return token, _data(response)


# ---------------------------------------------------------------------------
# RBAC
# ---------------------------------------------------------------------------
class TestAdminRBAC:
    @pytest.mark.parametrize(
        "path",
        [
            "/api/admin/stats",
            "/api/admin/orders",
            "/api/admin/customers",
            "/api/admin/products",
        ],
    )
    def test_requires_token(self, client: TestClient, path: str):
        assert client.get(path).status_code == 401

    @pytest.mark.parametrize(
        "path",
        [
            "/api/admin/stats",
            "/api/admin/orders",
            "/api/admin/customers",
            "/api/admin/products",
        ],
    )
    def test_forbidden_for_customer(self, client: TestClient, path: str):
        token, _ = _register(client)
        assert client.get(path, headers=_headers(token)).status_code == 403

    def test_order_update_requires_admin(self, client: TestClient, shop):
        token, order = _place_order(client, shop["product"])
        response = client.patch(
            f"/api/admin/orders/{order['id']}",
            json={"status": "shipped"},
            headers=_headers(token),
        )
        assert response.status_code == 403


# ---------------------------------------------------------------------------
# Dashboard stats
# ---------------------------------------------------------------------------
class TestDashboardStats:
    def test_stats_shape(self, client: TestClient, admin_token: str, shop):
        _place_order(client, shop["product"])  # ensure at least one order exists
        data = _data(client.get("/api/admin/stats", headers=_headers(admin_token)))

        assert data["order_count"] >= 1
        assert data["revenue"] > 0
        assert data["customer_count"] >= 1
        assert data["product_count"] >= 1
        assert set(data["orders_by_status"]) == {
            "pending", "confirmed", "processing", "shipped", "delivered", "cancelled",
        }
        assert len(data["revenue_last_7_days"]) == 7
        for point in data["revenue_last_7_days"]:
            assert {"date", "revenue"} <= set(point)
        assert isinstance(data["low_stock"], list)
        # low_stock caps at 8 rows, so counts may exceed the returned list
        assert data["low_stock_count"] >= 0
        assert all(row["stock"] <= 5 for row in data["low_stock"])
        assert len(data["recent_orders"]) <= 5
        if data["recent_orders"]:
            assert "customer" in data["recent_orders"][0]

    def test_low_stock_listing(self, client: TestClient, admin_token: str):
        """A product at/below threshold appears in the low-stock list."""
        with SessionLocal() as db:
            scarce = Product(
                name="Phase Six Scarce",
                slug="phase-six-scarce",
                description="Low stock",
                sku="SKU-P6-SCARCE",
                price=15.0,
                stock=2,
                is_active=True,
            )
            db.add(scarce)
            db.commit()
        try:
            data = _data(client.get("/api/admin/stats", headers=_headers(admin_token)))
            skus = [row["sku"] for row in data["low_stock"]]
            assert "SKU-P6-SCARCE" in skus
        finally:
            with SessionLocal() as db:
                scarce = db.scalar(select(Product).where(Product.sku == "SKU-P6-SCARCE"))
                if scarce is not None:
                    db.delete(scarce)
                    db.commit()


# ---------------------------------------------------------------------------
# Admin product listing (includes inactive)
# ---------------------------------------------------------------------------
class TestAdminProducts:
    def test_admin_list_includes_inactive(self, client: TestClient, admin_token: str):
        headers = _headers(admin_token)
        created = client.post("/api/products", headers=headers, json={
            "name": "Phase Six Draft",
            "price": 9.99,
            "stock": 3,
            "is_active": False,
            "sku": "SKU-P6-DRAFT",
        })
        assert created.status_code == 201
        product_id = _data(created)["id"]
        try:
            admin_list = _data(client.get("/api/admin/products", params={"search": "Phase Six Draft"},
                                          headers=headers))
            assert admin_list["total"] == 1
            assert admin_list["items"][0]["is_active"] is False

            public_list = _data(client.get("/api/products", params={"search": "Phase Six Draft"}))
            assert public_list["total"] == 0
        finally:
            client.delete(f"/api/products/{product_id}", headers=headers)


# ---------------------------------------------------------------------------
# Admin orders
# ---------------------------------------------------------------------------
class TestAdminOrders:
    def test_lists_all_orders_with_customer(self, client: TestClient, admin_token: str, shop):
        token, order = _place_order(client, shop["product"])
        data = _data(client.get("/api/admin/orders", headers=_headers(admin_token)))
        assert data["total"] >= 1
        match = next(row for row in data["items"] if row["id"] == order["id"])
        assert match["customer"]["email"].startswith("phase6_user")
        assert match["customer"]["first_name"] == "Phase"

    def test_status_filter_and_search(self, client: TestClient, admin_token: str, shop):
        _, order = _place_order(client, shop["product"], quantity=2)
        headers = _headers(admin_token)

        confirmed = _data(client.get("/api/admin/orders", params={"status": "confirmed"}, headers=headers))
        assert all(row["status"] == "confirmed" for row in confirmed["items"])
        assert any(row["id"] == order["id"] for row in confirmed["items"])

        shipped = _data(client.get("/api/admin/orders", params={"status": "shipped"}, headers=headers))
        assert not any(row["id"] == order["id"] for row in shipped["items"])

        by_number = _data(client.get(
            "/api/admin/orders", params={"search": order["order_number"]}, headers=headers
        ))
        assert by_number["total"] == 1
        assert by_number["items"][0]["id"] == order["id"]

    def test_invalid_status_filter(self, client: TestClient, admin_token: str):
        response = client.get(
            "/api/admin/orders", params={"status": "warp-speed"}, headers=_headers(admin_token)
        )
        assert response.status_code == 400

    def test_order_detail(self, client: TestClient, admin_token: str, shop):
        _, order = _place_order(client, shop["product"])
        data = _data(client.get(f"/api/admin/orders/{order['id']}", headers=_headers(admin_token)))
        assert data["order_number"] == order["order_number"]
        assert data["customer"]["email"]
        assert len(data["items"]) == 1
        assert data["shipping_address"]["city"] == "Admintown"

    def test_order_detail_404(self, client: TestClient, admin_token: str):
        response = client.get(f"/api/admin/orders/{uuid.uuid4()}", headers=_headers(admin_token))
        assert response.status_code == 404

    def test_update_status_transitions(self, client: TestClient, admin_token: str, shop):
        token, order = _place_order(client, shop["product"])
        headers = _headers(admin_token)

        response = client.patch(
            f"/api/admin/orders/{order['id']}", json={"status": "processing"}, headers=headers
        )
        assert response.status_code == 200
        assert _data(response)["status"] == "processing"

        response = client.patch(
            f"/api/admin/orders/{order['id']}",
            json={"status": "shipped", "shipping_status": "shipped"},
            headers=headers,
        )
        data = _data(response)
        assert data["status"] == "shipped"
        assert data["shipping_status"] == "shipped"

        # The customer sees the transition on their own order history
        mine = _data(client.get("/api/orders", headers=_headers(token)))
        assert mine["items"][0]["status"] == "shipped"

    def test_update_rejects_invalid_values(self, client: TestClient, admin_token: str, shop):
        _, order = _place_order(client, shop["product"])
        headers = _headers(admin_token)

        response = client.patch(
            f"/api/admin/orders/{order['id']}", json={"status": "teleported"}, headers=headers
        )
        assert response.status_code == 422

        response = client.patch(
            f"/api/admin/orders/{order['id']}", json={"payment_status": "bitcoin"}, headers=headers
        )
        assert response.status_code == 422

        response = client.patch(
            f"/api/admin/orders/{order['id']}", json={}, headers=headers
        )
        assert response.status_code == 422

    def test_update_404(self, client: TestClient, admin_token: str):
        response = client.patch(
            f"/api/admin/orders/{uuid.uuid4()}", json={"status": "shipped"},
            headers=_headers(admin_token),
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
class TestAdminCustomers:
    def test_customer_list_annotates_spend(self, client: TestClient, admin_token: str, shop):
        _, order = _place_order(client, shop["product"], quantity=2)  # $80 + tax/shipping
        data = _data(client.get("/api/admin/customers", headers=_headers(admin_token)))
        assert data["total"] >= 1

        # Locate the customer precisely via the order's owner from admin orders
        admin_orders = _data(client.get("/api/admin/orders", headers=_headers(admin_token)))
        owner = next(row for row in admin_orders["items"] if row["id"] == order["id"])
        match = next(row for row in data["items"] if row["email"] == owner["customer"]["email"])

        assert match["order_count"] >= 1
        assert match["total_spent"] >= 80.0
        assert match["is_active"] is True
        assert match["id"]

    def test_customer_search(self, client: TestClient, admin_token: str):
        _, email = _register(client)
        local_part = email.split("@")[0]
        data = _data(client.get(
            "/api/admin/customers", params={"search": local_part}, headers=_headers(admin_token)
        ))
        assert any(row["email"] == email for row in data["items"])

    def test_customer_detail(self, client: TestClient, admin_token: str, shop):
        _, order = _place_order(client, shop["product"])
        admin_orders = _data(client.get("/api/admin/orders", headers=_headers(admin_token)))
        owner = next(row for row in admin_orders["items"] if row["id"] == order["id"])

        data = _data(client.get(
            f"/api/admin/customers/{owner['customer']['id']}", headers=_headers(admin_token)
        ))
        assert data["email"] == owner["customer"]["email"]
        assert data["order_count"] >= 1
        assert data["total_spent"] > 0
        assert len(data["recent_orders"]) >= 1
        assert data["recent_orders"][0]["order_number"].startswith("FS-")

    def test_customer_detail_404(self, client: TestClient, admin_token: str):
        response = client.get(
            f"/api/admin/customers/{uuid.uuid4()}", headers=_headers(admin_token)
        )
        assert response.status_code == 404

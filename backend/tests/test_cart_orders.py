"""Phase 5 tests: cart, coupons, wishlist, addresses, checkout/orders."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.database import SessionLocal
from app.models.cart import Cart
from app.models.category import Category
from app.models.coupon import Coupon
from app.models.order import Order
from app.models.product import Product, ProductVariant
from app.models.user import User
from app.models.wishlist import Wishlist

_auth_counter = 0


@pytest.fixture(scope="module", autouse=True)
def isolate_catalog(client: TestClient):
    """Remove everything this module creates so global-count tests stay exact.

    test_products asserts exact totals over the shared session database, so
    phase-5 products/coupons/users must not outlive this module.
    """
    yield
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.email.like("phase5_user%"))).all()
        for user in users:
            # Orders lack an ORM cascade to User -> delete them first
            for order in db.scalars(select(Order).where(Order.user_id == user.id)).all():
                db.delete(order)  # cascades items + payments
            db.delete(user)      # cascades cart, wishlist, addresses
        products = db.scalars(select(Product).where(Product.sku.like("SKU-P5-%"))).all()
        for product in products:
            db.delete(product)   # cascades variants, images, reviews
        category = db.scalar(select(Category).where(Category.slug == "p5-category"))
        if category is not None:
            db.delete(category)
        db.execute(delete(Coupon).where(Coupon.code.in_(["SAVE10", "FLAT5"])))
        db.commit()


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _data(response) -> dict:
    body = response.json()
    assert body["success"] is True, body
    return body["data"]


def _register(client: TestClient) -> tuple[str, str]:
    """Register a fresh user and return (token, email)."""
    global _auth_counter
    _auth_counter += 1
    email = f"phase5_user{_auth_counter}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "first_name": "Phase",
            "last_name": f"Five{_auth_counter}",
            "email": email,
            "password": "Secret123!",
        },
    )
    assert response.status_code in (200, 201), response.text
    return _data(response)["access_token"], email


@pytest.fixture(scope="module")
def shop(client: TestClient):
    """Deterministic products + coupon for cart/order tests."""
    with SessionLocal() as db:
        category = Category(name="P5 Category", slug="p5-category")
        db.add(category)
        db.flush()

        gadget = Product(
            name="Phase Five Gadget", slug="phase-five-gadget",
            description="A gadget for phase five tests", sku="SKU-P5-GADGET",
            price=50.0, stock=10, rating=4.5, rating_count=10,
            is_active=True, category_id=category.id,
        )
        rich = Product(
            name="Phase Five Luxury", slug="phase-five-luxury",
            description="Over the free-shipping threshold", sku="SKU-P5-LUXURY",
            price=100.0, stock=5, rating=4.0, rating_count=4,
            is_active=True, category_id=category.id,
        )
        scarce = Product(
            name="Phase Five Scarce", slug="phase-five-scarce",
            description="Only two units", sku="SKU-P5-SCARCE",
            price=20.0, stock=2, rating=3.0, rating_count=3,
            is_active=True, category_id=category.id,
        )
        shirt = Product(
            name="Phase Five Shirt", slug="phase-five-shirt",
            description="Variant product", sku="SKU-P5-SHIRT",
            price=30.0, stock=0, rating=4.2, rating_count=5,
            is_active=True, category_id=category.id,
        )
        variant = ProductVariant(
            product_id=None, name="Large / Navy", sku="SKU-P5-SHIRT-LNVY",
            price=28.0, stock=4,
        )
        db.add_all([gadget, rich, scarce, shirt])
        db.flush()
        variant.product_id = shirt.id
        db.add(variant)
        db.add(Coupon(code="SAVE10", discount_type="percentage", value=10, min_order_amount=0))
        db.add(Coupon(code="FLAT5", discount_type="fixed", value=5, min_order_amount=0))
        db.commit()
        yield {
            "gadget": str(gadget.id),
            "rich": str(rich.id),
            "scarce": str(scarce.id),
            "shirt": str(shirt.id),
            "variant": str(variant.id),
        }


def _add(client, token, product_id, quantity=1, variant_id=None):
    payload = {"product_id": product_id, "quantity": quantity}
    if variant_id:
        payload["variant_id"] = variant_id
    return client.post("/api/cart/items", json=payload, headers=_headers(token))


# ---------------------------------------------------------------------------
# Cart
# ---------------------------------------------------------------------------
class TestCart:
    def test_cart_requires_auth(self, client: TestClient):
        assert client.get("/api/cart").status_code == 401

    def test_add_item_and_totals(self, client: TestClient, shop):
        token, _ = _register(client)
        response = _add(client, token, shop["gadget"], 2)
        assert response.status_code == 201
        data = _data(response)
        assert data["item_count"] == 2
        assert data["totals"]["subtotal"] == 100.0
        # $100 >= threshold -> free standard shipping, 8% tax
        assert data["totals"]["shipping"] == 0
        assert data["totals"]["tax"] == 8.0
        assert data["totals"]["total"] == 108.0
        item = data["items"][0]
        assert item["name"] == "Phase Five Gadget"
        assert item["unit_price"] == 50.0
        assert item["line_total"] == 100.0

    def test_add_merges_quantity(self, client: TestClient, shop):
        token, _ = _register(client)
        _add(client, token, shop["gadget"], 1)
        data = _data(_add(client, token, shop["gadget"], 2))
        assert data["item_count"] == 3
        assert len(data["items"]) == 1
        assert data["items"][0]["quantity"] == 3

    def test_add_beyond_stock_rejected(self, client: TestClient, shop):
        token, _ = _register(client)
        response = _add(client, token, shop["scarce"], 3)
        assert response.status_code == 400
        assert "Only 2" in response.json()["message"]

    def test_shipping_below_threshold(self, client: TestClient, shop):
        token, _ = _register(client)
        data = _data(_add(client, token, shop["gadget"], 1))  # $50 < $75
        assert data["totals"]["shipping"] == 9.99
        assert data["totals"]["tax"] == 4.0
        assert data["totals"]["total"] == 63.99

    def test_update_quantity(self, client: TestClient, shop):
        token, _ = _register(client)
        data = _data(_add(client, token, shop["gadget"], 1))
        item_id = data["items"][0]["id"]
        response = client.put(
            f"/api/cart/items/{item_id}", json={"quantity": 4}, headers=_headers(token)
        )
        assert response.status_code == 200
        assert _data(response)["items"][0]["quantity"] == 4

        # Above stock limit -> 400
        response = client.put(
            f"/api/cart/items/{item_id}", json={"quantity": 99}, headers=_headers(token)
        )
        assert response.status_code == 400

    def test_remove_and_clear(self, client: TestClient, shop):
        token, _ = _register(client)
        data = _data(_add(client, token, shop["gadget"], 1))
        item_id = data["items"][0]["id"]

        data = _data(client.delete(f"/api/cart/items/{item_id}", headers=_headers(token)))
        assert data["items"] == []

        _add(client, token, shop["gadget"], 2)
        data = _data(client.request("DELETE", "/api/cart", headers=_headers(token)))
        assert data["items"] == []
        assert data["item_count"] == 0

    def test_variant_stock_limit(self, client: TestClient, shop):
        token, _ = _register(client)
        response = _add(client, token, shop["shirt"], 5, variant_id=shop["variant"])
        assert response.status_code == 400  # variant stock is 4
        response = _add(client, token, shop["shirt"], 3, variant_id=shop["variant"])
        assert response.status_code == 201
        assert _data(response)["items"][0]["unit_price"] == 28.0


# ---------------------------------------------------------------------------
# Coupons
# ---------------------------------------------------------------------------
class TestCoupons:
    def test_apply_and_remove_coupon(self, client: TestClient, shop):
        token, _ = _register(client)
        _add(client, token, shop["gadget"], 2)  # $100

        data = _data(
            client.put("/api/cart/coupon", json={"code": "SAVE10"}, headers=_headers(token))
        )
        assert data["totals"]["coupon_code"] == "SAVE10"
        assert data["totals"]["discount"] == 10.0
        assert data["totals"]["tax"] == 7.2  # (100-10) * 0.08
        assert data["totals"]["total"] == 97.2

        data = _data(
            client.put("/api/cart/coupon", json={"code": None}, headers=_headers(token))
        )
        assert data["totals"]["coupon_code"] is None
        assert data["totals"]["discount"] == 0

    def test_fixed_coupon(self, client: TestClient, shop):
        token, _ = _register(client)
        _add(client, token, shop["gadget"], 1)
        data = _data(
            client.put("/api/cart/coupon", json={"code": "FLAT5"}, headers=_headers(token))
        )
        assert data["totals"]["discount"] == 5.0

    def test_invalid_coupon_rejected(self, client: TestClient, shop):
        token, _ = _register(client)
        _add(client, token, shop["gadget"], 1)
        response = client.put(
            "/api/cart/coupon", json={"code": "NOPE"}, headers=_headers(token)
        )
        assert response.status_code == 400
        assert "Invalid coupon" in response.json()["message"]


# ---------------------------------------------------------------------------
# Wishlist
# ---------------------------------------------------------------------------
class TestWishlist:
    def test_wishlist_flow(self, client: TestClient, shop):
        token, _ = _register(client)

        data = _data(client.get("/api/wishlist", headers=_headers(token)))
        assert data["items"] == []

        response = client.post(
            "/api/wishlist/items", json={"product_id": shop["gadget"]}, headers=_headers(token)
        )
        assert response.status_code == 201
        items = _data(response)["items"]
        assert len(items) == 1
        assert items[0]["product"]["name"] == "Phase Five Gadget"

        # Duplicate add keeps a single row
        response = client.post(
            "/api/wishlist/items", json={"product_id": shop["gadget"]}, headers=_headers(token)
        )
        assert len(_data(response)["items"]) == 1

        response = client.delete(
            f"/api/wishlist/items/{shop['gadget']}", headers=_headers(token)
        )
        assert _data(response)["items"] == []

    def test_wishlist_requires_auth(self, client: TestClient):
        assert client.get("/api/wishlist").status_code == 401


# ---------------------------------------------------------------------------
# Addresses
# ---------------------------------------------------------------------------
ADDRESS = {
    "label": "Home",
    "full_name": "Phase Five",
    "phone": "+1 555 0100",
    "line1": "1 Test Street",
    "line2": "Apt 5",
    "city": "Testville",
    "state": "TS",
    "postal_code": "12345",
    "country": "USA",
}


class TestAddresses:
    def test_address_crud(self, client: TestClient):
        token, _ = _register(client)

        response = client.post("/api/addresses", json=ADDRESS, headers=_headers(token))
        assert response.status_code == 201
        address = _data(response)
        assert address["is_default_shipping"] is True  # first address -> default

        rows = _data(client.get("/api/addresses", headers=_headers(token)))["items"]
        assert len(rows) == 1

        response = client.put(
            f"/api/addresses/{address['id']}",
            json={"city": "Newtown", "label": "Office"},
            headers=_headers(token),
        )
        assert response.status_code == 200
        assert _data(response)["city"] == "Newtown"

        response = client.delete(
            f"/api/addresses/{address['id']}", headers=_headers(token)
        )
        assert response.status_code == 200
        rows = _data(client.get("/api/addresses", headers=_headers(token)))["items"]
        assert rows == []

    def test_addresses_require_auth(self, client: TestClient):
        assert client.get("/api/addresses").status_code == 401


# ---------------------------------------------------------------------------
# Checkout / orders
# ---------------------------------------------------------------------------
class TestCheckout:
    def test_checkout_empty_cart(self, client: TestClient):
        token, _ = _register(client)
        response = client.post(
            "/api/orders",
            json={"shipping_address": ADDRESS, "shipping_method": "standard",
                  "payment_method": "card_mock"},
            headers=_headers(token),
        )
        assert response.status_code == 400
        assert "empty" in response.json()["message"]

    def test_checkout_happy_path(self, client: TestClient, shop):
        token, _ = _register(client)
        _add(client, token, shop["gadget"], 3)  # $150
        _add(client, token, shop["rich"], 1)    # +$100 -> $250

        response = client.post(
            "/api/orders",
            json={
                "shipping_address": ADDRESS,
                "shipping_method": "standard",
                "payment_method": "card_mock",
                "notes": "Please ring the bell",
            },
            headers=_headers(token),
        )
        assert response.status_code == 201, response.text
        order = _data(response)

        assert order["order_number"].startswith("FS-")
        assert order["status"] == "confirmed"
        assert order["payment_status"] == "paid"
        assert order["subtotal"] == 250.0
        assert order["discount"] == 0
        assert order["shipping_cost"] == 0      # over $75
        assert order["tax"] == 20.0
        assert order["total"] == 270.0
        assert len(order["items"]) == 2
        assert order["payments"][0]["status"] == "succeeded"
        assert order["shipping_address"]["city"] == "Testville"

        # Cart cleared after checkout
        cart = _data(client.get("/api/cart", headers=_headers(token)))
        assert cart["items"] == []

        # Stock decremented (10 -> 7 on the gadget)
        detail = _data(client.get(f"/api/products/{shop['gadget']}"))
        assert detail["stock"] == 7

        # Inline address landed in the address book
        addresses = _data(client.get("/api/addresses", headers=_headers(token)))["items"]
        assert len(addresses) == 1

    def test_checkout_with_coupon_and_express(self, client: TestClient, shop):
        token, _ = _register(client)
        _add(client, token, shop["gadget"], 2)  # $100
        client.put("/api/cart/coupon", json={"code": "SAVE10"}, headers=_headers(token))

        response = client.post(
            "/api/orders",
            json={"shipping_address": ADDRESS, "shipping_method": "express",
                  "payment_method": "card_mock"},
            headers=_headers(token),
        )
        assert response.status_code == 201, response.text
        order = _data(response)
        assert order["discount"] == 10.0
        assert order["shipping_cost"] == 19.99
        assert order["tax"] == 7.2  # (100-10) * 0.08
        assert order["total"] == 117.19

    def test_checkout_cod_is_pending(self, client: TestClient, shop):
        token, _ = _register(client)
        _add(client, token, shop["gadget"], 1)
        response = client.post(
            "/api/orders",
            json={"shipping_address": ADDRESS, "shipping_method": "standard",
                  "payment_method": "cod"},
            headers=_headers(token),
        )
        assert response.status_code == 201
        order = _data(response)
        assert order["status"] == "pending"
        assert order["payment_status"] == "pending"
        assert order["payments"][0]["status"] == "pending"

    def test_checkout_stock_race(self, client: TestClient, shop):
        """Stock changing between add-to-cart and checkout must fail cleanly."""
        token, _ = _register(client)
        _add(client, token, shop["scarce"], 2)
        with SessionLocal() as db:
            product = db.get(Product, uuid.UUID(shop["scarce"]))
            product.stock = 1
            db.commit()
        try:
            response = client.post(
                "/api/orders",
                json={"shipping_address": ADDRESS, "shipping_method": "standard",
                      "payment_method": "card_mock"},
                headers=_headers(token),
            )
            assert response.status_code == 400
            assert "stock" in response.json()["message"].lower()

            # Nothing was ordered and the cart survived the failure
            orders = _data(client.get("/api/orders", headers=_headers(token)))
            assert orders["total"] == 0
            cart = _data(client.get("/api/cart", headers=_headers(token)))
            assert len(cart["items"]) == 1
        finally:
            with SessionLocal() as db:
                product = db.get(Product, uuid.UUID(shop["scarce"]))
                product.stock = 2
                db.commit()

    def test_checkout_invalid_shipping_method(self, client: TestClient, shop):
        token, _ = _register(client)
        _add(client, token, shop["gadget"], 1)
        response = client.post(
            "/api/orders",
            json={"shipping_address": ADDRESS, "shipping_method": "teleport",
                  "payment_method": "card_mock"},
            headers=_headers(token),
        )
        assert response.status_code == 422


# ---------------------------------------------------------------------------
# Order history / authorization
# ---------------------------------------------------------------------------
class TestOrders:
    def test_order_list_and_detail(self, client: TestClient, shop):
        token, _ = _register(client)
        _add(client, token, shop["gadget"], 1)
        created = _data(client.post(
            "/api/orders",
            json={"shipping_address": ADDRESS, "shipping_method": "standard",
                  "payment_method": "card_mock"},
            headers=_headers(token),
        ))

        listing = _data(client.get("/api/orders", headers=_headers(token)))
        assert listing["total"] == 1
        assert listing["items"][0]["order_number"] == created["order_number"]

        detail = _data(client.get(f"/api/orders/{created['id']}", headers=_headers(token)))
        assert detail["order_number"] == created["order_number"]
        assert detail["items"][0]["product_name"] == "Phase Five Gadget"
        assert detail["items"][0]["sku"] == "SKU-P5-GADGET"
        assert detail["shipping_method"] == "standard"

    def test_cannot_view_other_users_order(self, client: TestClient, shop):
        token_a, _ = _register(client)
        _add(client, token_a, shop["gadget"], 1)
        created = _data(client.post(
            "/api/orders",
            json={"shipping_address": ADDRESS, "shipping_method": "standard",
                  "payment_method": "card_mock"},
            headers=_headers(token_a),
        ))

        token_b, _ = _register(client)
        response = client.get(f"/api/orders/{created['id']}", headers=_headers(token_b))
        assert response.status_code == 404

    def test_orders_require_auth(self, client: TestClient):
        assert client.get("/api/orders").status_code == 401

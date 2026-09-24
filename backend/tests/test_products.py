"""Phase 3 tests: product/category/brand APIs (search, filters, sort, CRUD)."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product


@pytest.fixture(scope="module")
def catalog(client: TestClient):
    """Create a small deterministic catalog for listing tests."""
    with SessionLocal() as db:
        electronics = Category(name="Cat Electronics", slug="cat-electronics")
        apparel = Category(name="Cat Apparel", slug="cat-apparel")
        brand_a = Brand(name="Brand A", slug="brand-a")
        brand_b = Brand(name="Brand B", slug="brand-b")
        db.add_all([electronics, apparel, brand_a, brand_b])
        db.flush()

        def make(name, price, cat, brand, rating=4.0, featured=False, stock=10):
            db.add(Product(
                name=name,
                slug=name.lower().replace(" ", "-"),
                description=f"Description for {name}",
                sku=f"SKU-{name.upper().replace(' ', '')}",
                price=price,
                stock=stock,
                rating=rating,
                rating_count=int(rating * 10),
                is_active=True,
                is_featured=featured,
                category_id=cat.id,
                brand_id=brand.id,
            ))

        make("Alpha Widget", 10.0, electronics, brand_a, rating=4.8, featured=True)
        make("Beta Gadget", 20.0, electronics, brand_b, rating=4.2)
        make("Gamma Gadget", 30.0, electronics, brand_b, rating=3.5, stock=0)
        make("Delta Shirt", 15.0, apparel, brand_a, rating=4.6, featured=True)
        make("Epsilon Coat", 50.0, apparel, brand_b, rating=4.9)
        # Inactive product must never appear in public listings
        hidden = Product(name="Hidden Thing", slug="hidden-thing", description="secret",
                         sku="SKU-HIDDEN", price=5.0, stock=5, is_active=False)
        db.add(hidden)
        db.commit()

        yield {
            "electronics": str(electronics.id),
            "apparel": str(apparel.id),
            "brand_a": str(brand_a.id),
        }


def _data(response):
    body = response.json()
    assert body["success"] is True, body
    return body["data"]


# ---------------------------------------------------------------------------
# Listing / search / filter / sort / pagination
# ---------------------------------------------------------------------------
def test_list_default_pagination(client: TestClient, catalog):
    data = _data(client.get("/api/products"))
    assert data["page"] == 1
    assert data["limit"] == 12
    assert data["total"] == 5  # hidden product excluded
    assert len(data["items"]) == 5
    assert all(item["is_active"] for item in data["items"])


def test_search_keyword(client: TestClient, catalog):
    data = _data(client.get("/api/products", params={"search": "gadget"}))
    assert data["total"] == 2
    names = {item["name"] for item in data["items"]}
    assert names == {"Beta Gadget", "Gamma Gadget"}


def test_filter_by_category_slug(client: TestClient, catalog):
    data = _data(client.get("/api/products", params={"category": "cat-apparel"}))
    assert data["total"] == 2
    assert {i["category_name"] for i in data["items"]} == {"Cat Apparel"}


def test_filter_by_brand_id(client: TestClient, catalog):
    data = _data(client.get("/api/products", params={"brand": catalog["brand_a"]}))
    assert data["total"] == 2


def test_filter_by_price_range(client: TestClient, catalog):
    data = _data(client.get("/api/products", params={"min_price": 14, "max_price": 31}))
    assert {i["name"] for i in data["items"]} == {"Beta Gadget", "Delta Shirt", "Gamma Gadget"}


def test_invalid_price_range(client: TestClient, catalog):
    response = client.get("/api/products", params={"min_price": 50, "max_price": 10})
    assert response.status_code == 400
    assert response.json()["success"] is False


def test_filter_by_rating(client: TestClient, catalog):
    data = _data(client.get("/api/products", params={"min_rating": 4.6}))
    assert {i["name"] for i in data["items"]} == {"Alpha Widget", "Delta Shirt", "Epsilon Coat"}


def test_filter_in_stock(client: TestClient, catalog):
    data = _data(client.get("/api/products", params={"in_stock": True}))
    assert "Gamma Gadget" not in {i["name"] for i in data["items"]}
    data = _data(client.get("/api/products", params={"in_stock": False}))
    assert {i["name"] for i in data["items"]} == {"Gamma Gadget"}


def test_filter_featured(client: TestClient, catalog):
    data = _data(client.get("/api/products", params={"is_featured": True}))
    assert data["total"] == 2


def test_sort_price_asc(client: TestClient, catalog):
    data = _data(client.get("/api/products", params={"sort": "price_asc"}))
    prices = [i["effective_price"] for i in data["items"]]
    assert prices == sorted(prices)


def test_sort_price_desc(client: TestClient, catalog):
    data = _data(client.get("/api/products", params={"sort": "price_desc"}))
    prices = [i["effective_price"] for i in data["items"]]
    assert prices == sorted(prices, reverse=True)


def test_invalid_sort_rejected(client: TestClient, catalog):
    response = client.get("/api/products", params={"sort": "bogus"})
    assert response.status_code == 400


def test_pagination_pages(client: TestClient, catalog):
    page1 = _data(client.get("/api/products", params={"limit": 2, "page": 1, "sort": "price_asc"}))
    page2 = _data(client.get("/api/products", params={"limit": 2, "page": 2, "sort": "price_asc"}))
    assert page1["total_pages"] == 3
    assert len(page1["items"]) == 2 and len(page2["items"]) == 2
    ids1 = {i["id"] for i in page1["items"]}
    ids2 = {i["id"] for i in page2["items"]}
    assert not ids1 & ids2  # no overlap between pages


def test_unknown_category_404(client: TestClient, catalog):
    response = client.get("/api/products", params={"category": "does-not-exist"})
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Detail / related / collections
# ---------------------------------------------------------------------------
def test_product_detail_by_id(client: TestClient, catalog):
    listing = _data(client.get("/api/products", params={"search": "Alpha Widget"}))
    product_id = listing["items"][0]["id"]

    data = _data(client.get(f"/api/products/{product_id}"))
    assert data["name"] == "Alpha Widget"
    assert data["description"].startswith("Description")
    assert isinstance(data["images"], list)
    assert isinstance(data["variants"], list)


def test_product_detail_by_slug(client: TestClient, catalog):
    data = _data(client.get("/api/products/alpha-widget"))
    assert data["sku"] == "SKU-ALPHAWIDGET"


def test_product_detail_missing_404(client: TestClient, catalog):
    response = client.get(f"/api/products/{uuid.uuid4()}")
    assert response.status_code == 404


def test_related_products(client: TestClient, catalog):
    data = _data(client.get("/api/products/alpha-widget/related"))
    assert len(data) == 2  # the two other electronics products
    assert all(i["name"] != "Alpha Widget" for i in data)
    assert all(i["category_name"] == "Cat Electronics" for i in data)


def test_featured_collection(client: TestClient, catalog):
    data = _data(client.get("/api/products/featured"))
    assert {i["name"] for i in data} == {"Alpha Widget", "Delta Shirt"}


def test_collections_exclude_inactive(client: TestClient, catalog):
    for path in ("/api/products/featured", "/api/products/new-arrivals", "/api/products/best-sellers"):
        data = _data(client.get(path))
        assert all(i["name"] != "Hidden Thing" for i in data)


# ---------------------------------------------------------------------------
# Categories / brands
# ---------------------------------------------------------------------------
def test_categories_list_with_counts(client: TestClient, catalog):
    data = _data(client.get("/api/categories"))
    slugs = {c["slug"]: c for c in data}
    assert slugs["cat-electronics"]["product_count"] == 3
    assert slugs["cat-apparel"]["product_count"] == 2


def test_category_tree(client: TestClient, catalog):
    data = _data(client.get("/api/categories", params={"tree": True}))
    assert isinstance(data, list) and len(data) >= 2


def test_brands_list_with_counts(client: TestClient, catalog):
    data = _data(client.get("/api/brands"))
    slugs = {b["slug"]: b for b in data}
    assert slugs["brand-a"]["product_count"] == 2
    assert slugs["brand-b"]["product_count"] == 3


def test_unknown_category_detail_404(client: TestClient):
    assert client.get("/api/categories/nope").status_code == 404


# ---------------------------------------------------------------------------
# Admin CRUD + RBAC
# ---------------------------------------------------------------------------
def _admin_headers(client: TestClient, admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


def test_create_product_requires_admin(client: TestClient):
    payload = {"name": "Sneaky Product", "price": 10}
    assert client.post("/api/products", json=payload).status_code == 401


def test_create_product_forbidden_for_customer(client: TestClient):
    reg = client.post("/api/auth/register", json={
        "email": "buyer@example.com", "password": "SecretPass123",
        "first_name": "Buy", "last_name": "Er",
    })
    token = reg.json()["data"]["access_token"]
    payload = {"name": "Sneaky Product", "price": 10}
    response = client.post("/api/products", json=payload,
                           headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_admin_product_crud(client: TestClient, admin_token: str, catalog):
    headers = _admin_headers(client, admin_token)

    # CREATE
    create = client.post("/api/products", headers=headers, json={
        "name": "Admin Created Lamp",
        "description": "A lovely desk lamp.",
        "price": 45.0,
        "sale_price": 39.0,
        "stock": 12,
        "category_id": catalog["apparel"],
        "brand_id": catalog["brand_a"],
        "images": [{"url": "https://example.com/lamp.jpg", "is_primary": True}],
        "variants": [{"name": "Black", "attributes": {"color": "Black"}, "stock": 6}],
    })
    assert create.status_code == 201
    product = _data(create)
    assert product["slug"] == "admin-created-lamp"
    assert product["discount_percent"] == 13
    assert len(product["images"]) == 1
    assert len(product["variants"]) == 1

    # Invisible to the public list while... (it is active, so visible):
    listing = _data(client.get("/api/products", params={"search": "Admin Created Lamp"}))
    assert listing["total"] == 1

    # UPDATE (deactivate -> disappears from public list)
    update = client.put(f"/api/products/{product['id']}", headers=headers,
                        json={"is_active": False, "price": 50.0})
    assert update.status_code == 200
    assert _data(update)["is_active"] is False
    listing = _data(client.get("/api/products", params={"search": "Admin Created Lamp"}))
    assert listing["total"] == 0

    # Sale price validation on update
    bad = client.put(f"/api/products/{product['id']}", headers=headers,
                     json={"price": 20.0, "sale_price": 99.0})
    assert bad.status_code == 400

    # DELETE
    delete = client.delete(f"/api/products/{product['id']}", headers=headers)
    assert delete.status_code == 200
    assert client.get(f"/api/products/{product['id']}").status_code == 404


def test_admin_category_crud(client: TestClient, admin_token: str):
    headers = _admin_headers(client, admin_token)

    created = client.post("/api/categories", headers=headers, json={"name": "Gadgets Pro"})
    assert created.status_code == 201
    category_id = _data(created)["id"]

    updated = client.put(f"/api/categories/{category_id}", headers=headers,
                         json={"is_active": False})
    assert updated.status_code == 200
    assert _data(updated)["name"] == "Gadgets Pro"

    deleted = client.delete(f"/api/categories/{category_id}", headers=headers)
    assert deleted.status_code == 200
    assert client.get(f"/api/categories/{category_id}").status_code == 404


def test_category_write_requires_admin(client: TestClient):
    assert client.post("/api/categories", json={"name": "Nope"}).status_code == 401
    assert client.post("/api/brands", json={"name": "Nope"}).status_code == 401
    assert client.delete(f"/api/brands/{uuid.uuid4()}").status_code == 401

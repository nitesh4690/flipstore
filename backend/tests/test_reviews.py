"""Phase 7 tests: product reviews (CRUD, aggregates, verified, moderation)."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.database import SessionLocal
from app.models.category import Category
from app.models.order import Order
from app.models.product import Product
from app.models.review import Review
from app.models.user import User

_auth_counter = 0


@pytest.fixture(scope="module", autouse=True)
def isolate(client: TestClient):
    """Remove everything this module creates so global-count tests stay exact."""
    yield
    with SessionLocal() as db:
        users = db.scalars(select(User).where(User.email.like("phase7rev_user%"))).all()
        for user in users:
            for order in db.scalars(select(Order).where(Order.user_id == user.id)).all():
                db.delete(order)  # cascades items + payments
            db.delete(user)      # cascades reviews, cart, wishlist, addresses
        products = db.scalars(select(Product).where(Product.sku.like("SKU-P7-REV%"))).all()
        for product in products:
            db.delete(product)   # cascades images + reviews
        category = db.scalar(select(Category).where(Category.slug == "p7-review-category"))
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
    email = f"phase7rev_user{_auth_counter}@example.com"
    response = client.post(
        "/api/auth/register",
        json={
            "first_name": "Rev",
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
        category = Category(name="P7 Review Category", slug="p7-review-category")
        db.add(category)
        db.flush()
        row = Product(
            name="Phase Seven Gadget",
            slug="phase-seven-gadget",
            description="Review fixture",
            sku="SKU-P7-REVW",
            price=25.0,
            stock=50,
            is_active=True,
            category_id=category.id,
        )
        db.add(row)
        db.commit()
        return str(row.id)


ADDRESS = {
    "label": "Home",
    "full_name": "Rev W",
    "phone": "+1 555 0107",
    "line1": "7 Review Road",
    "city": "Reviewtown",
    "state": "RV",
    "postal_code": "70001",
    "country": "USA",
}


def _list_reviews(client: TestClient, product: str, token: str | None = None, **params):
    headers = _headers(token) if token else {}
    return client.get(f"/api/products/{product}/reviews", params=params, headers=headers)


def _assert_aggregates(client: TestClient, product: str, token: str | None = None):
    """product.rating/rating_count must equal the live review rows."""
    listing = _list_reviews(client, product, token=token, limit=50)
    data = _data(listing)
    detail = _data(client.get(f"/api/products/{product}"))
    if data["total"] == 0:
        assert detail["rating"] == 0
        assert detail["rating_count"] == 0
    else:
        expected = round(sum(i["rating"] for i in data["items"]) / data["total"], 1)
        assert detail["rating"] == expected, (detail, data["summary"])
        assert detail["rating_count"] == data["total"]
    return data


# ---------------------------------------------------------------------------
# Listing
# ---------------------------------------------------------------------------
def test_list_reviews_starts_empty(client: TestClient, product: str):
    data = _data(_list_reviews(client, product))
    assert data["items"] == []
    assert data["total"] == 0
    assert data["summary"] == {
        "average": 0,
        "count": 0,
        # JSON object keys arrive as strings
        "distribution": {"1": 0, "2": 0, "3": 0, "4": 0, "5": 0},
    }
    assert data["product"]["id"] == product


def test_list_reviews_unknown_product_404(client: TestClient):
    response = client.get(f"/api/products/{uuid.uuid4()}/reviews")
    assert response.status_code == 404


def test_list_reviews_invalid_sort_400(client: TestClient, product: str):
    response = _list_reviews(client, product, sort="bogus")
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
def test_create_review_requires_auth(client: TestClient, product: str):
    response = client.post(f"/api/products/{product}/reviews", json={"rating": 5})
    assert response.status_code == 401


def test_create_review_recomputes_aggregates(client: TestClient, product: str):
    token, _ = _register(client)
    response = client.post(
        f"/api/products/{product}/reviews",
        json={"rating": 5, "comment": "Fantastic!"},
        headers=_headers(token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["message"] == "Review published — thanks for sharing!"

    data = _assert_aggregates(client, product, token)
    assert data["summary"]["count"] == 1
    assert data["summary"]["average"] == 5
    assert data["summary"]["distribution"]["5"] == 1

    mine = [item for item in data["items"] if item["is_mine"]]
    assert len(mine) == 1
    assert mine[0]["comment"] == "Fantastic!"
    assert mine[0]["verified"] is False  # bought nothing yet


def test_create_duplicate_review_conflict(client: TestClient, product: str):
    token, _ = _register(client)
    first = client.post(
        f"/api/products/{product}/reviews",
        json={"rating": 4},
        headers=_headers(token),
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/products/{product}/reviews",
        json={"rating": 5},
        headers=_headers(token),
    )
    assert second.status_code == 409
    assert "already reviewed" in second.json()["message"]


def test_create_review_rating_bounds(client: TestClient, product: str):
    token, _ = _register(client)
    for rating in (0, 6):
        response = client.post(
            f"/api/products/{product}/reviews",
            json={"rating": rating},
            headers=_headers(token),
        )
        assert response.status_code == 422, response.text


def test_create_rating_only_review_stores_null_comment(client: TestClient, product: str):
    token, _ = _register(client)
    response = client.post(
        f"/api/products/{product}/reviews",
        json={"rating": 3, "comment": "   "},
        headers=_headers(token),
    )
    assert response.status_code == 201
    data = _assert_aggregates(client, product, token)
    mine = [item for item in data["items"] if item["is_mine"]][0]
    assert mine["rating"] == 3
    assert mine["comment"] is None


# ---------------------------------------------------------------------------
# Update / delete permissions
# ---------------------------------------------------------------------------
def test_update_own_review(client: TestClient, product: str):
    token, _ = _register(client)
    created = _data(
        client.post(
            f"/api/products/{product}/reviews",
            json={"rating": 2, "comment": "Rough start"},
            headers=_headers(token),
        )
    )
    response = client.patch(
        f"/api/reviews/{created['id']}",
        json={"rating": 4, "comment": "It grew on me"},
        headers=_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Review updated"

    data = _assert_aggregates(client, product, token)
    mine = [item for item in data["items"] if item["is_mine"]][0]
    assert mine["rating"] == 4
    assert mine["comment"] == "It grew on me"


def test_cannot_touch_other_users_review(client: TestClient, product: str, admin_token: str):
    owner_token, _ = _register(client)
    created = _data(
        client.post(
            f"/api/products/{product}/reviews",
            json={"rating": 5, "comment": "Owner only"},
            headers=_headers(owner_token),
        )
    )
    stranger_token, _ = _register(client)

    patch = client.patch(
        f"/api/reviews/{created['id']}",
        json={"rating": 1},
        headers=_headers(stranger_token),
    )
    assert patch.status_code == 403

    delete = client.delete(f"/api/reviews/{created['id']}", headers=_headers(stranger_token))
    assert delete.status_code == 403

    # Admins can moderate any review
    admin_delete = client.delete(f"/api/reviews/{created['id']}", headers=_headers(admin_token))
    assert admin_delete.status_code == 200

    data = _assert_aggregates(client, product)
    assert all(item["id"] != created["id"] for item in data["items"])


def test_delete_own_review_updates_aggregates(client: TestClient, product: str):
    token, _ = _register(client)
    created = _data(
        client.post(
            f"/api/products/{product}/reviews",
            json={"rating": 1, "comment": "Not for me"},
            headers=_headers(token),
        )
    )
    before = _assert_aggregates(client, product)
    response = client.delete(f"/api/reviews/{created['id']}", headers=_headers(token))
    assert response.status_code == 200
    after = _assert_aggregates(client, product)
    assert after["total"] == before["total"] - 1


def test_delete_unknown_review_404(client: TestClient):
    token, _ = _register(client)
    response = client.delete(f"/api/reviews/{uuid.uuid4()}", headers=_headers(token))
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Summary / sorting / pagination / moderation
# ---------------------------------------------------------------------------
def test_summary_distribution_and_sorting(client: TestClient, product: str):
    # Two more voices: one happy, one lukewarm
    for rating, comment in ((5, "Loved it"), (3, "It's fine")):
        token, _ = _register(client)
        response = client.post(
            f"/api/products/{product}/reviews",
            json={"rating": rating, "comment": comment},
            headers=_headers(token),
        )
        assert response.status_code == 201

    data = _assert_aggregates(client, product)
    summary = data["summary"]
    assert summary["count"] == data["total"] == sum(summary["distribution"].values())
    weighted = sum(int(star) * count for star, count in summary["distribution"].items())
    assert summary["average"] == round(weighted / summary["count"], 1)

    highest = _data(_list_reviews(client, product, sort="highest", limit=50))
    ratings = [item["rating"] for item in highest["items"]]
    assert ratings == sorted(ratings, reverse=True)

    lowest = _data(_list_reviews(client, product, sort="lowest", limit=50))
    ratings = [item["rating"] for item in lowest["items"]]
    assert ratings == sorted(ratings)


def test_pagination(client: TestClient, product: str):
    first = _data(_list_reviews(client, product, page=1, limit=1))
    assert len(first["items"]) == 1
    assert first["limit"] == 1
    assert first["total_pages"] == first["total"]
    if first["total"] > 1:
        second = _data(_list_reviews(client, product, page=2, limit=1))
        assert second["items"][0]["id"] != first["items"][0]["id"]


def test_unapproved_reviews_are_hidden(client: TestClient, product: str):
    token, _ = _register(client)
    created = _data(
        client.post(
            f"/api/products/{product}/reviews",
            json={"rating": 5, "comment": "Pending moderation"},
            headers=_headers(token),
        )
    )
    visible = _data(_list_reviews(client, product, limit=50))
    assert any(item["id"] == created["id"] for item in visible["items"])

    # Hide it directly in the DB, confirm exclusion, then restore consistency
    with SessionLocal() as db:
        review = db.get(Review, uuid.UUID(created["id"]))
        review.is_approved = False
        db.commit()
    hidden = _data(_list_reviews(client, product, limit=50))
    assert all(item["id"] != created["id"] for item in hidden["items"])
    assert hidden["summary"]["count"] == visible["summary"]["count"] - 1

    with SessionLocal() as db:
        review = db.get(Review, uuid.UUID(created["id"]))
        review.is_approved = True
        db.commit()
    _assert_aggregates(client, product)


# ---------------------------------------------------------------------------
# Verified purchases
# ---------------------------------------------------------------------------
def test_verified_purchase_badge(client: TestClient, product: str):
    buyer_token, _ = _register(client)
    assert client.post(
        "/api/cart/items",
        json={"product_id": product, "quantity": 1},
        headers=_headers(buyer_token),
    ).status_code == 201
    placed = client.post(
        "/api/orders",
        json={
            "payment_method": "cod",
            "shipping_address": ADDRESS,
        },
        headers=_headers(buyer_token),
    )
    assert placed.status_code == 201, placed.text

    created = client.post(
        f"/api/products/{product}/reviews",
        json={"rating": 5, "comment": "Bought it — approve this"},
        headers=_headers(buyer_token),
    )
    assert created.status_code == 201

    spectator_token, _ = _register(client)
    spectator_review = client.post(
        f"/api/products/{product}/reviews",
        json={"rating": 4, "comment": "Haven't bought it"},
        headers=_headers(spectator_token),
    )
    assert spectator_review.status_code == 201

    data = _data(_list_reviews(client, product, limit=50))
    by_text = {item["comment"]: item for item in data["items"]}
    assert by_text["Bought it — approve this"]["verified"] is True
    assert by_text["Haven't bought it"]["verified"] is False

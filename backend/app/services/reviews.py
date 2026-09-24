"""Product review CRUD + rating aggregation.

`product.rating` / `product.rating_count` are ALWAYS recomputed from approved
review rows on create/update/delete — one source of truth (the seed backfills
rows for the demo catalog so storefront numbers stay realistic).
"""

import math
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppError
from app.models.order import Order, OrderItem
from app.models.review import Review
from app.models.user import User
from app.schemas.review import ReviewCreate, ReviewUpdate
from app.services import products as product_service

SORTS = {
    "newest": (Review.created_at.desc(),),
    "highest": (Review.rating.desc(), Review.created_at.desc()),
    "lowest": (Review.rating.asc(), Review.created_at.desc()),
}


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def recompute_rating(db: Session, product) -> None:
    """Set product.rating/rating_count from the product's approved reviews."""
    ratings = db.scalars(
        select(Review.rating).where(
            Review.product_id == product.id,
            Review.is_approved.is_(True),
        )
    ).all()
    if ratings:
        product.rating = round(sum(ratings) / len(ratings), 1)
        product.rating_count = len(ratings)
    else:
        product.rating = 0
        product.rating_count = 0
    db.add(product)


def _summary(db: Session, product_id: uuid.UUID) -> dict:
    distribution = {star: 0 for star in range(1, 6)}
    total = count = 0
    for star, star_count in db.execute(
        select(Review.rating, func.count(Review.id))
        .where(Review.product_id == product_id, Review.is_approved.is_(True))
        .group_by(Review.rating)
    ).all():
        distribution[int(star)] = int(star_count)
        total += int(star) * int(star_count)
        count += int(star_count)
    return {
        "average": round(total / count, 1) if count else 0,
        "count": count,
        "distribution": distribution,
    }


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
def get_review_product(db: Session, product_id: uuid.UUID):
    """Product for review routes (404/401 semantics shared with the catalog)."""
    return product_service.get_product(db, str(product_id))


def _verified_user_ids(db: Session, product_id: uuid.UUID, user_ids) -> set:
    """Reviewers who bought this product (any non-cancelled order)."""
    if not user_ids:
        return set()
    rows = db.execute(
        select(Order.user_id)
        .join(OrderItem, OrderItem.order_id == Order.id)
        .where(
            OrderItem.product_id == product_id,
            Order.user_id.in_(set(user_ids)),
            Order.status != "cancelled",
        )
        .distinct()
    ).all()
    return {row[0] for row in rows}


def _row(review: Review, viewer: User | None, verified_ids: set) -> dict:
    user = review.user
    return {
        "id": review.id,
        "product_id": review.product_id,
        "rating": review.rating,
        "comment": review.comment,
        "verified": review.user_id in verified_ids,
        "is_mine": viewer is not None and viewer.id == review.user_id,
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
        }
        if user is not None
        else None,
        "created_at": review.created_at,
        "updated_at": review.updated_at,
    }


def list_reviews(
    db: Session,
    product,
    *,
    viewer: User | None,
    page: int = 1,
    limit: int = 10,
    sort: str = "newest",
) -> dict:
    if sort not in SORTS:
        raise AppError(f"Invalid sort '{sort}'", status_code=400)

    base = select(Review).where(
        Review.product_id == product.id,
        Review.is_approved.is_(True),
    )
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.scalars(
        base.options(selectinload(Review.user))
        .order_by(*SORTS[sort])
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    verified_ids = _verified_user_ids(db, product.id, [r.user_id for r in rows])
    return {
        "items": [_row(review, viewer, verified_ids) for review in rows],
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": math.ceil(total / limit) if total else 0,
        "summary": _summary(db, product.id),
        "product": {
            "id": product.id,
            "name": product.name,
            "rating": float(product.rating),
            "rating_count": product.rating_count,
        },
    }


def get_review(db: Session, review_id: uuid.UUID) -> Review:
    review = db.get(Review, review_id)
    if review is None:
        raise AppError("Review not found", status_code=404)
    return review


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------
def create_review(db: Session, product, viewer: User, payload: ReviewCreate) -> Review:
    existing = db.scalar(
        select(Review).where(
            Review.product_id == product.id,
            Review.user_id == viewer.id,
        )
    )
    if existing is not None:
        raise AppError("You have already reviewed this product — edit your review instead", status_code=409)

    review = Review(
        product_id=product.id,
        user_id=viewer.id,
        rating=payload.rating,
        comment=payload.comment.strip() if payload.comment and payload.comment.strip() else None,
        is_approved=True,
    )
    db.add(review)
    db.flush()
    recompute_rating(db, product)
    db.commit()
    db.refresh(review)
    return review


def update_review(db: Session, review: Review, viewer: User, payload: ReviewUpdate) -> Review:
    if review.user_id != viewer.id:
        raise AppError("You can only edit your own review", status_code=403)

    data = payload.model_dump(exclude_unset=True)
    if "rating" in data and data["rating"] is not None:
        review.rating = data["rating"]
    if "comment" in data:
        comment = (data["comment"] or "").strip()
        review.comment = comment or None

    db.add(review)
    db.flush()  # session has autoflush=False — make the edit visible to recompute
    recompute_rating(db, review.product)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review: Review, viewer: User) -> None:
    if review.user_id != viewer.id and viewer.role_name != "admin":
        raise AppError("You can only delete your own review", status_code=403)

    product = review.product
    db.delete(review)
    db.flush()  # remove the row before recompute counts live reviews
    recompute_rating(db, product)
    db.commit()

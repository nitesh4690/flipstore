"""Product review endpoints — public list, signed-in create/edit/delete."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import (
    get_current_active_user,
    get_current_optional_user,
    get_db,
)
from app.schemas.review import ReviewCreate, ReviewUpdate
from app.services import reviews as review_service
from app.utils.responses import ok

router = APIRouter(tags=["reviews"])


@router.get("/products/{product_id}/reviews", response_model=dict)
def list_reviews(
    product_id: uuid.UUID,
    db: Session = Depends(get_db),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=50),
    sort: str = Query(default="newest", description="newest | highest | lowest"),
    viewer=Depends(get_current_optional_user),
):
    """Approved reviews + rating summary (viewer gets `is_mine` flags)."""
    product = review_service.get_review_product(db, product_id)
    result = review_service.list_reviews(
        db, product, viewer=viewer, page=page, limit=limit, sort=sort
    )
    return ok(result)


@router.post(
    "/products/{product_id}/reviews",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
def create_review(
    product_id: uuid.UUID,
    payload: ReviewCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    product = review_service.get_review_product(db, product_id)
    review = review_service.create_review(db, product, user, payload)
    return ok(
        {"id": review.id, "rating": review.rating, "comment": review.comment},
        message="Review published — thanks for sharing!",
    )


@router.patch("/reviews/{review_id}", response_model=dict)
def update_review(
    review_id: uuid.UUID,
    payload: ReviewUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    review = review_service.get_review(db, review_id)
    updated = review_service.update_review(db, review, user, payload)
    return ok(
        {"id": updated.id, "rating": updated.rating, "comment": updated.comment},
        message="Review updated",
    )


@router.delete("/reviews/{review_id}", response_model=dict)
def delete_review(
    review_id: uuid.UUID,
    db: Session = Depends(get_db),
    user=Depends(get_current_active_user),
):
    review = review_service.get_review(db, review_id)
    review_service.delete_review(db, review, user)
    return ok(None, message="Review deleted")

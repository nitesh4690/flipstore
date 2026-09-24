"""User profile endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.dependencies import get_current_active_user, get_db
from app.models.user import User
from app.schemas.auth import UserPublic
from app.schemas.user import ProfileUpdateRequest
from app.services import user as user_service
from app.utils.responses import ok

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=dict)
def get_my_profile(current_user: User = Depends(get_current_active_user)):
    return ok(UserPublic.model_validate(current_user).model_dump())


@router.put("/me", response_model=dict)
def update_my_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    updated = user_service.update_profile(db, current_user, payload)
    return ok(UserPublic.model_validate(updated).model_dump(), message="Profile updated")

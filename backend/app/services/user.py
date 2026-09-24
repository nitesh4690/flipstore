"""User profile business logic."""

from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import ProfileUpdateRequest


def update_profile(db: Session, user: User, payload: ProfileUpdateRequest) -> User:
    """Apply non-empty profile field changes."""
    updates = payload.model_dump(exclude_unset=True, exclude_none=True)

    if "first_name" in updates:
        user.first_name = updates["first_name"].strip()
    if "last_name" in updates:
        user.last_name = updates["last_name"].strip()
    if "phone" in updates:
        user.phone = updates["phone"].strip() if updates["phone"] else None

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

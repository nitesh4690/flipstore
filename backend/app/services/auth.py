"""Authentication business logic (register, login, password resets)."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.role import Role
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.utils.datetime import is_expired

DEFAULT_ROLES = {
    "customer": "Registered storefront customer",
    "admin": "Store administrator with full dashboard access",
}


def get_or_create_role(db: Session, name: str) -> Role:
    """Fetch a role by name, creating it if missing (idempotent)."""
    role = db.scalar(select(Role).where(Role.name == name))
    if role is None:
        role = Role(name=name, description=DEFAULT_ROLES.get(name))
        db.add(role)
        db.flush()
    return role


def register_user(db: Session, payload: RegisterRequest) -> User:
    """Create a customer account. Raises AppError(409) on duplicate email."""
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise AppError("An account with this email already exists", status_code=409)

    customer_role = get_or_create_role(db, "customer")
    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        role_id=customer_role.id,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, payload: LoginRequest) -> User:
    """Verify credentials. Raises AppError(401/403) with generic messages."""
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))

    if user is None or not verify_password(payload.password, user.password_hash):
        raise AppError("Invalid email or password", status_code=401)
    if not user.is_active:
        raise AppError("Your account has been deactivated. Contact support.", status_code=403)
    return user


def issue_token(user: User) -> dict:
    """Build the login/refresh response payload."""
    token, expires_in = create_access_token(user_id=user.id, role=user.role_name)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in,
        "user": user,
    }


def request_password_reset(db: Session, email: str) -> str | None:
    """Generate a short-lived reset token.

    Returns the raw token (caller decides whether to expose it), or None when
    the email does not exist — never reveal which emails are registered.
    """
    user = db.scalar(select(User).where(User.email == email.lower().strip()))
    if user is None or not user.is_active:
        return None

    raw_token = secrets.token_urlsafe(32)
    user.password_reset_token = hashlib.sha256(raw_token.encode()).hexdigest()
    user.password_reset_expires = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()
    return raw_token


def reset_password(db: Session, token: str, new_password: str) -> None:
    """Consume a reset token and set the new password."""
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    user = db.scalar(select(User).where(User.password_reset_token == token_hash))

    if user is None or user.password_reset_expires is None:
        raise AppError("Invalid or expired reset token", status_code=400)
    if is_expired(user.password_reset_expires):
        raise AppError("Invalid or expired reset token", status_code=400)

    user.password_hash = hash_password(new_password)
    user.password_reset_token = None
    user.password_reset_expires = None
    db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    """Verify the current password, then replace it."""
    if not verify_password(current_password, user.password_hash):
        raise AppError("Current password is incorrect", status_code=400)
    user.password_hash = hash_password(new_password)
    db.commit()

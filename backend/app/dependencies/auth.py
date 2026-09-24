"""Authentication/authorization dependencies.

- get_current_user()       -> valid, non-revoked JWT + existing user
- get_current_active_user() -> additionally requires is_active = True
- get_current_admin()       -> additionally requires the admin role
"""

import uuid

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# In-memory token revocation list (jti -> expiry epoch).
# Sufficient for a single process; a Redis/DB store can replace it later.
_revoked_jtis: dict[str, float] = {}


def revoke_token(payload: dict) -> None:
    """Mark a token as revoked until its natural expiry."""
    jti = payload.get("jti")
    exp = float(payload.get("exp", 0))
    if jti:
        _prune_revoked()
        _revoked_jtis[jti] = exp


def _prune_revoked() -> None:
    import time

    now = time.time()
    expired = [jti for jti, exp in _revoked_jtis.items() if exp < now]
    for jti in expired:
        _revoked_jtis.pop(jti, None)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the authenticated user from the Bearer token."""
    payload = decode_access_token(token)

    jti = payload.get("jti")
    if jti and jti in _revoked_jtis:
        raise AppError("Session has been signed out", status_code=401)

    try:
        user_uuid = uuid.UUID(payload["sub"])
    except (ValueError, KeyError) as exc:
        raise AppError("Invalid token", status_code=401) from exc

    user = db.get(User, user_uuid)
    if user is None:
        raise AppError("User not found", status_code=401)
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    """Reject deactivated accounts."""
    if not user.is_active:
        raise AppError("Account is deactivated", status_code=403)
    return user


def get_current_admin(user: User = Depends(get_current_active_user)) -> User:
    """Require the admin role (RBAC guard for /api/admin/*)."""
    if user.role_name != "admin":
        raise AppError("Admin access required", status_code=403)
    return user

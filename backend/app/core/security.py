"""JWT creation/decoding and password hashing helpers."""

import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.core.config import settings
from app.core.exceptions import AppError


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Constant-time verification of a password against its bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except (ValueError, TypeError):
        return False


# ---------------------------------------------------------------------------
# JWT access tokens  (claims: sub = user id, role, jti)
# ---------------------------------------------------------------------------
def create_access_token(
    *,
    user_id: str | uuid.UUID,
    role: str,
    expires_minutes: int | None = None,
    jti: str | None = None,
) -> tuple[str, int]:
    """Create a signed access token. Returns (token, expires_in_seconds)."""
    now = datetime.now(timezone.utc)
    lifetime = timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    expires_at = now + lifetime

    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "jti": jti or str(uuid.uuid4()),
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_access_token(token: str) -> dict:
    """Decode/validate an access token. Raises AppError(401) on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise AppError("Session expired, please sign in again", status_code=401) from exc
    except jwt.InvalidTokenError as exc:
        raise AppError("Invalid or expired token", status_code=401) from exc

    if payload.get("type") != "access" or not payload.get("sub"):
        raise AppError("Invalid token", status_code=401)
    return payload

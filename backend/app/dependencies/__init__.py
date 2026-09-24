"""Reusable FastAPI dependencies (get_db, get_current_user, get_current_admin...)."""

from app.core.database import get_db
from app.dependencies.auth import (
    get_current_active_user,
    get_current_admin,
    get_current_optional_user,
    get_current_user,
    oauth2_scheme,
    oauth2_scheme_optional,
    revoke_token,
)

__all__ = [
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_current_admin",
    "get_current_optional_user",
    "oauth2_scheme",
    "oauth2_scheme_optional",
    "revoke_token",
]

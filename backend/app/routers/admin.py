"""Admin-only endpoints (dashboard stats and management arrive in Phase 6)."""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_admin
from app.models.user import User
from app.utils.responses import ok

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/ping", response_model=dict)
def admin_ping(admin: User = Depends(get_current_admin)):
    """Guarded probe proving RBAC works: customers receive 403."""
    return ok({"email": admin.email, "role": admin.role_name}, message="Admin access OK")

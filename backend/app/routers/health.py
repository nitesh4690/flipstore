"""Health/readiness endpoints (useful for load balancers and smoke tests)."""

from fastapi import APIRouter
from sqlalchemy import text

from app.core.database import engine
from app.utils.responses import ok

router = APIRouter(tags=["Health"])


@router.get("/health")
def health_check():
    """Liveness probe plus a lightweight database ping."""
    db_status = "ok"
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:  # pragma: no cover - depends on infrastructure
        db_status = "unavailable"

    return ok(
        {"status": "healthy", "database": db_status},
        message="Service is running",
    )

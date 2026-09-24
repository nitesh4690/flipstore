"""Pytest bootstrap: isolated SQLite test database.

Environment is set BEFORE any app import so that `app.core.database`
builds its engine against the test database.
"""

import os
import pathlib

TEST_DB_PATH = pathlib.Path(__file__).parent / "test_flipstore.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"
os.environ["ENVIRONMENT"] = "test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """TestClient with a fresh schema for the whole session."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()


@pytest.fixture(scope="session")
def admin_token(client: TestClient) -> str:
    """Create (or reuse) the admin user and return its token."""
    from sqlalchemy import select

    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.role import Role
    from app.models.user import User
    from app.services.auth import issue_token

    with SessionLocal() as db:
        role = db.scalar(select(Role).where(Role.name == "admin"))
        if role is None:
            role = Role(name="admin", description="admin")
            db.add(role)
            db.flush()

        user = db.scalar(select(User).where(User.email == "admin@example.com"))
        if user is None:
            user = User(
                email="admin@example.com",
                password_hash=hash_password("AdminPass123"),
                first_name="Admin",
                last_name="User",
                role_id=role.id,
                is_active=True,
            )
            db.add(user)
            db.commit()

        return issue_token(user)["access_token"]

"""Phase 2 auth tests: registration, login, JWT, RBAC."""

from fastapi.testclient import TestClient


def _register(client: TestClient, email: str = "customer@example.com") -> dict:
    response = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecretPass123",
            "first_name": "Test",
            "last_name": "Customer",
        },
    )
    return response


def test_register_success(client: TestClient):
    response = _register(client)
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["access_token"]
    assert body["data"]["user"]["email"] == "customer@example.com"
    assert body["data"]["user"]["role"] == "customer"


def test_register_duplicate_email(client: TestClient):
    _register(client, "dup@example.com")
    response = _register(client, "dup@example.com")
    assert response.status_code == 409
    assert response.json()["success"] is False


def test_register_short_password_rejected(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "weak@example.com",
            "password": "short",
            "first_name": "Weak",
            "last_name": "Password",
        },
    )
    assert response.status_code == 422  # Pydantic validation


def test_login_success(client: TestClient):
    _register(client, "login@example.com")
    response = client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "SecretPass123"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient):
    _register(client, "wrongpw@example.com")
    response = client.post(
        "/api/auth/login",
        json={"email": "wrongpw@example.com", "password": "WrongPassword999"},
    )
    assert response.status_code == 401
    assert response.json()["message"] == "Invalid email or password"


def test_me_requires_token(client: TestClient):
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_returns_profile(client: TestClient):
    registration = _register(client, "profile@example.com")
    token = registration.json()["data"]["access_token"]
    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["email"] == "profile@example.com"
    assert data["role"] == "customer"


def test_invalid_token_rejected(client: TestClient):
    response = client.get(
        "/api/auth/me", headers={"Authorization": "Bearer not-a-real-token"}
    )
    assert response.status_code == 401


def test_logout_revokes_token(client: TestClient):
    registration = _register(client, "logout@example.com")
    token = registration.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/auth/me", headers=headers).status_code == 200
    assert client.post("/api/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_profile_update(client: TestClient):
    registration = _register(client, "editme@example.com")
    token = registration.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/api/users/me", json={"first_name": "Updated"}, headers=headers
    )
    assert response.status_code == 200
    assert response.json()["data"]["first_name"] == "Updated"


def test_change_password_flow(client: TestClient):
    registration = _register(client, "changepw@example.com")
    token = registration.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.put(
        "/api/auth/change-password",
        json={"current_password": "SecretPass123", "new_password": "NewSecret456"},
        headers=headers,
    )
    assert response.status_code == 200

    # Old password no longer works, new one does
    old = client.post(
        "/api/auth/login",
        json={"email": "changepw@example.com", "password": "SecretPass123"},
    )
    assert old.status_code == 401
    new = client.post(
        "/api/auth/login",
        json={"email": "changepw@example.com", "password": "NewSecret456"},
    )
    assert new.status_code == 200


def test_forgot_and_reset_password(client: TestClient):
    _register(client, "reset@example.com")
    response = client.post("/api/auth/forgot-password", json={"email": "reset@example.com"})
    assert response.status_code == 200
    token = response.json()["data"]["reset_token"]
    assert token  # exposed outside production until email delivery (Phase 7)

    reset = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "BrandNewPass789"},
    )
    assert reset.status_code == 200

    login = client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": "BrandNewPass789"},
    )
    assert login.status_code == 200


def test_admin_route_forbidden_for_customer(client: TestClient):
    registration = _register(client, "notadmin@example.com")
    token = registration.json()["data"]["access_token"]
    response = client.get(
        "/api/admin/ping", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403
    assert response.json()["message"] == "Admin access required"


def test_admin_route_allowed_for_admin(client: TestClient, admin_token: str):
    response = client.get(
        "/api/admin/ping", headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert response.status_code == 200
    assert response.json()["data"]["role"] == "admin"


def test_admin_route_requires_token(client: TestClient):
    assert client.get("/api/admin/ping").status_code == 401

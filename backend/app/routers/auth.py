"""Authentication endpoints: register, login, logout, password reset."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_access_token
from app.dependencies import get_current_user, get_db
from app.dependencies.auth import revoke_token
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserPublic,
)
from app.services import auth as auth_service
from app.utils.responses import ok

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", status_code=201, response_model=dict)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a customer account and return an access token."""
    user = auth_service.register_user(db, payload)
    return ok(
        TokenResponse.model_validate(auth_service.issue_token(user)).model_dump(),
        message="Account created successfully",
    )


@router.post("/login", response_model=dict)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """Verify credentials and issue a JWT access token."""
    user = auth_service.authenticate_user(db, payload)
    return ok(
        TokenResponse.model_validate(auth_service.issue_token(user)).model_dump(),
        message="Signed in successfully",
    )


@router.post("/logout", response_model=dict)
def logout(request: Request, current_user: User = Depends(get_current_user)):
    """Revoke the presented token (client should discard it as well)."""
    header = request.headers.get("authorization", "")
    token = header.removeprefix("Bearer ").strip() if header else ""
    if token:
        revoke_token(decode_access_token(token))
    return ok(None, message="Signed out successfully")


@router.get("/me", response_model=dict)
def me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return ok(UserPublic.model_validate(current_user).model_dump())


@router.post("/forgot-password", response_model=dict)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Start a password reset. Always returns 200 to avoid email enumeration."""
    raw_token = auth_service.request_password_reset(db, payload.email)
    reset_token = None
    if raw_token and settings.ENVIRONMENT != "production":
        # TODO(Phase 7): email this link instead of returning it.
        reset_token = raw_token
    return ok(
        ForgotPasswordResponse(
            message="If an account exists for that email, a reset link has been sent.",
            reset_token=reset_token,
        ).model_dump(),
        message="If an account exists for that email, a reset link has been sent.",
    )


@router.post("/reset-password", response_model=dict)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Consume a reset token and set a new password."""
    auth_service.reset_password(db, payload.token, payload.new_password)
    return ok(None, message="Password has been reset successfully")


@router.put("/change-password", response_model=dict)
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for an authenticated user."""
    auth_service.change_password(
        db, current_user, payload.current_password, payload.new_password
    )
    return ok(None, message="Password changed successfully")

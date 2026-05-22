"""
Auth route handlers.
All business logic delegated to auth_service.
Rate limiting via slowapi.
"""
from fastapi import APIRouter, Depends, Request, Response, Cookie, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.config import get_settings
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    TokenResponse,
    AuthResponse,
    UserResponse,
    MessageResponse,
    TOTPStepResponse,
    TOTPVerifyRequest,
)
from app.services import auth_service

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)

REFRESH_COOKIE_NAME = "faind_refresh_token"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/api/v1/auth",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/v1/auth")


# ── Register ─────────────────────────────────────────────────────────────────

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    await auth_service.register_user(db, data)
    return {"message": "Account created. Please check your email to verify your account."}


# ── Email Verification ────────────────────────────────────────────────────────

@router.post("/verify-email", response_model=AuthResponse)
@limiter.limit("10/minute")
async def verify_email(
    request: Request,
    response: Response,
    data: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    user = await auth_service.verify_email(db, data.email, data.code)

    ua = request.headers.get("user-agent")
    ip = get_remote_address(request)
    access_token, refresh_token = auth_service.create_session(db, user, ua, ip)
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("3/minute")
async def resend_verification(
    request: Request,
    data: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    await auth_service.resend_verification(db, data.email)
    return {"message": "If an unverified account exists for that email, a new code has been sent."}


# ── Login ─────────────────────────────────────────────────────────────────────

@router.post("/login")
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    user = auth_service.authenticate_user(db, data.email, data.password)

    from app.models.user import UserRole
    import pyotp
    from app.core.security import create_access_token
    from datetime import timedelta

    # Root Admin requires TOTP — issue a short-lived session token first
    if user.role == UserRole.ROOT_ADMIN and user.totp_enabled:
        # A short-lived token scoped only for the TOTP step
        session_token = create_access_token(
            {"sub": str(user.id), "role": user.role.value, "totp_pending": True},
            expires_delta=timedelta(minutes=5),
        )
        return TOTPStepResponse(session_token=session_token)

    ua = request.headers.get("user-agent")
    ip = get_remote_address(request)
    access_token, refresh_token = auth_service.create_session(db, user, ua, ip)
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


# ── Root Admin TOTP Step ───────────────────────────────────────────────────────

@router.post("/totp-verify", response_model=AuthResponse)
@limiter.limit("5/minute")
async def totp_verify(
    request: Request,
    response: Response,
    data: TOTPVerifyRequest,
    db: Session = Depends(get_db),
):
    import pyotp
    from app.core.security import verify_access_token, create_access_token
    from app.services.auth_service import get_user_by_id

    payload = verify_access_token(data.session_token)
    if not payload or not payload.get("totp_pending"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        )

    user = get_user_by_id(db, payload.get("sub"))
    if not user or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="2FA not configured for this account.",
        )

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(data.totp_code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code.",
        )

    ua = request.headers.get("user-agent")
    ip = get_remote_address(request)
    access_token, refresh_token = auth_service.create_session(db, user, ua, ip)
    _set_refresh_cookie(response, refresh_token)

    return AuthResponse(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


# ── Token Refresh ─────────────────────────────────────────────────────────────

@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    faind_refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    if not faind_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token found.",
        )

    ua = request.headers.get("user-agent")
    ip = get_remote_address(request)
    access_token, new_refresh_token = auth_service.refresh_session(
        db, faind_refresh_token, ua, ip
    )
    _set_refresh_cookie(response, new_refresh_token)

    return TokenResponse(access_token=access_token)


# ── Logout ────────────────────────────────────────────────────────────────────

@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    db: Session = Depends(get_db),
    faind_refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    current_user: User = Depends(get_current_user),
):
    if faind_refresh_token:
        auth_service.logout(db, faind_refresh_token)
    _clear_refresh_cookie(response)
    return {"message": "Logged out successfully."}


# ── Forgot / Reset Password ───────────────────────────────────────────────────

@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    await auth_service.request_password_reset(db, data.email)
    return {"message": "If an account exists for that email, a reset code has been sent."}


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    response: Response,
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
    faind_refresh_token: Optional[str] = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
):
    await auth_service.reset_password(db, data.email, data.code, data.new_password)
    _clear_refresh_cookie(response)
    return {"message": "Password reset successfully. Please log in with your new password."}


# ── Current User ──────────────────────────────────────────────────────────────

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)

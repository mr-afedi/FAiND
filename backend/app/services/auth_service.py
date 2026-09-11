"""
Authentication business logic.
All auth decisions live here — route handlers only handle HTTP concerns.
"""
import random
import hashlib
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.models.user import User, AccountStatus, UserRole
from app.models.university import University
from app.models.email_verification import EmailVerification
from app.models.refresh_token import RefreshToken
from app.models.password_reset import PasswordReset
from app.schemas.auth import RegisterRequest, LoginRequest
from app.utils.email import send_verification_email, send_password_reset_email

settings = get_settings()


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ── University helpers ──────────────────────────────────────────────────────


def get_university_by_domain(db: Session, domain: str) -> Optional[University]:
    return db.query(University).filter(
        University.email_domain == domain,
        University.is_active == True,
    ).first()


def _extract_domain(email: str) -> str:
    return email.split("@")[1].lower()


# ── Registration ────────────────────────────────────────────────────────────


async def register_user(db: Session, data: RegisterRequest) -> User:
    domain = _extract_domain(data.email)
    university = get_university_by_domain(db, domain)
    if not university:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please use your GCTU student email to register.",
        )

    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    if db.query(User).filter(User.username == data.username.lower()).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This username is already taken.",
        )

    user = User(
        university_id=university.id,
        email=data.email.lower(),
        username=data.username.lower(),
        full_name=data.full_name.strip(),
        hashed_password=hash_password(data.password),
        student_id=data.student_id.strip() if data.student_id else None,
        status=AccountStatus.UNVERIFIED,
        role=UserRole.USER,
    )
    db.add(user)
    db.flush()  # get user.id before commit

    await _create_and_send_verification(db, user)
    db.commit()
    db.refresh(user)
    return user


# ── Email Verification ──────────────────────────────────────────────────────


async def _create_and_send_verification(db: Session, user: User) -> EmailVerification:
    # Invalidate any existing unused codes
    db.query(EmailVerification).filter(
        EmailVerification.user_id == user.id,
        EmailVerification.is_used == False,
    ).update({"is_used": True})

    code = _generate_code()
    verification = EmailVerification(
        user_id=user.id,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
    )
    db.add(verification)
    db.flush()

    await send_verification_email(user.email, user.full_name, code)
    return verification


async def verify_email(db: Session, email: str, code: str) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user.status == AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified.",
        )

    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == user.id,
            EmailVerification.is_used == False,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code. Please request a new one.",
        )

    if verification.failed_attempts >= 5:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please request a new verification code.",
        )

    if verification.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new one.",
        )

    if verification.code != code:
        verification.failed_attempts += 1
        db.commit()
        remaining = 5 - verification.failed_attempts
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid code. {remaining} attempt(s) remaining.",
        )

    verification.is_used = True
    user.status = AccountStatus.ACTIVE
    db.commit()
    db.refresh(user)
    return user


async def resend_verification(db: Session, email: str) -> None:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        # Return silently — don't reveal whether email exists
        return

    if user.status == AccountStatus.ACTIVE:
        return

    # Check cooldown — don't allow resend if one was sent in the last 60 seconds
    recent = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.user_id == user.id,
            EmailVerification.is_used == False,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    if recent:
        age = (datetime.now(timezone.utc) - recent.created_at).total_seconds()
        if age < 60:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Please wait before requesting a new code.",
            )

    await _create_and_send_verification(db, user)
    db.commit()


# ── Login ───────────────────────────────────────────────────────────────────


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email.lower()).first()

    # Constant-time response to prevent user enumeration
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )

    if user.status == AccountStatus.UNVERIFIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email before logging in.",
        )

    if user.status == AccountStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been suspended. Contact support if you believe this is an error.",
        )

    if user.status == AccountStatus.DELETED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found.",
        )

    return user


def create_session(
    db: Session, user: User, user_agent: Optional[str] = None, ip: Optional[str] = None
) -> tuple[str, str]:
    """Create access + refresh tokens and persist the refresh token hash."""
    payload = {"sub": str(user.id), "role": user.role.value}
    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)

    token_hash = _hash_token(refresh_token)
    rt = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        user_agent=user_agent,
        ip_address=ip,
    )
    db.add(rt)

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    return access_token, refresh_token


# ── Token Refresh ────────────────────────────────────────────────────────────


def refresh_session(
    db: Session, raw_refresh_token: str, user_agent: Optional[str] = None, ip: Optional[str] = None
) -> tuple[str, str]:
    """Validate incoming refresh token, revoke it, and issue a new pair."""
    payload = verify_refresh_token(raw_refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    user_id = payload.get("sub")
    token_hash = _hash_token(raw_refresh_token)

    stored = db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash,
        RefreshToken.is_revoked == False,
    ).first()

    if not stored or str(stored.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token not recognised. Please log in again.",
        )

    if stored.expires_at < datetime.now(timezone.utc):
        stored.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired. Please log in again.",
        )

    user = db.query(User).filter(User.id == stored.user_id).first()
    if not user or user.status not in (AccountStatus.ACTIVE, ):
        stored.is_revoked = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer valid.",
        )

    # Revoke used token (rotation)
    stored.is_revoked = True
    db.flush()

    return create_session(db, user, user_agent, ip)


# ── Logout ───────────────────────────────────────────────────────────────────


def logout(db: Session, raw_refresh_token: str) -> None:
    """Revoke the provided refresh token."""
    if not raw_refresh_token:
        return
    token_hash = _hash_token(raw_refresh_token)
    db.query(RefreshToken).filter(
        RefreshToken.token_hash == token_hash
    ).update({"is_revoked": True})
    db.commit()


def logout_all(db: Session, user_id) -> None:
    """Revoke all refresh tokens for a user (e.g. on password change)."""
    db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.is_revoked == False,
    ).update({"is_revoked": True})
    db.commit()


# ── Password Reset ────────────────────────────────────────────────────────────


async def request_password_reset(db: Session, email: str) -> None:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user or user.status not in (AccountStatus.ACTIVE, AccountStatus.UNVERIFIED):
        # Silent — don't reveal whether email exists
        return

    # Invalidate existing unused resets
    db.query(PasswordReset).filter(
        PasswordReset.user_id == user.id,
        PasswordReset.is_used == False,
    ).update({"is_used": True})

    code = _generate_code()
    reset = PasswordReset(
        user_id=user.id,
        code=code,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(reset)
    db.commit()

    await send_password_reset_email(user.email, user.full_name, code)


async def reset_password(
    db: Session, email: str, code: str, new_password: str
) -> None:
    user = db.query(User).filter(User.email == email.lower()).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid reset request.")

    reset = (
        db.query(PasswordReset)
        .filter(
            PasswordReset.user_id == user.id,
            PasswordReset.is_used == False,
        )
        .order_by(PasswordReset.created_at.desc())
        .first()
    )

    if not reset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active password reset code. Please request a new one.",
        )

    if reset.expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset code has expired. Please request a new one.",
        )

    if reset.code != code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid reset code.",
        )

    reset.is_used = True
    user.hashed_password = hash_password(new_password)
    db.flush()

    # Invalidate all existing sessions
    logout_all(db, user.id)
    db.commit()


# ── Current User ─────────────────────────────────────────────────────────────


def get_user_by_id(db: Session, user_id) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

"""
User profile business logic.
All profile, settings, and account management live here.
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import verify_password, hash_password
from app.models.user import User, AccountStatus
from app.models.university import University
from app.schemas.user import (
    PublicProfileResponse,
    OwnProfileResponse,
    UpdateProfileRequest,
    ChangePasswordRequest,
    UpdateSettingsRequest,
    trust_tier,
)
from app.services.auth_service import logout_all


def _member_since(created_at: datetime) -> str:
    return created_at.strftime("%B %Y")


def _build_public_profile(user: User, university: University) -> PublicProfileResponse:
    return PublicProfileResponse(
        username=user.username,
        full_name=user.full_name,
        profile_photo_url=user.profile_photo_url,
        trust_tier=trust_tier(user.trust_score),
        university_short_name=university.short_name,
        member_since=_member_since(user.created_at),
        items_returned_count=0,   # Feature M will populate this
        tips_received_count=0,    # Feature Q will populate this
    )


def _build_own_profile(user: User, university: University) -> OwnProfileResponse:
    return OwnProfileResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        student_id=user.student_id,
        profile_photo_url=user.profile_photo_url,
        role=user.role.value,
        status=user.status.value,
        trust_score=user.trust_score,
        trust_tier=trust_tier(user.trust_score),
        university_id=user.university_id,
        university_short_name=university.short_name,
        civic_alerts_enabled=user.civic_alerts_enabled,
        push_notifications_enabled=user.push_notifications_enabled,
        email_notifications_enabled=user.email_notifications_enabled,
        member_since=_member_since(user.created_at),
    )


# ── Read ──────────────────────────────────────────────────────────────────────

def get_own_profile(db: Session, user: User) -> OwnProfileResponse:
    university = db.query(University).filter(University.id == user.university_id).first()
    return _build_own_profile(user, university)


def get_public_profile(db: Session, username: str) -> PublicProfileResponse:
    user = db.query(User).filter(
        User.username == username.lower(),
        User.status == AccountStatus.ACTIVE,
    ).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    university = db.query(University).filter(University.id == user.university_id).first()
    return _build_public_profile(user, university)


# ── Update profile ────────────────────────────────────────────────────────────

def update_profile(db: Session, user: User, data: UpdateProfileRequest) -> OwnProfileResponse:
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.student_id is not None:
        user.student_id = data.student_id.strip() or None
    if data.profile_photo_url is not None:
        user.profile_photo_url = data.profile_photo_url or None
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    university = db.query(University).filter(University.id == user.university_id).first()
    return _build_own_profile(user, university)


# ── Change password ───────────────────────────────────────────────────────────

def change_password(db: Session, user: User, data: ChangePasswordRequest) -> None:
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password.",
        )
    user.hashed_password = hash_password(data.new_password)
    user.updated_at = datetime.now(timezone.utc)
    db.flush()
    logout_all(db, user.id)
    db.commit()


# ── Update notification settings ─────────────────────────────────────────────

def update_settings(db: Session, user: User, data: UpdateSettingsRequest) -> OwnProfileResponse:
    if data.civic_alerts_enabled is not None:
        user.civic_alerts_enabled = data.civic_alerts_enabled
    if data.push_notifications_enabled is not None:
        user.push_notifications_enabled = data.push_notifications_enabled
    if data.email_notifications_enabled is not None:
        user.email_notifications_enabled = data.email_notifications_enabled
    user.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(user)
    university = db.query(University).filter(University.id == user.university_id).first()
    return _build_own_profile(user, university)


# ── Delete account ────────────────────────────────────────────────────────────

def delete_account(db: Session, user: User, password: str) -> None:
    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password.",
        )
    user.status = AccountStatus.DELETED
    user.email = f"deleted_{user.id}@deleted.faind"   # Free up the email
    user.username = f"deleted_{user.id}"               # Free up the username
    user.updated_at = datetime.now(timezone.utc)
    db.flush()
    logout_all(db, user.id)
    db.commit()

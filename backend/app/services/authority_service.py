"""
Authority authentication — Section 16.
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import create_access_token, hash_password, verify_password
from app.models.authority import Authority
from app.models.authority_otp import AuthorityOtp
from app.models.drop_point import DropPoint
from app.models.item import Item, ItemType
from app.models.admin_log import AdminActionType
from app.models.user import User
from app.schemas.authority import (
    AUTHORITY_EMAIL_DOMAIN,
    AuthorityListItem,
    AuthorityProfileResponse,
    AuthorityScopedItemResponse,
    CreateAuthorityRequest,
)
from app.utils.email import send_authority_otp_email

OTP_EXPIRE_MINUTES = 10
OTP_SESSION_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_otp_code() -> str:
    return f"{random.randint(0, 999999):06d}"


def get_authority_by_id(db: Session, authority_id: uuid.UUID) -> Authority | None:
    return (
        db.query(Authority)
        .options(joinedload(Authority.drop_point))
        .filter(Authority.id == authority_id)
        .first()
    )


def _validate_email_domain(email: str) -> str:
    normalized = email.strip().lower()
    if not normalized.endswith(AUTHORITY_EMAIL_DOMAIN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authority email must be a {AUTHORITY_EMAIL_DOMAIN} address.",
        )
    return normalized


def authenticate_authority(db: Session, email: str, password: str) -> Authority:
    normalized = _validate_email_domain(email)
    authority = (
        db.query(Authority)
        .options(joinedload(Authority.drop_point))
        .filter(Authority.email == normalized)
        .first()
    )
    if not authority or not verify_password(password, authority.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not authority.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This authority account has been deactivated.",
        )
    return authority


async def start_authority_login(db: Session, email: str, password: str) -> str:
    authority = authenticate_authority(db, email, password)

    db.query(AuthorityOtp).filter(
        AuthorityOtp.authority_id == authority.id,
        AuthorityOtp.is_used.is_(False),
    ).update({"is_used": True})

    code = _generate_otp_code()
    otp = AuthorityOtp(
        authority_id=authority.id,
        code=code,
        expires_at=_now() + timedelta(minutes=OTP_EXPIRE_MINUTES),
    )
    db.add(otp)
    db.flush()

    await send_authority_otp_email(authority.email, code)

    session_token = create_access_token(
        {
            "sub": str(authority.id),
            "role": "authority",
            "otp_pending": True,
        },
        expires_delta=timedelta(minutes=OTP_SESSION_MINUTES),
    )
    return session_token


def verify_authority_otp(db: Session, session_token_payload: dict, code: str) -> str:
    authority_id = session_token_payload.get("sub")
    if not authority_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    authority = get_authority_by_id(db, uuid.UUID(authority_id))
    if not authority or not authority.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")

    otp = (
        db.query(AuthorityOtp)
        .filter(
            AuthorityOtp.authority_id == authority.id,
            AuthorityOtp.is_used.is_(False),
        )
        .order_by(AuthorityOtp.created_at.desc())
        .first()
    )
    if not otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code. Please sign in again.",
        )
    if otp.failed_attempts >= MAX_OTP_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed attempts. Please sign in again.",
        )
    if otp.expires_at < _now():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please sign in again.",
        )
    if otp.code != code.strip():
        otp.failed_attempts += 1
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid verification code.",
        )

    otp.is_used = True
    return create_access_token(
        {
            "sub": str(authority.id),
            "role": "authority",
            "drop_point_id": str(authority.drop_point_id),
            "university_id": str(authority.university_id),
        }
    )


def build_authority_profile(authority: Authority) -> AuthorityProfileResponse:
    drop_point_name = authority.drop_point.name if authority.drop_point else "Unknown"
    return AuthorityProfileResponse(
        id=authority.id,
        email=authority.email,
        university_id=authority.university_id,
        drop_point_id=authority.drop_point_id,
        drop_point_name=drop_point_name,
        is_active=authority.is_active,
        created_at=authority.created_at,
    )


def get_scoped_found_item(
    db: Session,
    authority: Authority,
    item_id: uuid.UUID,
) -> AuthorityScopedItemResponse:
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    if item.drop_point_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    if item.drop_point_id != authority.drop_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This item belongs to a different drop point.",
        )
    return AuthorityScopedItemResponse(
        id=item.id,
        status=item.status.value,
        category=item.category.value,
        public_description=item.public_description,
        drop_point_id=item.drop_point_id,
    )


def create_authority_account(
    db: Session,
    payload: CreateAuthorityRequest,
    *,
    allowed_drop_point_ids: set[uuid.UUID] | None = None,
    actor: User | None = None,
) -> AuthorityListItem:
    if allowed_drop_point_ids is not None:
        if payload.drop_point_id not in allowed_drop_point_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This drop point is outside your assigned scope.",
            )
    email = _validate_email_domain(payload.email)
    if db.query(Authority).filter(Authority.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An authority with this email already exists.",
        )

    drop_point = db.query(DropPoint).filter(DropPoint.id == payload.drop_point_id).first()
    if not drop_point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop point not found.")

    existing = (
        db.query(Authority)
        .filter(Authority.drop_point_id == payload.drop_point_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This drop point already has an authority account.",
        )

    authority = Authority(
        email=email,
        hashed_password=hash_password(payload.password),
        university_id=drop_point.university_id,
        drop_point_id=drop_point.id,
        is_active=True,
    )
    db.add(authority)
    db.flush()
    authority.drop_point = drop_point

    if actor:
        from app.services.admin_dashboard_service import log_action

        log_action(
            db,
            admin=actor,
            action=AdminActionType.AUTHORITY_CREATE,
            target_type="authority",
            target_id=authority.id,
            detail={
                "email": authority.email,
                "drop_point_id": str(authority.drop_point_id),
                "drop_point_name": drop_point.name,
            },
        )

    from app.services import admin_notification_service

    admin_notification_service.notify_admins_authority_created(
        db,
        authority_id=authority.id,
        email=authority.email,
        drop_point_name=drop_point.name,
    )

    return _authority_to_list_item(authority)


def list_authority_accounts(db: Session) -> list[AuthorityListItem]:
    rows = (
        db.query(Authority)
        .options(joinedload(Authority.drop_point))
        .order_by(Authority.created_at.desc())
        .all()
    )
    return [_authority_to_list_item(row) for row in rows]


def list_authority_accounts_for_drop_points(
    db: Session,
    drop_point_ids: set[uuid.UUID],
) -> list[AuthorityListItem]:
    if not drop_point_ids:
        return []
    rows = (
        db.query(Authority)
        .options(joinedload(Authority.drop_point))
        .filter(Authority.drop_point_id.in_(drop_point_ids))
        .order_by(Authority.created_at.desc())
        .all()
    )
    return [_authority_to_list_item(row) for row in rows]


def _authority_to_list_item(authority: Authority) -> AuthorityListItem:
    return AuthorityListItem(
        id=authority.id,
        email=authority.email,
        university_id=authority.university_id,
        drop_point_id=authority.drop_point_id,
        drop_point_name=authority.drop_point.name if authority.drop_point else "Unknown",
        is_active=authority.is_active,
        created_at=authority.created_at,
    )


def _get_authority_or_404(db: Session, authority_id: uuid.UUID) -> Authority:
    authority = (
        db.query(Authority)
        .options(joinedload(Authority.drop_point))
        .filter(Authority.id == authority_id)
        .first()
    )
    if not authority:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Authority not found.")
    return authority


def set_authority_active(
    db: Session,
    authority_id: uuid.UUID,
    *,
    active: bool,
    allowed_drop_point_ids: set[uuid.UUID] | None = None,
    actor: User | None = None,
) -> AuthorityListItem:
    authority = _get_authority_or_404(db, authority_id)
    if allowed_drop_point_ids is not None:
        if authority.drop_point_id not in allowed_drop_point_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This authority is outside your assigned scope.",
            )

    authority.is_active = active
    authority.updated_at = _now()

    if actor:
        from app.services.admin_dashboard_service import log_action

        log_action(
            db,
            admin=actor,
            action=AdminActionType.AUTHORITY_ACTIVATE if active else AdminActionType.AUTHORITY_DEACTIVATE,
            target_type="authority",
            target_id=authority.id,
            detail={
                "email": authority.email,
                "drop_point_id": str(authority.drop_point_id),
            },
        )

    if not active:
        from app.services import admin_notification_service

        admin_notification_service.notify_admins_authority_deactivated(
            db,
            authority_id=authority.id,
            email=authority.email,
            drop_point_name=authority.drop_point.name if authority.drop_point else "Unknown",
        )

    return _authority_to_list_item(authority)


def reassign_authority(
    db: Session,
    authority_id: uuid.UUID,
    new_drop_point_id: uuid.UUID,
    actor: User,
) -> AuthorityListItem:
    authority = _get_authority_or_404(db, authority_id)
    if authority.drop_point_id == new_drop_point_id:
        return _authority_to_list_item(authority)

    new_drop_point = db.query(DropPoint).filter(DropPoint.id == new_drop_point_id).first()
    if not new_drop_point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop point not found.")
    if new_drop_point.university_id != authority.university_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Drop point must belong to the same university.",
        )

    existing = (
        db.query(Authority)
        .filter(Authority.drop_point_id == new_drop_point_id, Authority.id != authority.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The target drop point already has an authority account.",
        )

    old_drop_point_id = authority.drop_point_id
    old_name = authority.drop_point.name if authority.drop_point else "Unknown"
    authority.drop_point_id = new_drop_point_id
    authority.updated_at = _now()
    authority.drop_point = new_drop_point
    db.flush()

    from app.services.admin_dashboard_service import log_action

    log_action(
        db,
        admin=actor,
        action=AdminActionType.AUTHORITY_REASSIGN,
        target_type="authority",
        target_id=authority.id,
        detail={
            "email": authority.email,
            "from_drop_point_id": str(old_drop_point_id),
            "from_drop_point_name": old_name,
            "to_drop_point_id": str(new_drop_point_id),
            "to_drop_point_name": new_drop_point.name,
        },
    )
    return _authority_to_list_item(authority)


def reset_authority_password(
    db: Session,
    authority_id: uuid.UUID,
    new_password: str,
    *,
    allowed_drop_point_ids: set[uuid.UUID] | None = None,
) -> AuthorityListItem:
    authority = _get_authority_or_404(db, authority_id)
    if allowed_drop_point_ids is not None:
        if authority.drop_point_id not in allowed_drop_point_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This authority is outside your assigned scope.",
            )
    authority.hashed_password = hash_password(new_password)
    authority.updated_at = _now()
    return _authority_to_list_item(authority)

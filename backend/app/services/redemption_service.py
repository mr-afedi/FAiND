"""
Redemption service — Section 12.4 (W12).
"""
from __future__ import annotations

import logging
import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.admin_log import AdminActionType, AdminLog
from app.models.redemption_code import RedemptionCode, RedemptionCodeStatus
from app.models.user import User
from app.schemas.redemption import (
    RedeemTokensRequest,
    RedeemTokensResponse,
    RedemptionLookupResponse,
    RedemptionOwnerInfo,
)
from app.services import token_service

logger = logging.getLogger(__name__)

REDEMPTION_CODE_EXPIRY_DAYS = 30
_CODE_ALPHABET = string.ascii_uppercase + string.digits


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_code(code: str) -> str:
    return code.strip().upper()


def _generate_unique_code(db: Session) -> str:
    for _ in range(20):
        suffix = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(6))
        candidate = f"FAIND-{suffix}"
        exists = (
            db.query(RedemptionCode.id)
            .filter(RedemptionCode.code == candidate)
            .first()
        )
        if not exists:
            return candidate
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Could not generate a redemption code. Please try again.",
    )


def _owner_info(user: User) -> RedemptionOwnerInfo:
    return RedemptionOwnerInfo(
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
    )


def _to_lookup_response(
    row: RedemptionCode,
    owner: User,
    *,
    message: str,
) -> RedemptionLookupResponse:
    return RedemptionLookupResponse(
        code=row.code,
        token_amount=row.token_amount,
        status=row.status.value,
        owner=_owner_info(owner),
        created_at=row.created_at,
        expires_at=row.expires_at,
        redeemed_at=row.redeemed_at,
        message=message,
    )


def _expire_code(db: Session, row: RedemptionCode) -> None:
    if row.status != RedemptionCodeStatus.ACTIVE:
        return
    row.status = RedemptionCodeStatus.EXPIRED
    token_service.record_redemption_refund(db, row.user_id, row.token_amount)
    logger.info(
        "redemption code expired id=%s user=%s amount=%s",
        row.id,
        row.user_id,
        row.token_amount,
    )


def create_redemption_code(
    db: Session,
    user: User,
    payload: RedeemTokensRequest,
) -> RedeemTokensResponse:
    balance = token_service.get_user_token_balance(db, user.id)
    if payload.token_amount > balance:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Insufficient balance. You have {balance} tokens.",
        )

    now = _now()
    code = _generate_unique_code(db)
    row = RedemptionCode(
        user_id=user.id,
        token_amount=payload.token_amount,
        code=code,
        status=RedemptionCodeStatus.ACTIVE,
        created_at=now,
        expires_at=now + timedelta(days=REDEMPTION_CODE_EXPIRY_DAYS),
    )
    db.add(row)
    token_service.record_redemption_debit(db, user.id, payload.token_amount)
    db.flush()

    balance_after = token_service.get_user_token_balance(db, user.id)
    return RedeemTokensResponse(
        code=code,
        token_amount=payload.token_amount,
        expires_at=row.expires_at,
        balance_after=balance_after,
    )


def lookup_and_redeem_code(
    db: Session,
    code: str,
    *,
    admin: User | None = None,
    supervisor=None,
) -> RedemptionLookupResponse:
    if not admin and not supervisor:
        raise ValueError("Redemption actor required.")
    if admin and supervisor:
        raise ValueError("Only one redemption actor allowed.")
    normalized = _normalize_code(code)
    row = (
        db.query(RedemptionCode)
        .filter(RedemptionCode.code == normalized)
        .with_for_update()
        .first()
    )
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Redemption code not found.",
        )

    owner = db.query(User).filter(User.id == row.user_id).one()
    now = _now()

    if row.status == RedemptionCodeStatus.REDEEMED:
        return _to_lookup_response(
            row,
            owner,
            message="This code has already been redeemed.",
        )

    if row.status == RedemptionCodeStatus.EXPIRED:
        return _to_lookup_response(
            row,
            owner,
            message="This code has expired. Tokens were refunded to the user.",
        )

    if row.expires_at <= now:
        _expire_code(db, row)
        db.flush()
        return _to_lookup_response(
            row,
            owner,
            message="This code has expired. Tokens were refunded to the user.",
        )

    row.status = RedemptionCodeStatus.REDEEMED
    row.redeemed_at = now
    row.redeemed_by_admin_id = admin.id if admin else None
    actor_detail: dict[str, str] = {
        "code": row.code,
        "token_amount": row.token_amount,
        "user_id": str(row.user_id),
    }
    if supervisor:
        actor_detail["supervisor_id"] = str(supervisor.id)
    db.add(
        AdminLog(
            admin_id=admin.id if admin else None,
            action=AdminActionType.REDEMPTION_REDEEMED,
            target_type="redemption_code",
            target_id=row.id,
            detail=actor_detail,
        )
    )
    db.flush()
    actor_label = admin.id if admin else supervisor.id
    logger.info(
        "redemption code redeemed id=%s actor=%s amount=%s",
        row.id,
        actor_label,
        row.token_amount,
    )
    from app.services import admin_notification_service

    admin_notification_service.notify_admins_redemption_used(
        db,
        redemption_code_id=row.id,
        code=row.code,
        token_amount=row.token_amount,
    )
    return _to_lookup_response(
        row,
        owner,
        message="Code redeemed successfully.",
    )


def warn_expiring_redemption_codes(db: Session) -> int:
    """Daily job — notify users 3 days before redemption code expiry (Section 14.1)."""
    from app.services import notification_service

    now = _now()
    soon = now + timedelta(days=3)
    rows = (
        db.query(RedemptionCode)
        .filter(
            RedemptionCode.status == RedemptionCodeStatus.ACTIVE,
            RedemptionCode.expiry_warning_sent_at.is_(None),
            RedemptionCode.expires_at <= soon,
            RedemptionCode.expires_at > now,
        )
        .all()
    )
    for row in rows:
        notification_service.notify_redemption_expiring_soon(
            db,
            user_id=row.user_id,
            code=row.code,
            token_amount=row.token_amount,
        )
        row.expiry_warning_sent_at = now
    return len(rows)


def expire_stale_redemption_codes(db: Session) -> int:
    """Daily job — expire unused codes past 30 days and refund tokens (Section 12.4)."""
    now = _now()
    stale = (
        db.query(RedemptionCode)
        .filter(
            RedemptionCode.status == RedemptionCodeStatus.ACTIVE,
            RedemptionCode.expires_at < now,
        )
        .all()
    )
    count = 0
    for row in stale:
        _expire_code(db, row)
        count += 1
    return count

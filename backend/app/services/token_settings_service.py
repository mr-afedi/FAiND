"""
Token settings — Section 12.1 configurable values (W11).
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.admin_log import AdminActionType, AdminLog
from app.models.token_ledger import TokenLedgerReason
from app.models.token_settings import TokenSettings
from app.models.user import User
from app.schemas.token import TokenSettingsResponse, TokenSettingsUpdate

_DEFAULTS = {
    "found_item_posted": 10,
    "drop_off_on_time": 40,
    "drop_off_late": 20,
    "item_claimed": 10,
}


def get_settings(db: Session) -> TokenSettings:
    row = db.query(TokenSettings).filter(TokenSettings.id == 1).first()
    if row:
        return row
    row = TokenSettings(id=1, **_DEFAULTS)
    db.add(row)
    db.flush()
    return row


def amount_for_reason(db: Session, reason: TokenLedgerReason) -> int:
    settings = get_settings(db)
    mapping = {
        TokenLedgerReason.FOUND_ITEM_POSTED: settings.found_item_posted,
        TokenLedgerReason.DROP_OFF_ON_TIME: settings.drop_off_on_time,
        TokenLedgerReason.DROP_OFF_LATE: settings.drop_off_late,
        TokenLedgerReason.ITEM_CLAIMED: settings.item_claimed,
    }
    if reason not in mapping:
        raise ValueError(f"No configured token amount for reason {reason}")
    return mapping[reason]


def to_response(settings: TokenSettings) -> TokenSettingsResponse:
    return TokenSettingsResponse(
        found_item_posted=settings.found_item_posted,
        drop_off_on_time=settings.drop_off_on_time,
        drop_off_late=settings.drop_off_late,
        item_claimed=settings.item_claimed,
        updated_at=settings.updated_at,
    )


def update_settings(
    db: Session,
    admin: User,
    payload: TokenSettingsUpdate,
) -> TokenSettingsResponse:
    settings = get_settings(db)
    changes: dict[str, dict[str, int]] = {}

    for field in ("found_item_posted", "drop_off_on_time", "drop_off_late", "item_claimed"):
        value = getattr(payload, field)
        if value is not None:
            if value < 0:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"{field} cannot be negative.",
                )
            old = getattr(settings, field)
            if old != value:
                changes[field] = {"from": old, "to": value}
                setattr(settings, field, value)

    if not changes:
        return to_response(settings)

    settings.updated_by_id = admin.id
    settings.updated_at = datetime.now(timezone.utc)
    db.add(
        AdminLog(
            admin_id=admin.id,
            action=AdminActionType.TOKEN_SETTINGS_UPDATE,
            target_type="token_settings",
            target_id=None,
            detail=changes,
        )
    )
    db.flush()
    return to_response(settings)

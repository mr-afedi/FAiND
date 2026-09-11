"""
Token service — Section 12.1 / 12.2, Section 9.3 escrow (W5).
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemStatus
from app.models.token_escrow import TokenEscrow, TokenEscrowEntry
from app.models.token_ledger import TokenLedger, TokenLedgerReason
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.schemas.token import TokenEscrowInfo
from app.services import auth_service, token_settings_service

logger = logging.getLogger(__name__)

ESCROW_EXPIRY_DAYS = 7


@dataclass
class EscrowAwardResult:
    escrow_token: Optional[str]
    pending_total: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_escrow_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _escrow_total(escrow: TokenEscrow) -> int:
    return sum(entry.delta for entry in escrow.entries)


def get_user_token_balance(db: Session, user_id: uuid.UUID) -> int:
    total = (
        db.query(func.coalesce(func.sum(TokenLedger.delta), 0))
        .filter(TokenLedger.user_id == user_id)
        .scalar()
    )
    return int(total or 0)


def list_user_ledger_entries(
    db: Session,
    user_id: uuid.UUID,
    *,
    limit: int = 20,
) -> list[TokenLedger]:
    return (
        db.query(TokenLedger)
        .filter(TokenLedger.user_id == user_id)
        .order_by(TokenLedger.created_at.desc())
        .limit(limit)
        .all()
    )


def record_redemption_debit(db: Session, user_id: uuid.UUID, amount: int) -> None:
    _credit_ledger(
        db,
        user_id=user_id,
        delta=-amount,
        reason=TokenLedgerReason.REDEMPTION,
        reference_item_id=None,
    )


def record_redemption_refund(db: Session, user_id: uuid.UUID, amount: int) -> None:
    _credit_ledger(
        db,
        user_id=user_id,
        delta=amount,
        reason=TokenLedgerReason.REDEMPTION_REFUND,
        reference_item_id=None,
    )


def _award_exists(db: Session, item_id: uuid.UUID, reason: TokenLedgerReason) -> bool:
    if (
        db.query(TokenLedger.id)
        .filter(
            TokenLedger.reference_item_id == item_id,
            TokenLedger.reason == reason,
        )
        .first()
    ):
        return True
    if (
        db.query(TokenEscrowEntry.id)
        .filter(
            TokenEscrowEntry.reference_item_id == item_id,
            TokenEscrowEntry.reason == reason,
        )
        .first()
    ):
        return True
    return False


def _credit_ledger(
    db: Session,
    *,
    user_id: uuid.UUID,
    delta: int,
    reason: TokenLedgerReason,
    reference_item_id: Optional[uuid.UUID],
) -> None:
    db.add(
        TokenLedger(
            user_id=user_id,
            delta=delta,
            reason=reason,
            reference_item_id=reference_item_id,
        )
    )
    logger.info(
        "token ledger credit user=%s delta=%s reason=%s item=%s",
        user_id,
        delta,
        reason.value,
        reference_item_id,
    )


def _get_escrow_by_plain_token(db: Session, plain_token: str) -> Optional[TokenEscrow]:
    token_hash = _hash_escrow_token(plain_token.strip())
    return (
        db.query(TokenEscrow)
        .options(joinedload(TokenEscrow.entries))
        .filter(TokenEscrow.escrow_token_hash == token_hash)
        .first()
    )


def _active_escrow(escrow: TokenEscrow) -> bool:
    now = _now()
    if escrow.claimed_at or escrow.discarded_at:
        return False
    return escrow.expires_at > now


def _escrow_expiring_soon(escrow: TokenEscrow) -> bool:
    """Section 14.1 — day 6 of 7; surfaced on tracking page (no push for anonymous)."""
    if not _active_escrow(escrow):
        return False
    return (escrow.expires_at - _now()) <= timedelta(days=1)


def _create_escrow(db: Session) -> tuple[TokenEscrow, str]:
    plain = secrets.token_urlsafe(32)
    escrow = TokenEscrow(
        escrow_token_hash=_hash_escrow_token(plain),
        expires_at=_now() + timedelta(days=ESCROW_EXPIRY_DAYS),
    )
    db.add(escrow)
    db.flush()
    return escrow, plain


def _resolve_escrow(
    db: Session,
    plain_token: Optional[str],
) -> tuple[TokenEscrow, str]:
    if plain_token:
        escrow = _get_escrow_by_plain_token(db, plain_token)
        if escrow and _active_escrow(escrow):
            return escrow, plain_token.strip()
    return _create_escrow(db)


def _find_escrow_for_item(db: Session, item_id: uuid.UUID) -> Optional[TokenEscrow]:
    entry = (
        db.query(TokenEscrowEntry)
        .options(joinedload(TokenEscrowEntry.escrow).joinedload(TokenEscrow.entries))
        .filter(TokenEscrowEntry.reference_item_id == item_id)
        .order_by(TokenEscrowEntry.created_at.asc())
        .first()
    )
    if not entry:
        return None
    return entry.escrow


def _add_escrow_entry(
    db: Session,
    escrow: TokenEscrow,
    *,
    delta: int,
    reason: TokenLedgerReason,
    reference_item_id: uuid.UUID,
) -> bool:
    if _award_exists(db, reference_item_id, reason):
        return False
    db.add(
        TokenEscrowEntry(
            escrow_id=escrow.id,
            delta=delta,
            reason=reason,
            reference_item_id=reference_item_id,
        )
    )
    db.flush()
    db.refresh(escrow)
    return True


def award_found_item_posted(
    db: Session,
    item: Item,
    *,
    user: Optional[User],
    escrow_token: Optional[str] = None,
) -> EscrowAwardResult:
    """Section 12.1 — 10 tokens for posting a found item."""
    reason = TokenLedgerReason.FOUND_ITEM_POSTED
    if _award_exists(db, item.id, reason):
        if user:
            return EscrowAwardResult(escrow_token=None, pending_total=0)
        escrow = _find_escrow_for_item(db, item.id)
        if escrow and _active_escrow(escrow):
            return EscrowAwardResult(
                escrow_token=escrow_token,
                pending_total=_escrow_total(escrow),
            )
        return EscrowAwardResult(escrow_token=None, pending_total=0)

    if user:
        amount = token_settings_service.amount_for_reason(db, reason)
        _credit_ledger(
            db,
            user_id=user.id,
            delta=amount,
            reason=reason,
            reference_item_id=item.id,
        )
        return EscrowAwardResult(escrow_token=None, pending_total=0)

    escrow, plain = _resolve_escrow(db, escrow_token)
    amount = token_settings_service.amount_for_reason(db, reason)
    _add_escrow_entry(
        db,
        escrow,
        delta=amount,
        reason=reason,
        reference_item_id=item.id,
    )
    return EscrowAwardResult(
        escrow_token=plain,
        pending_total=_escrow_total(escrow),
    )


def award_drop_off_confirmed(db: Session, item: Item) -> EscrowAwardResult:
    """Section 12.1 — drop-off tokens when AT_DROPPOINT is confirmed."""
    if item.status != ItemStatus.AT_DROPPOINT:
        return EscrowAwardResult(escrow_token=None, pending_total=0)

    if item.dropoff_late:
        reason = TokenLedgerReason.DROP_OFF_LATE
    else:
        reason = TokenLedgerReason.DROP_OFF_ON_TIME

    amount = token_settings_service.amount_for_reason(db, reason)

    if _award_exists(db, item.id, reason):
        if item.posted_by_id:
            return EscrowAwardResult(escrow_token=None, pending_total=0)
        escrow = _find_escrow_for_item(db, item.id)
        if escrow and _active_escrow(escrow):
            return EscrowAwardResult(
                escrow_token=None,
                pending_total=_escrow_total(escrow),
            )
        return EscrowAwardResult(escrow_token=None, pending_total=0)

    if item.posted_by_id:
        _credit_ledger(
            db,
            user_id=item.posted_by_id,
            delta=amount,
            reason=reason,
            reference_item_id=item.id,
        )
        return EscrowAwardResult(escrow_token=None, pending_total=0)

    escrow = _find_escrow_for_item(db, item.id)
    plain: Optional[str] = None
    if escrow and _active_escrow(escrow):
        added = _add_escrow_entry(
            db,
            escrow,
            delta=amount,
            reason=reason,
            reference_item_id=item.id,
        )
        if added:
            return EscrowAwardResult(
                escrow_token=None,
                pending_total=_escrow_total(escrow),
            )
        return EscrowAwardResult(
            escrow_token=None,
            pending_total=_escrow_total(escrow),
        )

    escrow, plain = _create_escrow(db)
    _add_escrow_entry(
        db,
        escrow,
        delta=amount,
        reason=reason,
        reference_item_id=item.id,
    )
    return EscrowAwardResult(
        escrow_token=plain,
        pending_total=_escrow_total(escrow),
    )


def award_item_claimed(db: Session, item: Item) -> None:
    """Section 11 / 12.1 — finder bonus when item is successfully claimed."""
    reason = TokenLedgerReason.ITEM_CLAIMED
    if _award_exists(db, item.id, reason):
        return

    if item.posted_by_id:
        amount = token_settings_service.amount_for_reason(db, reason)
        _credit_ledger(
            db,
            user_id=item.posted_by_id,
            delta=amount,
            reason=reason,
            reference_item_id=item.id,
        )
        return

    amount = token_settings_service.amount_for_reason(db, reason)
    escrow = _find_escrow_for_item(db, item.id)
    if escrow and _active_escrow(escrow):
        _add_escrow_entry(
            db,
            escrow,
            delta=amount,
            reason=reason,
            reference_item_id=item.id,
        )
        return

    escrow, _ = _create_escrow(db)
    _add_escrow_entry(
        db,
        escrow,
        delta=amount,
        reason=reason,
        reference_item_id=item.id,
    )


def build_token_escrow_info(
    db: Session,
    item: Item,
    *,
    escrow_token_plain: Optional[str] = None,
) -> TokenEscrowInfo:
    if item.posted_by_id:
        return TokenEscrowInfo(
            show_registration_prompt=False,
            pending_total=0,
            escrow_token=None,
        )

    escrow = _find_escrow_for_item(db, item.id)
    if not escrow or not _active_escrow(escrow):
        return TokenEscrowInfo(
            show_registration_prompt=False,
            pending_total=0,
            escrow_token=escrow_token_plain,
        )

    total = _escrow_total(escrow)
    show_prompt = item.status == ItemStatus.AT_DROPPOINT and total > 0
    expiring = _escrow_expiring_soon(escrow)
    return TokenEscrowInfo(
        show_registration_prompt=show_prompt,
        pending_total=total,
        escrow_token=escrow_token_plain,
        expiring_soon=expiring,
    )


def get_escrow_status(db: Session, plain_token: str) -> TokenEscrowInfo:
    escrow = _get_escrow_by_plain_token(db, plain_token)
    if not escrow or not _active_escrow(escrow):
        return TokenEscrowInfo(
            show_registration_prompt=False,
            pending_total=0,
            escrow_token=None,
        )
    total = _escrow_total(escrow)
    return TokenEscrowInfo(
        show_registration_prompt=total > 0,
        pending_total=total,
        escrow_token=plain_token,
        expiring_soon=_escrow_expiring_soon(escrow),
    )


def discard_escrow(db: Session, plain_token: str) -> None:
    escrow = _get_escrow_by_plain_token(db, plain_token)
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found.")
    if escrow.claimed_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="These tokens have already been claimed.",
        )
    now = _now()
    escrow.discarded_at = now
    for entry in list(escrow.entries):
        db.delete(entry)
    logger.info("token escrow discarded id=%s", escrow.id)


def _transfer_escrow_to_user(db: Session, escrow: TokenEscrow, user: User) -> int:
    if escrow.claimed_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="These tokens have already been claimed.",
        )
    if escrow.discarded_at:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="These tokens are no longer available.",
        )
    if escrow.expires_at <= _now():
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="These tokens have expired.",
        )

    total = 0
    for entry in escrow.entries:
        _credit_ledger(
            db,
            user_id=user.id,
            delta=entry.delta,
            reason=entry.reason,
            reference_item_id=entry.reference_item_id,
        )
        total += entry.delta
        db.delete(entry)

    escrow.claimed_at = _now()
    escrow.claimed_by_user_id = user.id
    logger.info("token escrow claimed id=%s user=%s total=%s", escrow.id, user.id, total)
    return total


def claim_escrow_for_user(
    db: Session,
    *,
    plain_token: str,
    user: User,
) -> int:
    escrow = _get_escrow_by_plain_token(db, plain_token)
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found.")
    return _transfer_escrow_to_user(db, escrow, user)


def claim_escrow_for_login(
    db: Session,
    *,
    plain_token: str,
    email: str,
    password: str,
) -> tuple[User, int]:
    escrow = _get_escrow_by_plain_token(db, plain_token)
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found.")
    user = auth_service.authenticate_user(db, email, password)
    total = _transfer_escrow_to_user(db, escrow, user)
    return user, total


async def claim_escrow_for_register(
    db: Session,
    *,
    plain_token: str,
    data: RegisterRequest,
) -> tuple[User, int]:
    escrow = _get_escrow_by_plain_token(db, plain_token)
    if not escrow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Escrow not found.")
    user = await auth_service.register_user(db, data)
    total = _transfer_escrow_to_user(db, escrow, user)
    return user, total


def expire_stale_escrows(db: Session) -> int:
    """Daily job — discard unclaimed escrow past the 7-day window (Section 9.3)."""
    now = _now()
    stale = (
        db.query(TokenEscrow)
        .options(joinedload(TokenEscrow.entries))
        .filter(
            TokenEscrow.claimed_at.is_(None),
            TokenEscrow.discarded_at.is_(None),
            TokenEscrow.expires_at < now,
        )
        .all()
    )
    count = 0
    for escrow in stale:
        escrow.discarded_at = now
        for entry in list(escrow.entries):
            db.delete(entry)
        count += 1
        logger.info("token escrow expired id=%s", escrow.id)
    return count


def warn_expiring_escrows(db: Session) -> int:
    """Daily job — flag escrows entering final 24h (Section 14.1 day 6 of 7)."""
    now = _now()
    threshold = now + timedelta(days=1)
    rows = (
        db.query(TokenEscrow)
        .filter(
            TokenEscrow.claimed_at.is_(None),
            TokenEscrow.discarded_at.is_(None),
            TokenEscrow.expiry_warning_sent_at.is_(None),
            TokenEscrow.expires_at <= threshold,
            TokenEscrow.expires_at > now,
        )
        .all()
    )
    for escrow in rows:
        escrow.expiry_warning_sent_at = now
        logger.info("token escrow expiring soon id=%s", escrow.id)
    return len(rows)

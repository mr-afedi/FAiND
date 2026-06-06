"""
Returned items lifecycle — tipping window, disputes, tip-freeze (Section 16, Feature N).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.item import Item, ItemStatus
from app.models.item_return import ItemReturn
from app.models.user import User, UserRole, AccountStatus
from app.models.notification import NotificationType
from app.services import notification_service

SKIP_APPRECIATION_HOURS = 24


def _days_left(ends_at: datetime | None, now: datetime) -> int:
    if not ends_at or ends_at <= now:
        return 0
    return max(0, (ends_at - now).days + (1 if (ends_at - now).seconds else 0))


def is_dispute_active(record: ItemReturn) -> bool:
    return record.dispute_filed_at is not None and record.dispute_resolved_at is None


def tipping_window_open(record: ItemReturn, now: datetime) -> bool:
    if not record.returned_at or is_dispute_active(record):
        return False
    if record.appreciation_sent_at:
        return False
    if record.tipping_window_ends_at and record.tipping_window_ends_at <= now:
        return False
    if record.appreciation_skipped_until and record.appreciation_skipped_until > now:
        return False
    return bool(record.tipping_window_ends_at and record.tipping_window_ends_at > now)


def dispute_window_open(record: ItemReturn, now: datetime) -> bool:
    if not record.returned_at or is_dispute_active(record):
        return False
    return bool(record.dispute_window_ends_at and record.dispute_window_ends_at > now)


def build_lifecycle_flags(
    record: ItemReturn,
    viewer: User,
    now: datetime | None = None,
) -> dict:
    """Computed Section 16.3–16.4 flags for detail/list responses."""
    now = now or datetime.now(timezone.utc)
    is_lost_owner = viewer.id == record.lost_owner_id
    dispute_active = is_dispute_active(record)
    tip_open = tipping_window_open(record, now)
    disp_open = dispute_window_open(record, now)

    return {
        "tipping_window_open": tip_open,
        "dispute_window_open": disp_open,
        "dispute_active": dispute_active,
        "appreciation_sent": record.appreciation_sent_at is not None,
        "appreciation_skipped_until": record.appreciation_skipped_until,
        "tip_frozen": record.tip_frozen,
        "tipping_days_left": _days_left(record.tipping_window_ends_at, now) if tip_open else 0,
        "dispute_days_left": _days_left(record.dispute_window_ends_at, now) if disp_open else 0,
        "can_send_appreciation": is_lost_owner and tip_open and not record.tip_frozen,
        "can_skip_appreciation": is_lost_owner and tip_open,
        "can_dispute": disp_open,
        "chat_read_only": record.returned_at is not None,
    }


def skip_appreciation(db: Session, return_id: uuid.UUID, user: User) -> ItemReturn:
    record = _get_return_for_user(db, return_id, user)
    if user.id != record.lost_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the lost item owner can skip appreciation.",
        )
    now = datetime.now(timezone.utc)
    if not tipping_window_open(record, now):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The appreciation window is not open.",
        )
    record.appreciation_skipped_until = now + timedelta(hours=SKIP_APPRECIATION_HOURS)
    db.commit()
    db.refresh(record)
    return record


def file_dispute(
    db: Session,
    return_id: uuid.UUID,
    user: User,
    reason: str,
) -> ItemReturn:
    record = _get_return_for_user(db, return_id, user)
    now = datetime.now(timezone.utc)
    if not dispute_window_open(record, now):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The dispute window is closed or a dispute is already open.",
        )

    reason = reason.strip()
    if len(reason) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least 10 characters explaining the dispute.",
        )

    record.dispute_filed_at = now
    record.dispute_filed_by_id = user.id
    record.dispute_reason = reason
    record.admin_review_flagged = True

    if record.appreciation_sent_at:
        record.tip_frozen = True

    lost = db.query(Item).filter(Item.id == record.lost_item_id).first()
    found = db.query(Item).filter(Item.id == record.found_item_id).first()
    if lost:
        lost.status = ItemStatus.UNDER_DISPUTE
        lost.updated_at = now
    if found:
        found.status = ItemStatus.UNDER_DISPUTE
        found.updated_at = now

    notification_service.notify_return_disputed(
        db,
        record=record,
        filed_by_id=user.id,
        tip_frozen=record.tip_frozen,
    )
    if record.tip_frozen:
        notify_admins_dispute_with_tip(db, record)
    db.commit()
    db.refresh(record)
    return record


def _get_return_for_user(db: Session, return_id: uuid.UUID, user: User) -> ItemReturn:
    record = db.query(ItemReturn).filter(ItemReturn.id == return_id).first()
    if not record or not record.returned_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found.")
    if user.id not in (record.lost_owner_id, record.found_owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return record


def is_return_chat_readonly(db: Session, potential_match_id: uuid.UUID) -> bool:
    record = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.potential_match_id == potential_match_id,
            ItemReturn.returned_at.isnot(None),
        )
        .first()
    )
    return record is not None


def mark_appreciation_sent(db: Session, return_id: uuid.UUID) -> ItemReturn:
    """Called by TippingService when Paystack payment succeeds."""
    record = db.query(ItemReturn).filter(ItemReturn.id == return_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found.")
    now = datetime.now(timezone.utc)
    record.appreciation_sent_at = now
    record.appreciation_skipped_until = None
    record.summary_note = "The owner expressed appreciation to the finder."
    db.commit()
    db.refresh(record)
    return record


def archive_completed_returns(db: Session) -> int:
    """
    Section 16.7 — RETURNED → ARCHIVED after 7-day windows close (no open dispute).
    """
    now = datetime.now(timezone.utc)
    rows = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.returned_at.isnot(None),
            ItemReturn.dispute_filed_at.is_(None),
            ItemReturn.tipping_window_ends_at.isnot(None),
            ItemReturn.tipping_window_ends_at < now,
        )
        .all()
    )
    count = 0
    for record in rows:
        for item_id in (record.lost_item_id, record.found_item_id):
            item = db.query(Item).filter(Item.id == item_id).first()
            if item and item.status == ItemStatus.RETURNED:
                item.status = ItemStatus.ARCHIVED
                item.updated_at = now
                count += 1
    if count:
        db.commit()
    return count


def notify_admins_dispute_with_tip(db: Session, record: ItemReturn) -> None:
    """Section 16.5 — flag admins when a tip exists on a disputed return."""
    admins = (
        db.query(User)
        .filter(
            User.university_id == record.university_id,
            User.role.in_((UserRole.ROOT_ADMIN, UserRole.ASSISTANT_ROOT_ADMIN, UserRole.UNIVERSITY_ADMIN)),
            User.status == AccountStatus.ACTIVE,
        )
        .all()
    )
    body = (
        "A return dispute was filed and an appreciation payment may need review. "
        f"Return ID: {record.id}"
    )
    link = f"/returns/{record.id}"
    for admin in admins:
        notification_service.create_notification(
            db,
            admin.id,
            NotificationType.GENERAL,
            title="Disputed return with tip",
            body=body,
            link=link,
            reference_id=record.id,
        )
    db.flush()

"""
Returned items lifecycle — dispute window and archiving (Section 16, Feature N).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.item import Item, ItemStatus
from app.models.item_return import ItemReturn
from app.models.user import User
from app.services import notification_service

RETURN_WINDOW_DAYS = 7


def _days_left(ends_at: datetime | None, now: datetime) -> int:
    if not ends_at or ends_at <= now:
        return 0
    return max(0, (ends_at - now).days + (1 if (ends_at - now).seconds else 0))


def _dispute_window_end(record: ItemReturn) -> datetime | None:
    if not record.returned_at:
        return None
    if record.dispute_window_ends_at:
        return record.dispute_window_ends_at
    return record.returned_at + timedelta(days=RETURN_WINDOW_DAYS)


def is_dispute_active(record: ItemReturn) -> bool:
    return record.dispute_filed_at is not None and record.dispute_resolved_at is None


def dispute_window_open(record: ItemReturn, now: datetime) -> bool:
    if not record.returned_at or is_dispute_active(record):
        return False
    window_end = _dispute_window_end(record)
    return bool(window_end and window_end > now)


def build_lifecycle_flags(
    record: ItemReturn,
    viewer: User,
    now: datetime | None = None,
) -> dict:
    """Computed dispute flags for detail responses."""
    now = now or datetime.now(timezone.utc)
    disp_open = dispute_window_open(record, now)
    return {
        "dispute_window_open": disp_open,
        "dispute_active": is_dispute_active(record),
        "dispute_days_left": _days_left(_dispute_window_end(record), now) if disp_open else 0,
        "can_dispute": disp_open,
    }


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
    )
    from app.services import admin_notification_service

    admin_notification_service.notify_admins_return_disputed(db, return_id=record.id)
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


def archive_completed_returns(db: Session) -> int:
    """
    Section 16.7 — RETURNED → ARCHIVED after dispute window closes (no open dispute).
    """
    now = datetime.now(timezone.utc)
    rows = (
        db.query(ItemReturn)
        .filter(ItemReturn.returned_at.isnot(None))
        .all()
    )
    count = 0
    for record in rows:
        if record.dispute_filed_at and not record.dispute_resolved_at:
            continue
        if record.admin_review_flagged and not record.dispute_resolved_at:
            continue
        window_end = _dispute_window_end(record)
        if not window_end or window_end >= now:
            continue
        for item_id in (record.lost_item_id, record.found_item_id):
            item = db.query(Item).filter(Item.id == item_id).first()
            if item and item.status == ItemStatus.RETURNED:
                item.status = ItemStatus.ARCHIVED
                item.updated_at = now
                count += 1
    if count:
        db.commit()
    return count

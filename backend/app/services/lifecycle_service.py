"""
Post lifecycle scheduled jobs — Section 21.7 (Feature S).

All business logic for APScheduler jobs lives here; scheduler.py only wires triggers.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemStatus
from app.models.item_return import ItemReturn
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.user import User
from app.services import matching_service, notification_service, returned_items_service
from app.services.fraud_service import HIGH_THRESHOLD

logger = logging.getLogger(__name__)

EXPIRY_REMINDER_DAYS = 3
DELETION_RETENTION_DAYS = 60

_EXPIRABLE_STATUSES = (
    ItemStatus.OPEN,
    ItemStatus.FOUND,
    ItemStatus.POTENTIAL_MATCH,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user_under_fraud_investigation(user: User | None) -> bool:
    """Section 21.6 — block deletion queue when owner is under fraud investigation."""
    return bool(user and user.fraud_risk_score >= HIGH_THRESHOLD)


def expire_items_past_deadline(db: Session) -> int:
    """
    Section 21.1 / 21.2 — hourly: items past expiry_date → EXPIRED, removed from pool.
    """
    now = _now()
    items = (
        db.query(Item)
        .filter(
            Item.expiry_date < now,
            Item.status.in_(_EXPIRABLE_STATUSES),
            Item.admin_locked.is_(False),
        )
        .all()
    )
    if not items:
        return 0

    count = 0
    for item in items:
        item.status = ItemStatus.EXPIRED
        item.updated_at = now
        matching_service.cleanup_on_item_archive(db, item.id)
        count += 1
        logger.info("expire_items_past_deadline: item=%s → EXPIRED", item.id)

    return count


def send_expiry_reminders(db: Session) -> int:
    """
    Section 21.1 / 21.2 — daily: notify owners 3 days before expiry_date.
    """
    now = _now()
    reminder_cutoff = now + timedelta(days=EXPIRY_REMINDER_DAYS)

    items = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(
            Item.expiry_reminder_sent_at.is_(None),
            Item.expiry_date > now,
            Item.expiry_date <= reminder_cutoff,
            Item.status.in_(_EXPIRABLE_STATUSES),
            Item.admin_locked.is_(False),
        )
        .all()
    )
    if not items:
        return 0

    count = 0
    for item in items:
        days_left = max(1, (item.expiry_date - now).days)
        notification_service.notify_post_expiring(
            db,
            owner_id=item.posted_by_id,
            item_id=item.id,
            days_left=days_left,
        )
        item.expiry_reminder_sent_at = now
        count += 1

    db.commit()
    logger.info("send_expiry_reminders: sent %d reminder(s)", count)
    return count


def close_expired_tipping_windows(db: Session) -> int:
    """
    Section 16.3 / 21.7 — daily: RETURNED → ARCHIVED after tipping window closes.
    """
    count = returned_items_service.archive_completed_returns(db)
    if count:
        logger.info("close_expired_tipping_windows: archived %d item(s)", count)
    return count


def close_expired_dispute_windows(db: Session) -> int:
    """
    Section 16.4 / 21.7 — daily: finalize returns whose dispute window has closed.

    Clears stale UNDER_DISPUTE on items when the related return dispute was already resolved.
    """
    now = _now()
    updated = 0

    resolved_returns = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.dispute_filed_at.isnot(None),
            ItemReturn.dispute_resolved_at.isnot(None),
        )
        .all()
    )
    for record in resolved_returns:
        for item_id in (record.lost_item_id, record.found_item_id):
            item = db.query(Item).filter(Item.id == item_id).first()
            if item and item.status == ItemStatus.UNDER_DISPUTE:
                item.status = (
                    ItemStatus.RETURNED if record.returned_at else ItemStatus.POTENTIAL_MATCH
                )
                item.updated_at = now
                updated += 1

    if updated:
        db.commit()
        logger.info("close_expired_dispute_windows: corrected %d item status(es)", updated)
    return updated


def queue_eligible_items_for_deletion(db: Session) -> int:
    """
    Section 21.6 / 21.7 — daily: move eligible ARCHIVED/EXPIRED items to deletion queue.
    """
    now = _now()
    cutoff = now - timedelta(days=DELETION_RETENTION_DAYS)

    items = (
        db.query(Item)
        .options(joinedload(Item.posted_by))
        .filter(
            Item.status.in_((ItemStatus.ARCHIVED, ItemStatus.EXPIRED)),
            Item.deletion_queued_at.is_(None),
            Item.admin_locked.is_(False),
            Item.updated_at <= cutoff,
        )
        .all()
    )
    if not items:
        return 0

    count = 0
    for item in items:
        if item.status == ItemStatus.UNDER_DISPUTE:
            continue
        if _user_under_fraud_investigation(item.posted_by):
            continue
        item.deletion_queued_at = now
        item.updated_at = now
        count += 1

    if count:
        db.commit()
        logger.info("queue_eligible_items_for_deletion: queued %d item(s)", count)
    return count


def resume_paused_matches_on_resolved_disputes(db: Session) -> int:
    """
    Section 21.7 — daily: resume PAUSED matches after disputes are resolved.
    """
    resolved_returns = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.dispute_filed_at.isnot(None),
            ItemReturn.dispute_resolved_at.isnot(None),
        )
        .all()
    )
    if not resolved_returns:
        return 0

    resumed_item_ids: set[uuid.UUID] = set()
    for record in resolved_returns:
        for item_id in (record.lost_item_id, record.found_item_id):
            if item_id in resumed_item_ids:
                continue
            item = db.query(Item).filter(Item.id == item_id).first()
            if item and item.status == ItemStatus.UNDER_DISPUTE:
                continue
            matching_service.resume_matches_for_item(db, item_id)
            resumed_item_ids.add(item_id)

    paused_orphans = (
        db.query(PotentialMatch)
        .filter(PotentialMatch.status == PotentialMatchStatus.PAUSED)
        .all()
    )
    extra = 0
    for match in paused_orphans:
        lost = db.query(Item).filter(Item.id == match.lost_item_id).first()
        found = db.query(Item).filter(Item.id == match.found_item_id).first()
        if lost and lost.status == ItemStatus.UNDER_DISPUTE:
            continue
        if found and found.status == ItemStatus.UNDER_DISPUTE:
            continue
        match.status = PotentialMatchStatus.ACTIVE
        extra += 1

    if extra:
        db.commit()
        logger.info(
            "resume_paused_matches_on_resolved_disputes: resumed %d orphan PAUSED match(es)",
            extra,
        )

    return len(resumed_item_ids) + extra

"""
Drop-off deadline jobs — Section 7.5 / 14.1 (24h / 48h / 72h).
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session, joinedload

from app.models.claim import Claim, ClaimStatus
from app.models.item import Item, ItemStatus, ItemType
from app.services import authority_notification_service, drop_off_service, notification_service
from app.services import admin_notification_service

logger = logging.getLogger(__name__)

_PENDING_DROP_OFF_STATUSES = (ItemStatus.FOUND, ItemStatus.OVERDUE)


def process_drop_off_lifecycle(db: Session) -> dict[str, int]:
    """Hourly: reminders, OVERDUE escalation, UNCONFIRMED hiding."""
    now = drop_off_service._now()
    counts = {"reminders": 0, "overdue": 0, "unconfirmed": 0}

    items = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.status.in_(_PENDING_DROP_OFF_STATUSES),
        )
        .all()
    )

    for item in items:
        if drop_off_service.is_dropoff_complete(item):
            continue

        age_hours = drop_off_service._item_age_hours(item, now)

        if age_hours >= drop_off_service.DROP_OFF_UNCONFIRMED_HOURS:
            item.status = ItemStatus.UNCONFIRMED
            item.updated_at = now
            counts["unconfirmed"] += 1
            if item.drop_point:
                authority_notification_service.notify_authority_item_unconfirmed(
                    db, item=item, drop_point=item.drop_point
                )
                admin_notification_service.notify_admins_item_unconfirmed(
                    db,
                    item_id=item.id,
                    drop_point_name=item.drop_point.name,
                )
                notification_service.notify_interested_parties_item_unconfirmed(
                    db, item=item
                )
            logger.info("drop_off lifecycle item=%s → UNCONFIRMED", item.id)
            continue

        if age_hours >= drop_off_service.DROP_OFF_DEADLINE_HOURS and item.status == ItemStatus.FOUND:
            item.status = ItemStatus.OVERDUE
            item.updated_at = now
            counts["overdue"] += 1
            if item.drop_point:
                authority_notification_service.notify_authority_item_overdue(
                    db, item=item, drop_point=item.drop_point
                )
                admin_notification_service.notify_admins_item_overdue(
                    db,
                    item_id=item.id,
                    drop_point_name=item.drop_point.name,
                )
            _notify_pending_claim_owners(db, item)
            logger.info("drop_off lifecycle item=%s → OVERDUE", item.id)
            continue

        if (
            age_hours >= drop_off_service.DROP_OFF_REMINDER_HOURS
            and not item.dropoff_reminder_sent_at
        ):
            item.dropoff_reminder_sent_at = now
            item.updated_at = now
            counts["reminders"] += 1
            authority_notification_service.notify_finder_dropoff_reminder(db, item=item)
            logger.info("drop_off lifecycle reminder sent item=%s", item.id)

    if counts["reminders"] or counts["overdue"] or counts["unconfirmed"]:
        logger.info(
            "process_drop_off_lifecycle reminders=%s overdue=%s unconfirmed=%s",
            counts["reminders"],
            counts["overdue"],
            counts["unconfirmed"],
        )

    return counts


def _notify_pending_claim_owners(db: Session, found_item: Item) -> None:
    """Section 14.1 — 48h OVERDUE: owners with pending claims on this item."""
    claims = (
        db.query(Claim)
        .filter(
            Claim.found_item_id == found_item.id,
            Claim.status == ClaimStatus.PENDING,
        )
        .all()
    )
    for claim in claims:
        notification_service.notify_owner_found_item_overdue(
            db,
            owner_id=claim.claimant_user_id,
            found_item_id=found_item.id,
        )

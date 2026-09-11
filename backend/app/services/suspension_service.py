"""
Suspension system — Section 4.7, Feature T.

Canonical entry point for admin suspend/unsuspend side effects:
item hiding, match pausing, push deactivation, notifications.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.admin_log import AdminActionType
from app.models.item import Item, ItemStatus
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.push_subscription import PushSubscription
from app.models.user import User, UserRole, AccountStatus
from app.services import matching_service, notification_service

logger = logging.getLogger(__name__)

_ITEM_HIDE_STATUSES = (
    ItemStatus.OPEN,
    ItemStatus.FOUND,
    ItemStatus.POTENTIAL_MATCH,
    ItemStatus.UNDER_VERIFICATION,
)

_PAUSEABLE_MATCH_STATUSES = (
    PotentialMatchStatus.ACTIVE,
    PotentialMatchStatus.PENDING_REVIEW,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hide_user_items(db: Session, user_id: uuid.UUID) -> int:
    """Section 4.7 — flag active posts hidden from feed and matching pool."""
    items = (
        db.query(Item)
        .filter(
            Item.posted_by_id == user_id,
            Item.status.in_(_ITEM_HIDE_STATUSES),
            Item.hidden_by_suspension.is_(False),
        )
        .all()
    )
    now = _now()
    for item in items:
        item.hidden_by_suspension = True
        item.updated_at = now
    return len(items)


def _restore_user_items(db: Session, user_id: uuid.UUID) -> int:
    """Section 4.7 — restore suspended posts to feed and matching pool."""
    items = (
        db.query(Item)
        .filter(
            Item.posted_by_id == user_id,
            Item.hidden_by_suspension.is_(True),
        )
        .all()
    )
    now = _now()
    for item in items:
        item.hidden_by_suspension = False
        item.updated_at = now
    return len(items)


def _pause_user_matches(db: Session, user_id: uuid.UUID) -> int:
    """Section 4.7 — pause pending verification / live matches for the user."""
    item_ids = [
        row[0]
        for row in db.query(Item.id).filter(Item.posted_by_id == user_id).all()
    ]
    if not item_ids:
        return 0

    matches = (
        db.query(PotentialMatch)
        .filter(
            PotentialMatch.status.in_(_PAUSEABLE_MATCH_STATUSES),
            or_(
                PotentialMatch.lost_item_id.in_(item_ids),
                PotentialMatch.found_item_id.in_(item_ids),
            ),
        )
        .all()
    )
    for match in matches:
        match.status = PotentialMatchStatus.PAUSED
    return len(matches)


def _set_push_subscriptions_active(db: Session, user_id: uuid.UUID, *, active: bool) -> int:
    """Section 4.7 — temporarily deactivate / reactivate Web Push subscriptions."""
    subs = (
        db.query(PushSubscription)
        .filter(PushSubscription.user_id == user_id)
        .all()
    )
    for sub in subs:
        sub.is_active = active
    return len(subs)


def _resume_user_matches(db: Session, user_id: uuid.UUID) -> int:
    """Section 4.7 — resume matches paused during suspension."""
    item_ids = [
        row[0]
        for row in db.query(Item.id).filter(Item.posted_by_id == user_id).all()
    ]
    total = 0
    for item_id in item_ids:
        item = db.query(Item).filter(Item.id == item_id).first()
        if item and item.status == ItemStatus.UNDER_DISPUTE:
            continue
        total += matching_service.resume_matches_for_item(db, item_id)
    return total


def _assert_can_suspend(target: User) -> None:
    if target.role == UserRole.ROOT_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot suspend an admin account.",
        )
    if target.status == AccountStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already suspended.",
        )


def suspend_user(
    db: Session,
    target: User,
    admin: User,
    *,
    reason: str | None = None,
    log_action=None,
) -> User:
    """
    Suspend a user and apply all Section 4.7 side effects.
    `log_action` is injected to avoid circular imports with admin_dashboard_service.
    """
    _assert_can_suspend(target)

    now = _now()
    target.status = AccountStatus.SUSPENDED
    target.suspended_at = now
    target.suspended_by_id = admin.id

    hidden = _hide_user_items(db, target.id)
    paused = _pause_user_matches(db, target.id)
    push_deactivated = _set_push_subscriptions_active(db, target.id, active=False)

    notification_service.notify_account_suspended(db, target.id)

    if log_action:
        log_action(
            db,
            admin=admin,
            action=AdminActionType.SUSPEND_USER,
            target_type="user",
            target_id=target.id,
            detail={
                "reason": reason or "",
                "status_before": "active",
                "status_after": "suspended",
                "items_hidden": hidden,
                "matches_paused": paused,
                "push_subscriptions_deactivated": push_deactivated,
            },
        )

    db.commit()
    db.refresh(target)
    logger.info(
        "suspend_user: user=%s hidden=%d paused=%d push=%d",
        target.id,
        hidden,
        paused,
        push_deactivated,
    )
    return target


def unsuspend_user(
    db: Session,
    target: User,
    admin: User,
    *,
    log_action=None,
) -> User:
    """Lift suspension and restore Section 4.7 resources."""
    if target.status != AccountStatus.SUSPENDED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is not suspended.",
        )

    target.status = AccountStatus.ACTIVE
    target.suspended_at = None
    target.suspended_by_id = None

    restored = _restore_user_items(db, target.id)
    push_reactivated = _set_push_subscriptions_active(db, target.id, active=True)
    resumed = _resume_user_matches(db, target.id)

    notification_service.notify_account_unsuspended(db, target.id)

    if log_action:
        log_action(
            db,
            admin=admin,
            action=AdminActionType.UNSUSPEND_USER,
            target_type="user",
            target_id=target.id,
            detail={
                "status_before": "suspended",
                "status_after": "active",
                "items_restored": restored,
                "push_subscriptions_reactivated": push_reactivated,
                "matches_resumed": resumed,
            },
        )

    db.commit()
    db.refresh(target)
    logger.info(
        "unsuspend_user: user=%s restored=%d push=%d matches=%d",
        target.id,
        restored,
        push_reactivated,
        resumed,
    )
    return target

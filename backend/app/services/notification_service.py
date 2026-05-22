"""
Notification service — in-app notification layer + Web Push (Section 11.4).

Delivery layers implemented here:
  1. In-app (notifications table)
  3. Web Push (via push_service)
"""
import uuid
import logging
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


def _fire_push(db: Session, user_id: uuid.UUID, title: str, body: str, url: str) -> None:
    """Best-effort Web Push — never raises so it cannot break the main flow."""
    try:
        from app.services.push_service import send_push_to_user
        send_push_to_user(db, user_id=user_id, title=title, body=body, url=url)
    except Exception as exc:
        logger.warning("Web Push delivery failed for user %s: %s", user_id, exc)


def create_notification(
    db: Session,
    user_id: uuid.UUID,
    notification_type: NotificationType,
    title: str,
    body: str,
    link: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        body=body,
        link=link,
        reference_id=reference_id,
    )
    db.add(notif)
    return notif


def notify_match_found(
    db: Session,
    lost_owner_id: uuid.UUID,
    found_owner_id: uuid.UUID,
    match_id: uuid.UUID,
    lost_item_id: uuid.UUID,
    found_item_id: uuid.UUID,
    score_pct: int,
) -> None:
    """Section 11.1 — AI match found: notify both parties in-app + push.

    Each user's notification deep-links to their own item detail page so
    they land directly on the matched item.
    """
    lost_title = "Potential match found!"
    lost_body = (
        f"Our AI found a {score_pct}% match for your lost item. "
        "Tap to review and verify ownership."
    )
    found_title = "Your found item may match a lost post"
    found_body = (
        f"Our AI matched your found item ({score_pct}% confidence) "
        "with a lost item report. The owner will be notified."
    )
    # Deep-link each user to their own item's detail page
    lost_link = f"/items/{lost_item_id}"
    found_link = f"/items/{found_item_id}"

    create_notification(
        db,
        user_id=lost_owner_id,
        notification_type=NotificationType.MATCH_FOUND,
        title=lost_title,
        body=lost_body,
        link=lost_link,
        reference_id=match_id,
    )
    create_notification(
        db,
        user_id=found_owner_id,
        notification_type=NotificationType.MATCH_FOUND,
        title=found_title,
        body=found_body,
        link=found_link,
        reference_id=match_id,
    )
    db.flush()

    # Web Push layer (Section 11.3) — title is always "FAiND", body is event-specific
    _fire_push(db, user_id=lost_owner_id, title="FAiND", body=lost_body, url=lost_link)
    _fire_push(db, user_id=found_owner_id, title="FAiND", body=found_body, url=found_link)


def get_unread_count(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id, Notification.read == False)
        .count()
    )


def list_notifications(
    db: Session,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

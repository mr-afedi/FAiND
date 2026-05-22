"""
Notification service — in-app notification layer (Section 11.4).

Feature H will add Web Push on top of these records.
"""
import uuid
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType


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
    score_pct: int,
) -> None:
    """Section 11.1 — AI match found: notify both parties."""
    create_notification(
        db,
        user_id=lost_owner_id,
        notification_type=NotificationType.MATCH_FOUND,
        title="Potential match found!",
        body=(
            f"Our AI found a {score_pct}% match for your lost item. "
            "Tap to review and verify ownership."
        ),
        link="/dashboard?tab=pending",
        reference_id=match_id,
    )
    create_notification(
        db,
        user_id=found_owner_id,
        notification_type=NotificationType.MATCH_FOUND,
        title="Your found item may match a lost post",
        body=(
            f"Our AI matched your found item ({score_pct}% confidence) "
            "with a lost item report. The owner will be notified."
        ),
        link="/dashboard?tab=pending",
        reference_id=match_id,
    )


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

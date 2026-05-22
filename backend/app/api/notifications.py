"""
In-app notifications API (Feature G — bell wiring in Feature H).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.services import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    id: uuid.UUID
    notification_type: str
    title: str
    body: str
    link: str | None
    reference_id: uuid.UUID | None
    read: bool
    created_at: str

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]
    unread_count: int


@router.get("/me", response_model=NotificationListResponse)
def get_my_notifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = notification_service.list_notifications(db, current_user.id, skip=skip, limit=limit)
    unread = notification_service.get_unread_count(db, current_user.id)
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=n.id,
                notification_type=n.notification_type.value,
                title=n.title,
                body=n.body,
                link=n.link,
                reference_id=n.reference_id,
                read=n.read,
                created_at=n.created_at.isoformat(),
            )
            for n in rows
        ],
        unread_count=unread,
    )


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == current_user.id)
        .first()
    )
    if notif:
        notif.read = True
        db.commit()
    return {"ok": True}


@router.post("/me/read-all")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications for the current user as read."""
    db.query(Notification).filter(
        Notification.user_id == current_user.id, Notification.read == False
    ).update({"read": True})
    db.commit()
    return {"ok": True}

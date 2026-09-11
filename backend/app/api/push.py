"""
/push — Web Push subscription management endpoints (Section 11.3).

POST  /push/subscribe          — register a push subscription
DELETE /push/subscribe         — remove a push subscription
GET   /push/vapid-public-key   — return VAPID public key (needed by frontend)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user, require_admin
from app.core.config import get_settings
from app.models.user import User
from app.services.push_service import save_subscription, delete_subscription, save_staff_subscription, delete_staff_subscription
from app.schemas.staff_push import (
    StaffPushSubscribeRequest,
    StaffPushUnsubscribeRequest,
    StaffPushSettingsResponse,
    StaffPushSettingsUpdate,
)
from app.models.staff_push_subscription import StaffPushType

router = APIRouter(prefix="/push", tags=["push"])
settings = get_settings()


class SubscribeRequest(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


class UnsubscribeRequest(BaseModel):
    endpoint: str


@router.get("/vapid-public-key")
def get_vapid_public_key():
    """Return the VAPID public key so the frontend can subscribe."""
    if not settings.VAPID_PUBLIC_KEY or settings.VAPID_PUBLIC_KEY == "your-vapid-public-key":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Web Push is not configured on this server.",
        )
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe", status_code=status.HTTP_201_CREATED)
def subscribe(
    payload: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Save (upsert) a browser push subscription for the current user."""
    save_subscription(
        db,
        user_id=current_user.id,
        endpoint=payload.endpoint,
        p256dh=payload.p256dh,
        auth=payload.auth,
    )
    return {"detail": "Subscribed to push notifications."}


@router.delete("/subscribe", status_code=status.HTTP_200_OK)
def unsubscribe(
    payload: UnsubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a browser push subscription."""
    deleted = delete_subscription(db, user_id=current_user.id, endpoint=payload.endpoint)
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    return {"detail": "Unsubscribed."}


@router.get("/admin/settings", response_model=StaffPushSettingsResponse)
def admin_get_push_settings(admin: User = Depends(require_admin)):
    return StaffPushSettingsResponse(push_notifications_enabled=admin.push_notifications_enabled)


@router.patch("/admin/settings", response_model=StaffPushSettingsResponse)
def admin_update_push_settings(
    payload: StaffPushSettingsUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    admin.push_notifications_enabled = payload.push_notifications_enabled
    db.commit()
    return StaffPushSettingsResponse(push_notifications_enabled=admin.push_notifications_enabled)


@router.post("/admin/subscribe", status_code=status.HTTP_201_CREATED)
def admin_push_subscribe(
    payload: StaffPushSubscribeRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    save_staff_subscription(
        db,
        staff_type=StaffPushType.ADMIN,
        staff_id=admin.id,
        endpoint=payload.endpoint,
        p256dh=payload.p256dh,
        auth=payload.auth,
    )
    return {"detail": "Subscribed to push notifications."}


@router.delete("/admin/subscribe", status_code=status.HTTP_200_OK)
def admin_push_unsubscribe(
    payload: StaffPushUnsubscribeRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    deleted = delete_staff_subscription(
        db,
        staff_type=StaffPushType.ADMIN,
        staff_id=admin.id,
        endpoint=payload.endpoint,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    return {"detail": "Unsubscribed."}

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
from app.core.deps import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.services.push_service import save_subscription, delete_subscription

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

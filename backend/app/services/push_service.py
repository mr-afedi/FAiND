"""
push_service.py — Web Push notification delivery via pywebpush (Section 11.3).

Responsibilities:
 - Store/remove PushSubscription records
 - Send push payloads to all active subscriptions for a user
 - Gracefully handle expired/invalid subscriptions (delete them)
"""
import json
import logging
from functools import lru_cache
from uuid import UUID

from py_vapid import Vapid
from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.core.config import get_settings
from app.models.push_subscription import PushSubscription
from app.models.staff_push_subscription import StaffPushSubscription, StaffPushType
from app.models.user import User
from app.models.authority import Authority
from app.models.supervisor import Supervisor

logger = logging.getLogger(__name__)
settings = get_settings()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _vapid_configured() -> bool:
    return bool(settings.VAPID_PRIVATE_KEY and settings.VAPID_PUBLIC_KEY
                and settings.VAPID_PRIVATE_KEY != "your-vapid-private-key")


@lru_cache(maxsize=1)
def _get_vapid() -> Vapid:
    """Load VAPID signing key — PEM string in .env (\\n escaped) → Vapid object."""
    pem = settings.VAPID_PRIVATE_KEY.replace("\\n", "\n").encode()
    return Vapid.from_pem(pem)


def save_subscription(db: Session, user_id: UUID, endpoint: str, p256dh: str, auth: str) -> PushSubscription:
    """Upsert a push subscription (same endpoint updates keys)."""
    stmt = (
        pg_insert(PushSubscription)
        .values(user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth)
        .on_conflict_do_update(
            constraint="uq_push_user_endpoint",
            set_={"p256dh": p256dh, "auth": auth, "is_active": True},
        )
        .returning(PushSubscription)
    )
    result = db.execute(stmt)
    db.commit()
    return result.scalars().first()


def delete_subscription(db: Session, user_id: UUID, endpoint: str) -> bool:
    """Remove a specific push subscription. Returns True if deleted."""
    sub = (
        db.query(PushSubscription)
        .filter(PushSubscription.user_id == user_id, PushSubscription.endpoint == endpoint)
        .first()
    )
    if sub:
        db.delete(sub)
        db.commit()
        return True
    return False


def send_push_to_user(db: Session, user_id: UUID, title: str, body: str, url: str = "/") -> None:
    """
    Send a Web Push notification to all subscriptions for a user.
    Invalid/expired subscriptions are silently removed.
    """
    if not _vapid_configured():
        print(f"[Push] SKIP user {user_id} — VAPID keys not configured", flush=True)
        return

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.push_notifications_enabled:
        print(
            f"[Push] SKIP user {user_id} — push_notifications_enabled is off or user missing",
            flush=True,
        )
        return

    subscriptions = (
        db.query(PushSubscription)
        .filter(
            PushSubscription.user_id == user_id,
            PushSubscription.is_active.is_(True),
        )
        .all()
    )
    if not subscriptions:
        print(f"[Push] SKIP user {user_id} — no browser subscriptions saved", flush=True)
        return

    payload = json.dumps({
        "title": title,
        "body": body,
        "icon": "/pwa-192x192.png",
        "url": url,
    })

    vapid_claims = {"sub": settings.VAPID_CLAIMS_EMAIL or "mailto:admin@faind.app"}

    try:
        vapid = _get_vapid()
    except Exception as exc:
        print(f"[Push] ERROR — invalid VAPID private key: {exc}", flush=True)
        return

    stale_ids = []
    sent = 0
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=vapid,
                vapid_claims=vapid_claims,
            )
            sent += 1
            print(
                f"[Push] ✅ Sent to user {user_id} — \"{title}\" → {sub.endpoint[:50]}...",
                flush=True,
            )
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None) if exc.response else None
            err_text = str(exc).lower()
            is_stale = status in (404, 410) or "410" in err_text or "404" in err_text or "expired" in err_text or "unsubscribed" in err_text
            if is_stale:
                stale_ids.append(sub.id)
                print(
                    f"[Push] Removed stale subscription {sub.id} (HTTP {status or 'gone'})",
                    flush=True,
                )
            else:
                detail = exc.response.text[:200] if exc.response else str(exc)
                print(
                    f"[Push] ❌ WebPush failed for subscription {sub.id} (HTTP {status}): {detail}",
                    flush=True,
                )
        except Exception as exc:
            print(f"[Push] ❌ Unexpected error for subscription {sub.id}: {exc}", flush=True)

    if stale_ids:
        db.query(PushSubscription).filter(PushSubscription.id.in_(stale_ids)).delete(
            synchronize_session=False
        )
        db.commit()

    if sent == 0 and not stale_ids:
        print(f"[Push] No deliveries succeeded for user {user_id}", flush=True)


def save_staff_subscription(
    db: Session,
    *,
    staff_type: StaffPushType,
    staff_id: UUID,
    endpoint: str,
    p256dh: str,
    auth: str,
) -> StaffPushSubscription:
    stmt = (
        pg_insert(StaffPushSubscription)
        .values(
            staff_type=staff_type,
            staff_id=staff_id,
            endpoint=endpoint,
            p256dh=p256dh,
            auth=auth,
        )
        .on_conflict_do_update(
            constraint="uq_staff_push_endpoint",
            set_={"p256dh": p256dh, "auth": auth, "is_active": True},
        )
        .returning(StaffPushSubscription)
    )
    result = db.execute(stmt)
    db.commit()
    return result.scalars().first()


def delete_staff_subscription(
    db: Session,
    *,
    staff_type: StaffPushType,
    staff_id: UUID,
    endpoint: str,
) -> bool:
    sub = (
        db.query(StaffPushSubscription)
        .filter(
            StaffPushSubscription.staff_type == staff_type,
            StaffPushSubscription.staff_id == staff_id,
            StaffPushSubscription.endpoint == endpoint,
        )
        .first()
    )
    if sub:
        db.delete(sub)
        db.commit()
        return True
    return False


def _send_push_to_subscriptions(
    db: Session,
    subscriptions: list[StaffPushSubscription],
    *,
    title: str,
    body: str,
    url: str,
    label: str,
) -> None:
    if not _vapid_configured() or not subscriptions:
        return

    payload = json.dumps({
        "title": title,
        "body": body,
        "icon": "/pwa-192x192.png",
        "url": url,
    })
    vapid_claims = {"sub": settings.VAPID_CLAIMS_EMAIL or "mailto:admin@faind.app"}

    try:
        vapid = _get_vapid()
    except Exception as exc:
        print(f"[Push] ERROR — invalid VAPID private key: {exc}", flush=True)
        return

    stale_ids = []
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=vapid,
                vapid_claims=vapid_claims,
            )
            print(f"[Push] ✅ Sent to {label} → {sub.endpoint[:50]}...", flush=True)
        except WebPushException as exc:
            status = getattr(exc.response, "status_code", None) if exc.response else None
            err_text = str(exc).lower()
            is_stale = status in (404, 410) or "410" in err_text or "404" in err_text
            if is_stale:
                stale_ids.append(sub.id)
        except Exception as exc:
            print(f"[Push] ❌ Unexpected staff push error: {exc}", flush=True)

    if stale_ids:
        db.query(StaffPushSubscription).filter(StaffPushSubscription.id.in_(stale_ids)).delete(
            synchronize_session=False
        )
        db.commit()


def _staff_subscriptions(
    db: Session, staff_type: StaffPushType, staff_id: UUID
) -> list[StaffPushSubscription]:
    return (
        db.query(StaffPushSubscription)
        .filter(
            StaffPushSubscription.staff_type == staff_type,
            StaffPushSubscription.staff_id == staff_id,
            StaffPushSubscription.is_active.is_(True),
        )
        .all()
    )


def send_push_to_authority(
    db: Session,
    *,
    authority_id: UUID,
    title: str,
    body: str,
    url: str = "/authority",
) -> None:
    authority = db.query(Authority).filter(Authority.id == authority_id).first()
    if not authority or not authority.push_notifications_enabled:
        return
    subs = _staff_subscriptions(db, StaffPushType.AUTHORITY, authority_id)
    _send_push_to_subscriptions(
        db, subs, title=title, body=body, url=url, label=f"authority {authority_id}"
    )


def send_push_to_supervisor(
    db: Session,
    *,
    supervisor_id: UUID,
    title: str,
    body: str,
    url: str = "/supervisor",
) -> None:
    supervisor = db.query(Supervisor).filter(Supervisor.id == supervisor_id).first()
    if not supervisor or not supervisor.push_notifications_enabled:
        return
    subs = _staff_subscriptions(db, StaffPushType.SUPERVISOR, supervisor_id)
    _send_push_to_subscriptions(
        db, subs, title=title, body=body, url=url, label=f"supervisor {supervisor_id}"
    )


def send_push_to_admin(
    db: Session,
    *,
    admin_user_id: UUID,
    title: str,
    body: str,
    url: str = "/admin",
) -> None:
    admin = db.query(User).filter(User.id == admin_user_id).first()
    if not admin or not admin.push_notifications_enabled:
        return
    subs = _staff_subscriptions(db, StaffPushType.ADMIN, admin_user_id)
    _send_push_to_subscriptions(
        db, subs, title=title, body=body, url=url, label=f"admin {admin_user_id}"
    )

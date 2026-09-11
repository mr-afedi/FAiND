"""
Authority notifications — Section 14.1 (W16).

Email + in-app dashboard alerts for the drop point authority.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.authority import Authority
from app.models.authority_alert import AuthorityAlertType
from app.models.item import Item
from app.services import authority_alert_service
from app.services import push_service
from app.utils.email import send_authority_alert_email

if TYPE_CHECKING:
    from app.models.claim import Claim
    from app.models.claim_inquiry import ClaimInquiry
    from app.models.user import User

logger = logging.getLogger(__name__)


def _fire_authority_email(email: str, subject: str, body: str) -> None:
    def _run() -> None:
        try:
            asyncio.run(send_authority_alert_email(email, subject, body))
        except Exception as exc:
            logger.warning("Authority email failed for %s: %s", email, exc)

    threading.Thread(target=_run, daemon=True).start()


def _get_active_authority(db: Session, drop_point_id: uuid.UUID) -> Authority | None:
    return (
        db.query(Authority)
        .filter(Authority.drop_point_id == drop_point_id, Authority.is_active.is_(True))
        .first()
    )


def _push_url_from_authority_link(link: str | None) -> str:
    if not link:
        return "/authority"
    if link.startswith("authority:claims:"):
        return "/authority?tab=claims"
    if link.startswith("authority:incoming") or link == "authority:incoming":
        return "/authority?tab=incoming"
    if link.startswith("authority:handover"):
        return "/authority?tab=handover"
    if link == "authority:settings":
        return "/authority?tab=settings"
    return "/authority"


def _notify_authority(
    db: Session,
    *,
    drop_point: DropPoint,
    subject: str,
    body: str,
    alert_type: AuthorityAlertType,
    link: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> None:
    authority = _get_active_authority(db, drop_point.id)
    if authority:
        authority_alert_service.create_alert(
            db,
            authority_id=authority.id,
            alert_type=alert_type,
            title=subject,
            body=body,
            link=link,
            reference_id=reference_id,
        )
        _fire_authority_email(authority.email, subject, body)
        push_service.send_push_to_authority(
            db,
            authority_id=authority.id,
            title=subject,
            body=body,
            url=_push_url_from_authority_link(link),
        )
        logger.info(
            "AUTHORITY_NOTIFY email=%s drop_point=%s subject=%s",
            authority.email,
            drop_point.name,
            subject,
        )
    else:
        logger.info(
            "AUTHORITY_NOTIFY skip — no active authority for drop_point=%s (%s)",
            drop_point.id,
            drop_point.name,
        )

    from app.services import supervisor_notification_service

    supervisor_notification_service.mirror_authority_notification(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=alert_type,
        link=link,
        reference_id=reference_id,
    )


def notify_authority_found_item_reported(
    db: Session,
    *,
    item: Item,
    drop_point: DropPoint,
) -> None:
    """New found item assigned to this drop point (Section 7.3)."""
    subject = "New found item reported"
    body = (
        f"A new found item was reported for {drop_point.name}: "
        f"\"{item.public_description[:120]}\". "
        f"Tracking ref: {item.tracking_reference or 'n/a'}."
    )
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=AuthorityAlertType.NEW_ITEM_INCOMING,
        link="authority:incoming",
        reference_id=item.id,
    )


def notify_authority_finder_marked_dropoff(
    db: Session,
    *,
    item: Item,
    drop_point: DropPoint,
) -> None:
    """Finder confirmed drop-off — awaiting authority receipt (Section 14.1)."""
    subject = "Finder marked drop-off"
    body = (
        f"A finder marked an item as dropped off at {drop_point.name}. "
        f"Ref: {item.tracking_reference or item.id}. "
        "Please confirm receipt in your dashboard."
    )
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=AuthorityAlertType.FINDER_MARKED_DROPOFF,
        link="authority:incoming",
        reference_id=item.id,
    )


def notify_finder_dropoff_reminder(db: Session, *, item: Item) -> None:
    """24h reminder — registered finders only; anonymous finders use tracking page."""
    from app.services import notification_service

    notification_service.notify_finder_dropoff_reminder(db, item=item)


def notify_authority_item_overdue(
    db: Session,
    *,
    item: Item,
    drop_point: DropPoint,
) -> None:
    """48h — item overdue for drop-off (Section 14.1)."""
    subject = "Item overdue for drop-off"
    body = (
        f"Found item at {drop_point.name} is overdue for drop-off "
        f"(ref {item.tracking_reference or item.id}). Review in your dashboard."
    )
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=AuthorityAlertType.ITEM_OVERDUE,
        link="authority:incoming",
        reference_id=item.id,
    )


def notify_authority_item_unconfirmed(
    db: Session,
    *,
    item: Item,
    drop_point: DropPoint,
) -> None:
    """72h — item unconfirmed / hidden (Section 14.1)."""
    subject = "Item unconfirmed after 72 hours"
    body = (
        f"Found item at {drop_point.name} moved to UNCONFIRMED after 72 hours "
        f"(ref {item.tracking_reference or item.id})."
    )
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=AuthorityAlertType.ADMIN_ACTION,
        link="authority:incoming",
        reference_id=item.id,
    )


def notify_authority_received_stub(
    db: Session,
    *,
    item: Item,
    drop_point: DropPoint,
) -> None:
    """Authority recorded receipt — logged only; finder is notified on finalize."""
    _ = db, item, drop_point


def notify_authority_dropoff_confirmed(
    db: Session,
    *,
    item: Item,
    drop_point: DropPoint,
) -> None:
    """Drop-off fully confirmed — finder/claimants notified elsewhere."""
    _ = db, item, drop_point


def notify_authority_new_claim(
    db: Session,
    *,
    claim: Claim,
    item: Item,
    claimant: User,
) -> None:
    """Claim submitted — notify drop point authority (Section 14.1)."""
    drop_point = item.drop_point
    if not drop_point:
        logger.info("AUTHORITY_CLAIM_NOTIFY — no drop point on item=%s", item.id)
        return
    subject = "New claim submitted"
    body = (
        f"New claim (Path {claim.claim_path.value}) on item "
        f"\"{item.public_description[:100]}\" from {claimant.email}. "
        "Review claims in your dashboard."
    )
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=AuthorityAlertType.NEW_CLAIM,
        link=f"authority:claims:{item.id}",
        reference_id=claim.id,
    )


def notify_authority_claim_inquiry(
    db: Session,
    *,
    claim: Claim,
    item: Item,
    inquiry: ClaimInquiry,
    drop_point: DropPoint | None,
) -> None:
    """Predefined inquiry from owner — authority dashboard + email (Section 14.1)."""
    from app.models.claim_inquiry import INQUIRY_LABELS

    if not drop_point:
        return
    label = INQUIRY_LABELS.get(inquiry.message_type, inquiry.message_type.value)
    subject = "Claimant inquiry received"
    body = (
        f"A claimant sent an inquiry on item \"{item.public_description[:100]}\": "
        f"\"{label}\". Reply from your claims dashboard."
    )
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=AuthorityAlertType.OWNER_INQUIRY,
        link=f"authority:claims:{item.id}",
        reference_id=inquiry.id,
    )


def notify_authority_handover_complete(
    db: Session,
    *,
    item: Item,
    drop_point: DropPoint,
    handover_id: uuid.UUID,
) -> None:
    """Item successfully handed over — deletable informational alert."""
    subject = "Handover complete"
    body = (
        f"Item \"{item.public_description[:100]}\" was successfully handed over "
        f"at {drop_point.name}."
    )
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=AuthorityAlertType.HANDOVER_COMPLETE,
        link="authority:handover",
        reference_id=handover_id,
    )


def notify_authority_item_removed(
    db: Session,
    *,
    item: Item,
    drop_point: DropPoint,
) -> None:
    """Admin removed an item at this drop point — deletable informational."""
    subject = "Item removed by admin"
    body = (
        f"An item at {drop_point.name} was removed by an administrator: "
        f"\"{item.public_description[:100]}\"."
    )
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=AuthorityAlertType.ITEM_REMOVED,
        link="authority:at-droppoint",
        reference_id=item.id,
    )


def notify_authority_drop_point_closed(
    db: Session,
    *,
    drop_point: DropPoint,
) -> None:
    """Authority toggled temporary closure — deletable after seen."""
    subject = "Drop point temporarily closed"
    body = (
        f"{drop_point.name} is now marked temporarily closed"
        f"{f': {drop_point.closed_reason}' if drop_point.closed_reason else ''}. "
        "Owners with pending claims have been notified."
    )
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=AuthorityAlertType.DROP_POINT_CLOSED,
        link="authority:settings",
        reference_id=drop_point.id,
    )


def notify_authority_admin_action(
    db: Session,
    *,
    drop_point: DropPoint,
    title: str,
    body: str,
    reference_id: uuid.UUID | None = None,
) -> None:
    """Admin action affecting this drop point — non-deletable."""
    _notify_authority(
        db,
        drop_point=drop_point,
        subject=title,
        body=body,
        alert_type=AuthorityAlertType.ADMIN_ACTION,
        link="authority:incoming",
        reference_id=reference_id,
    )

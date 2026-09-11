"""
Supervisor notifications — same triggers as authority across assigned drop points (V5).
"""
from __future__ import annotations

import logging
import uuid

from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.authority_alert import AuthorityAlertType
from app.models.drop_point import DropPoint
from app.models.item import Item
from app.models.supervisor_alert import SupervisorAlertType
from app.services import supervisor_alert_service, push_service

if TYPE_CHECKING:
    from app.models.claim import Claim
    from app.models.claim_inquiry import ClaimInquiry
    from app.models.user import User

logger = logging.getLogger(__name__)

_AUTHORITY_TO_SUPERVISOR = {
    AuthorityAlertType.NEW_ITEM_INCOMING: SupervisorAlertType.NEW_ITEM_INCOMING,
    AuthorityAlertType.FINDER_MARKED_DROPOFF: SupervisorAlertType.FINDER_MARKED_DROPOFF,
    AuthorityAlertType.NEW_CLAIM: SupervisorAlertType.NEW_CLAIM,
    AuthorityAlertType.OWNER_INQUIRY: SupervisorAlertType.OWNER_INQUIRY,
    AuthorityAlertType.ITEM_OVERDUE: SupervisorAlertType.ITEM_OVERDUE,
    AuthorityAlertType.ADMIN_ACTION: SupervisorAlertType.ADMIN_ACTION,
    AuthorityAlertType.HANDOVER_COMPLETE: SupervisorAlertType.HANDOVER_COMPLETE,
    AuthorityAlertType.ITEM_REMOVED: SupervisorAlertType.ITEM_REMOVED,
    AuthorityAlertType.DROP_POINT_CLOSED: SupervisorAlertType.DROP_POINT_CLOSED,
}


def mirror_authority_notification(
    db: Session,
    *,
    drop_point: DropPoint,
    subject: str,
    body: str,
    alert_type: AuthorityAlertType,
    link: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> None:
    sup_type = _AUTHORITY_TO_SUPERVISOR.get(alert_type)
    if not sup_type:
        return
    _notify_supervisors(
        db,
        drop_point=drop_point,
        subject=subject,
        body=body,
        alert_type=sup_type,
        link=link,
        reference_id=reference_id,
    )


def _authority_link_to_supervisor(link: str | None) -> str | None:
    if not link:
        return None
    if link.startswith("authority:"):
        return link.replace("authority:", "supervisor:", 1)
    return link


def _notify_supervisors(
    db: Session,
    *,
    drop_point: DropPoint,
    subject: str,
    body: str,
    alert_type: SupervisorAlertType,
    link: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> None:
    supervisor_link = _authority_link_to_supervisor(link)
    rows = supervisor_alert_service.create_alerts_for_drop_point(
        db,
        drop_point_id=drop_point.id,
        alert_type=alert_type,
        title=subject,
        body=body,
        link=supervisor_link,
        reference_id=reference_id,
    )
    for row in rows:
        push_service.send_push_to_supervisor(
            db,
            supervisor_id=row.supervisor_id,
            title=subject,
            body=body,
            url=_push_url_from_link(supervisor_link),
        )
    if rows:
        logger.info(
            "SUPERVISOR_NOTIFY drop_point=%s subject=%s count=%s",
            drop_point.name,
            subject,
            len(rows),
        )


def _push_url_from_link(link: str | None) -> str:
    if not link:
        return "/supervisor"
    if link.startswith("supervisor:claims:"):
        return "/supervisor?tab=claims"
    if link.startswith("supervisor:incoming") or link == "supervisor:incoming":
        return "/supervisor?tab=items"
    if link.startswith("supervisor:handover"):
        return "/supervisor?tab=items"
    return "/supervisor"


def notify_supervisor_found_item_reported(db: Session, *, item: Item, drop_point: DropPoint) -> None:
    _notify_supervisors(
        db,
        drop_point=drop_point,
        subject="New found item reported",
        body=(
            f"A new found item was reported for {drop_point.name}: "
            f"\"{item.public_description[:120]}\"."
        ),
        alert_type=SupervisorAlertType.NEW_ITEM_INCOMING,
        link="supervisor:incoming",
        reference_id=item.id,
    )


def notify_supervisor_finder_marked_dropoff(db: Session, *, item: Item, drop_point: DropPoint) -> None:
    _notify_supervisors(
        db,
        drop_point=drop_point,
        subject="Finder marked drop-off",
        body=(
            f"A finder marked an item as dropped off at {drop_point.name}. "
            "Please ensure the authority confirms receipt."
        ),
        alert_type=SupervisorAlertType.FINDER_MARKED_DROPOFF,
        link="supervisor:incoming",
        reference_id=item.id,
    )


def notify_supervisor_item_overdue(db: Session, *, item: Item, drop_point: DropPoint) -> None:
    _notify_supervisors(
        db,
        drop_point=drop_point,
        subject="Item overdue for drop-off",
        body=(
            f"Found item at {drop_point.name} is overdue for drop-off "
            f"(ref {item.tracking_reference or item.id})."
        ),
        alert_type=SupervisorAlertType.ITEM_OVERDUE,
        link="supervisor:incoming",
        reference_id=item.id,
    )


def notify_supervisor_new_claim(
    db: Session,
    *,
    claim: "Claim",
    item: Item,
    claimant: "User",
) -> None:
    drop_point = item.drop_point
    if not drop_point:
        return
    _notify_supervisors(
        db,
        drop_point=drop_point,
        subject="New claim submitted",
        body=(
            f"New claim (Path {claim.claim_path.value}) on item "
            f"\"{item.public_description[:100]}\" from {claimant.email}."
        ),
        alert_type=SupervisorAlertType.NEW_CLAIM,
        link=f"supervisor:claims:{item.id}",
        reference_id=claim.id,
    )


def notify_supervisor_claim_inquiry(
    db: Session,
    *,
    claim: "Claim",
    item: Item,
    inquiry: "ClaimInquiry",
    drop_point: DropPoint | None,
) -> None:
    from app.models.claim_inquiry import INQUIRY_LABELS

    if not drop_point:
        return
    label = INQUIRY_LABELS.get(inquiry.message_type, inquiry.message_type.value)
    _notify_supervisors(
        db,
        drop_point=drop_point,
        subject="Claimant inquiry received",
        body=(
            f"A claimant sent an inquiry on item \"{item.public_description[:100]}\": "
            f"\"{label}\"."
        ),
        alert_type=SupervisorAlertType.OWNER_INQUIRY,
        link=f"supervisor:claims:{item.id}",
        reference_id=inquiry.id,
    )

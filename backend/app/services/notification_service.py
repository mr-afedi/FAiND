"""
Notification service — in-app notification layer + Web Push (Section 11.4).

Delivery layers implemented here:
  1. In-app (notifications table)
  3. Web Push (via push_service)
"""
import logging
import threading
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)


def _fire_push(db: Session, user_id: uuid.UUID, title: str, body: str, url: str) -> None:
    """Best-effort Web Push — deferred so slow network I/O cannot block API responses."""
    try:
        from app.services.push_service import send_push_to_user

        uid = user_id

        def _deliver() -> None:
            from app.core.database import SessionLocal

            session = SessionLocal()
            try:
                send_push_to_user(session, user_id=uid, title=title, body=body, url=url)
            except Exception as exc:
                logger.warning("Web Push delivery failed for user %s: %s", uid, exc)
            finally:
                session.close()

        threading.Thread(target=_deliver, daemon=True).start()
    except Exception as exc:
        logger.warning("Web Push dispatch failed for user %s: %s", user_id, exc)


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
    found_owner_id: uuid.UUID | None,
    match_id: uuid.UUID,
    lost_item_id: uuid.UUID,
    found_item_id: uuid.UUID,
    score_pct: int,
) -> None:
    """Section 14.1 — AI match found: lost item owner only (Path A)."""
    lost_body = (
        f"Our AI found a {score_pct}% match for your lost item. "
        "Tap to view the matched item and submit a claim."
    )
    lost_link = f"/items/{found_item_id}"

    create_notification(
        db,
        user_id=lost_owner_id,
        notification_type=NotificationType.MATCH_FOUND,
        title="Potential match found!",
        body=lost_body,
        link=lost_link,
        reference_id=match_id,
    )
    db.flush()
    _fire_push(db, user_id=lost_owner_id, title="FAiND", body=lost_body, url=lost_link)


def notify_interested_parties_item_at_droppoint(db: Session, *, item, drop_point) -> None:
    """V5 — notify users who registered interest before drop-off."""
    from app.services import item_interest_service

    dp_name = drop_point.name if drop_point else "the drop point"
    body = (
        f"The item you were interested in has arrived at {dp_name}. "
        "You can now submit your claim."
    )
    link = f"/claims/found/{item.id}?path=c"
    for user_id in item_interest_service.list_interested_user_ids(db, item.id):
        create_notification(
            db,
            user_id,
            NotificationType.GENERAL,
            title="Item ready to claim",
            body=body,
            link=link,
            reference_id=item.id,
        )
        db.flush()
        _fire_push(db, user_id, "FAiND", body, link)


def notify_interested_parties_item_unconfirmed(db: Session, *, item) -> None:
    """V5 — item never dropped off after 72h."""
    from app.services import item_interest_service

    body = (
        "Unfortunately the item you were interested in was not dropped off. "
        "Keep an eye out for new found items."
    )
    link = "/found"
    for user_id in item_interest_service.list_interested_user_ids(db, item.id):
        create_notification(
            db,
            user_id,
            NotificationType.GENERAL,
            title="Item not dropped off",
            body=body,
            link=link,
            reference_id=item.id,
        )
        db.flush()
        _fire_push(db, user_id, "FAiND", body, link)


def notify_owner_claim_not_at_drop_point(
    db: Session,
    *,
    owner_id: uuid.UUID,
    found_item_id: uuid.UUID,
    claim_id: uuid.UUID,
) -> None:
    """Section 8.1 step 6 — owner claimed before item is at drop point."""
    body = (
        "Your claim is on file. This item has not been dropped off at the drop point yet. "
        "We will notify you when it is ready for collection."
    )
    link = f"/items/{found_item_id}"
    create_notification(
        db,
        owner_id,
        NotificationType.CLAIM_RECEIVED,
        title="Claim submitted — awaiting drop-off",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, owner_id, "FAiND", body, link)


def notify_owner_claim_ready_for_collection(
    db: Session,
    *,
    owner_id: uuid.UUID,
    found_item_id: uuid.UUID,
    claim_id: uuid.UUID,
    drop_point,
) -> None:
    """Section 8.1 step 6 — item at drop point; owner should collect in person."""
    dp_name = drop_point.name if drop_point else "the drop point"
    hours = drop_point.operating_hours if drop_point else None
    hours_part = f" during {hours}" if hours else ""
    body = (
        f"Your claim is on file. The item is at {dp_name}{hours_part}. "
        "Please bring your student ID to collect it."
    )
    link = f"/items/{found_item_id}"
    create_notification(
        db,
        owner_id,
        NotificationType.CLAIM_RECEIVED,
        title="Claim submitted — ready for collection",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, owner_id, "FAiND", body, link)


def notify_claim_call_to_collect(
    db: Session,
    *,
    claimant_id: uuid.UUID,
    found_item_id: uuid.UUID,
    claim_id: uuid.UUID,
    drop_point,
) -> None:
    """Section 8.5 — authority calls a claimant to collect."""
    dp_name = drop_point.name if drop_point else "the drop point"
    hours = drop_point.operating_hours if drop_point else None
    hours_part = f" during {hours}" if hours else ""
    body = (
        f"You have been called to collect your claimed item at {dp_name}{hours_part}. "
        "Please bring your student ID."
    )
    link = f"/items/{found_item_id}"
    create_notification(
        db,
        claimant_id,
        NotificationType.CLAIM_RECEIVED,
        title="Please come to collect",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, claimant_id, "FAiND", body, link)


def notify_owner_inquiry_reply(
    db: Session,
    *,
    owner_id: uuid.UUID,
    claim_id: uuid.UUID,
    found_item_id: uuid.UUID,
    reply_label: str,
) -> None:
    """Section 13.3 — authority quick reply sent to claim owner."""
    body = f"Drop point authority replied: {reply_label}"
    link = f"/claims/status/{claim_id}"
    create_notification(
        db,
        owner_id,
        NotificationType.GENERAL,
        title="Reply from drop point",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, owner_id, "FAiND", body, link)


def notify_claim_verified(
    db: Session,
    *,
    claimant_id: uuid.UUID,
    found_item_id: uuid.UUID,
    claim_id: uuid.UUID,
    drop_point,
) -> None:
    """Section 8.5 — claimant verified as owner; handover follows in W10."""
    dp_name = drop_point.name if drop_point else "the drop point"
    body = (
        f"You have been verified as the owner. Please visit {dp_name} to complete handover. "
        "Bring your student ID."
    )
    link = f"/items/{found_item_id}"
    create_notification(
        db,
        claimant_id,
        NotificationType.CLAIM_RECEIVED,
        title="Claim verified — owner confirmed",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, claimant_id, "FAiND", body, link)


def notify_claim_rejected_other_verified(
    db: Session,
    *,
    claimant_id: uuid.UUID,
    found_item_id: uuid.UUID,
    claim_id: uuid.UUID,
) -> None:
    """Section 8.5 — another claimant was verified for this item."""
    body = (
        "Your claim was not approved — another claimant was verified as the owner "
        "after an in-person review."
    )
    link = f"/items/{found_item_id}"
    create_notification(
        db,
        claimant_id,
        NotificationType.GENERAL,
        title="Claim not approved",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, claimant_id, "FAiND", body, link)


def notify_claim_rejected_manual(
    db: Session,
    *,
    claimant_id: uuid.UUID,
    found_item_id: uuid.UUID,
    claim_id: uuid.UUID,
) -> None:
    """Section 8.5 — authority manually rejected a claim."""
    body = (
        "Your claim was not approved after review at the drop point. "
        "If you believe this is an error, contact the drop point staff."
    )
    link = f"/items/{found_item_id}"
    create_notification(
        db,
        claimant_id,
        NotificationType.GENERAL,
        title="Claim rejected",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, claimant_id, "FAiND", body, link)


def notify_finder_dropoff_reminder(db: Session, *, item) -> None:
    """Section 14.1 — 24h drop-off reminder; registered finders only."""
    if not item.posted_by_id:
        return
    body = (
        "Reminder: please drop off your found item at the selected drop point within 48 hours "
        "to keep your report active."
    )
    link = f"/track/found?ref={item.tracking_reference}" if item.tracking_reference else f"/items/{item.id}"
    create_notification(
        db,
        item.posted_by_id,
        NotificationType.GENERAL,
        title="Drop-off reminder",
        body=body,
        link=link,
        reference_id=item.id,
    )
    db.flush()
    _fire_push(db, item.posted_by_id, "FAiND", body, link)


def notify_finder_dropoff_complete(db: Session, *, item) -> None:
    """Section 14.1 — drop-off confirmed; registered finder only."""
    if not item.posted_by_id:
        return
    body = "Your found item drop-off has been confirmed at the drop point."
    link = f"/items/{item.id}"
    create_notification(
        db,
        item.posted_by_id,
        NotificationType.GENERAL,
        title="Drop-off confirmed",
        body=body,
        link=link,
        reference_id=item.id,
    )
    db.flush()
    _fire_push(db, item.posted_by_id, "FAiND", body, link)


def notify_pending_claim_owners_item_ready(db: Session, *, item, drop_point) -> None:
    """Section 14.1 — item at drop point; notify pending claimants."""
    from app.models.claim import Claim, ClaimStatus

    claims = (
        db.query(Claim)
        .filter(Claim.found_item_id == item.id, Claim.status == ClaimStatus.PENDING)
        .all()
    )
    for claim in claims:
        notify_owner_claim_ready_for_collection(
            db,
            owner_id=claim.claimant_user_id,
            found_item_id=item.id,
            claim_id=claim.id,
            drop_point=drop_point,
        )


def notify_owner_found_item_overdue(
    db: Session,
    *,
    owner_id: uuid.UUID,
    found_item_id: uuid.UUID,
) -> None:
    """Section 14.1 — 48h overdue for owners with pending claims."""
    body = (
        "A found item you claimed is overdue for drop-off. "
        "We'll notify you when it arrives at the drop point."
    )
    link = f"/items/{found_item_id}"
    create_notification(
        db,
        owner_id,
        NotificationType.GENERAL,
        title="Found item not yet dropped off",
        body=body,
        link=link,
        reference_id=found_item_id,
    )
    db.flush()
    _fire_push(db, owner_id, "FAiND", body, link)


def notify_owners_drop_point_temporarily_closed(db: Session, *, drop_point) -> None:
    """Section 14.1 — drop point temporarily closed."""
    from app.models.claim import Claim, ClaimStatus
    from app.models.item import Item

    reason = drop_point.closed_reason or "No reason given"
    claims = (
        db.query(Claim)
        .join(Item, Claim.found_item_id == Item.id)
        .filter(Item.drop_point_id == drop_point.id, Claim.status == ClaimStatus.PENDING)
        .all()
    )
    for claim in claims:
        body = (
            f"{drop_point.name} is temporarily closed ({reason}). "
            "Your claim remains on file — we'll notify you when collection resumes."
        )
        link = f"/items/{claim.found_item_id}"
        create_notification(
            db,
            claim.claimant_user_id,
            NotificationType.GENERAL,
            title="Drop point temporarily closed",
            body=body,
            link=link,
            reference_id=claim.id,
        )
        db.flush()
        _fire_push(db, claim.claimant_user_id, "FAiND", body, link)


def notify_redemption_expiring_soon(
    db: Session,
    *,
    user_id: uuid.UUID,
    code: str,
    token_amount: int,
) -> None:
    """Section 14.1 — redemption code expiring soon."""
    body = (
        f"Your redemption code {code} ({token_amount} tokens) expires soon. "
        "Redeem it at a campus partner before it expires."
    )
    create_notification(
        db,
        user_id,
        NotificationType.GENERAL,
        title="Redemption code expiring soon",
        body=body,
        link="/dashboard",
    )
    db.flush()
    _fire_push(db, user_id, "FAiND", body, "/dashboard")


def notify_finder_handover_complete(
    db: Session,
    *,
    finder_id: uuid.UUID,
    item_id: uuid.UUID,
    handover_id: uuid.UUID,
) -> None:
    """Section 14.1 — handover complete; registered finder."""
    body = "An item you found has been returned to its owner."
    link = f"/items/{item_id}"
    create_notification(
        db,
        finder_id,
        NotificationType.ITEM_RETURNED,
        title="Item returned",
        body=body,
        link=link,
        reference_id=handover_id,
    )
    db.flush()
    _fire_push(db, finder_id, "FAiND", body, link)


def notify_handover_awaiting_owner(
    db: Session,
    *,
    claimant_id: uuid.UUID,
    handover_id: uuid.UUID,
    item_id: uuid.UUID,
) -> None:
    """Section 11 — owner digital sign-off required."""
    body = (
        "The drop point has recorded your handover. Please confirm digitally "
        "that you received the item in the condition shown."
    )
    link = f"/handover/{handover_id}"
    create_notification(
        db,
        claimant_id,
        NotificationType.GENERAL,
        title="Confirm item handover",
        body=body,
        link=link,
        reference_id=handover_id,
    )
    db.flush()
    _fire_push(db, claimant_id, "FAiND", body, link)


def notify_handover_completed(
    db: Session,
    *,
    claimant_id: uuid.UUID,
    item_id: uuid.UUID,
    handover_id: uuid.UUID,
    owner_confirmed: bool,
    authority_override: bool,
) -> None:
    """Section 11 — handover complete, item returned."""
    if authority_override:
        body = "Your item handover has been completed by the drop point authority."
    else:
        body = "Thank you for confirming. Your item has been marked as returned."
    link = f"/handover/{handover_id}"
    create_notification(
        db,
        claimant_id,
        NotificationType.ITEM_RETURNED,
        title="Item returned",
        body=body,
        link=link,
        reference_id=handover_id,
    )
    db.flush()
    _fire_push(db, claimant_id, "FAiND", body, link)


def notify_post_expiring(
    db: Session,
    owner_id: uuid.UUID,
    item_id: uuid.UUID,
    days_left: int,
) -> None:
    """Section 21.1 / 21.2 — post expires within 3 days."""
    day_word = "day" if days_left == 1 else "days"
    body = (
        f"Your post expires in {days_left} {day_word}. "
        "Extend it from your dashboard if you still need it."
    )
    link = f"/items/{item_id}"
    create_notification(
        db,
        owner_id,
        NotificationType.POST_EXPIRING,
        title="Post expiring soon",
        body=body,
        link=link,
        reference_id=item_id,
    )
    db.flush()
    _fire_push(db, owner_id, "FAiND", body, link)


def notify_potential_match_expired(
    db: Session,
    owner_id: uuid.UUID,
    lost_item_id: uuid.UUID,
    match_id: uuid.UUID,
) -> None:
    """Section 11.1 / 21.3 — POTENTIAL_MATCH expired after 14 days."""
    body = (
        "Your potential match has expired. Your item is back in the active pool."
    )
    link = f"/items/{lost_item_id}"
    create_notification(
        db, owner_id, NotificationType.POTENTIAL_MATCH_EXPIRED,
        title="Potential match expired",
        body=body, link=link, reference_id=match_id,
    )
    db.flush()
    _fire_push(db, owner_id, "FAiND", body, link)


def notify_item_returned(
    db: Session,
    *,
    lost_owner_id: uuid.UUID,
    found_owner_id: uuid.UUID,
    return_id: uuid.UUID,
    lost_item_id: uuid.UUID,
    found_item_id: uuid.UUID,
) -> None:
    """Section 15.3 — both parties notified when return is confirmed."""
    owner_body = "You confirmed receipt — this item is now marked as returned."
    finder_body = "The owner confirmed the return."
    owner_link = f"/returns/{return_id}"
    finder_link = f"/returns/{return_id}"

    create_notification(
        db,
        lost_owner_id,
        NotificationType.ITEM_RETURNED,
        title="Item returned",
        body=owner_body,
        link=owner_link,
        reference_id=return_id,
    )
    create_notification(
        db,
        found_owner_id,
        NotificationType.ITEM_RETURNED,
        title="Successful return",
        body=finder_body,
        link=finder_link,
        reference_id=return_id,
    )
    db.flush()
    _fire_push(db, lost_owner_id, "FAiND", owner_body, owner_link)
    _fire_push(db, found_owner_id, "FAiND", finder_body, finder_link)


def notify_finder_handed_over(
    db: Session,
    *,
    owner_id: uuid.UUID,
    match_id: uuid.UUID,
    return_id: uuid.UUID,
) -> None:
    """Section 15.1 — finder confirmed handover; owner must confirm receipt."""
    body = (
        "The finder confirmed they handed over your item. "
        "Please confirm receipt when you have it."
    )
    link = f"/returns/confirm/{match_id}"
    create_notification(
        db,
        owner_id,
        NotificationType.GENERAL,
        title="Confirm item receipt",
        body=body,
        link=link,
        reference_id=return_id,
    )
    db.flush()
    _fire_push(db, owner_id, "FAiND", body, link)


def notify_return_disputed(
    db: Session,
    *,
    record,
    filed_by_id: uuid.UUID,
) -> None:
    """Section 16.4 — both parties notified when a return is disputed."""
    link = f"/returns/{record.id}"
    filer_is_owner = filed_by_id == record.lost_owner_id
    other_id = record.found_owner_id if filer_is_owner else record.lost_owner_id
    filer_body = "Your dispute was submitted. An admin will review this return."
    other_body = "The other party disputed this return. An admin will review the case."
    create_notification(
        db,
        filed_by_id,
        NotificationType.GENERAL,
        title="Return dispute submitted",
        body=filer_body,
        link=link,
        reference_id=record.id,
    )
    create_notification(
        db,
        other_id,
        NotificationType.GENERAL,
        title="Return disputed",
        body=other_body,
        link=link,
        reference_id=record.id,
    )
    db.flush()
    _fire_push(db, filed_by_id, "FAiND", filer_body, link)
    _fire_push(db, other_id, "FAiND", other_body, link)


def notify_return_receipt_reminder(
    db: Session,
    *,
    owner_id: uuid.UUID,
    match_id: uuid.UUID,
    return_id: uuid.UUID,
    lost_item_id: uuid.UUID,
) -> None:
    """Section 15.1 — finder confirmed but owner has not within 7 days."""
    body = (
        "The finder marked your item as handed over. "
        "Please confirm receipt when you have it."
    )
    link = f"/returns/confirm/{match_id}"
    create_notification(
        db,
        owner_id,
        NotificationType.GENERAL,
        title="Confirm your item receipt",
        body=body,
        link=link,
        reference_id=return_id,
    )
    db.flush()
    _fire_push(db, owner_id, "FAiND", body, link)


def notify_report_reviewed(
    db: Session,
    reporter_id: uuid.UUID,
    report_id: uuid.UUID,
) -> None:
    """Section 13.1/13.2 — reporter notified when admin acts (outcome not disclosed)."""
    body = "Thank you — your report has been reviewed."
    create_notification(
        db,
        reporter_id,
        NotificationType.GENERAL,
        title="Report reviewed",
        body=body,
        link="/dashboard",
        reference_id=report_id,
    )
    db.flush()
    _fire_push(db, reporter_id, "FAiND", body, "/dashboard")


def notify_admins_report_escalated(
    db: Session,
    *,
    report_type: str,
    report_id: uuid.UUID,
) -> None:
    """Section 13 — auto-escalation at 3+ distinct reporters."""
    from app.services import admin_notification_service

    admin_notification_service.notify_admins_report_escalated(
        db, report_type=report_type, report_id=report_id
    )


def notify_user_warned(db: Session, user_id: uuid.UUID) -> None:
    """Section 13.4 — warn user after admin review."""
    body = (
        "A moderator reviewed reports about your account. "
        "Please follow FAiND community guidelines."
    )
    create_notification(
        db,
        user_id,
        NotificationType.GENERAL,
        title="Community guidelines reminder",
        body=body,
        link="/settings",
        reference_id=None,
    )
    db.flush()
    _fire_push(db, user_id, "FAiND", body, "/settings")


def notify_account_suspended(db: Session, user_id: uuid.UUID) -> None:
    """Section 4.7 — suspended user notification."""
    body = (
        "Your account has been suspended pending review. "
        "Contact support if you believe this is an error."
    )
    create_notification(
        db,
        user_id,
        NotificationType.ACCOUNT_SUSPENDED,
        title="Account suspended",
        body=body,
        link="/settings",
        reference_id=None,
    )
    db.flush()
    _fire_push(db, user_id, "FAiND", body, "/settings")


def notify_account_unsuspended(db: Session, user_id: uuid.UUID) -> None:
    """Section 4.7 — suspension lifted."""
    body = "Your account suspension has been lifted."
    create_notification(
        db,
        user_id,
        NotificationType.ACCOUNT_UNSUSPENDED,
        title="Account restored",
        body=body,
        link="/dashboard",
        reference_id=None,
    )
    db.flush()
    _fire_push(db, user_id, "FAiND", body, "/dashboard")


_NON_DELETABLE_TYPES = frozenset({
    NotificationType.MATCH_FOUND,
    NotificationType.POTENTIAL_MATCH_EXPIRED,
    NotificationType.VERIFICATION_PASSED,
    NotificationType.VERIFICATION_FAILED,
    NotificationType.VERIFICATION_REVIEW,
    NotificationType.CLAIM_RECEIVED,
    NotificationType.POST_EXPIRING,
    NotificationType.ACCOUNT_SUSPENDED,
})

_DELETABLE_TYPES = frozenset({
    NotificationType.ITEM_RETURNED,
    NotificationType.ACCOUNT_UNSUSPENDED,
})

# GENERAL notifications — title substring rules (lowercased)
_NON_DELETABLE_GENERAL_SUBSTRINGS = (
    "confirm item receipt",
    "confirm your item receipt",
    "confirm item handover",
    "return dispute",
    "return disputed",
    "dispute resolved",
    "claim not approved",
    "claim rejected",
    "drop-off reminder",
    "drop-off confirmed",
    "drop point temporarily closed",
    "redemption code expiring",
    "potential match",
    "match found",
    "post expiring",
    "account suspended",
    "community guidelines",
    "report reviewed",
)

_DELETABLE_GENERAL_SUBSTRINGS = (
    "post extended",
    "post removed",
)


def is_notification_deletable(notification: Notification) -> bool:
    """Whether the user may permanently delete this notification."""
    t = notification.notification_type
    if t in _NON_DELETABLE_TYPES:
        return False
    if t in _DELETABLE_TYPES:
        return True
    if t != NotificationType.GENERAL:
        return False
    title = (notification.title or "").strip().lower()
    for sub in _NON_DELETABLE_GENERAL_SUBSTRINGS:
        if sub in title:
            return False
    for sub in _DELETABLE_GENERAL_SUBSTRINGS:
        if sub in title:
            return True
    return False


def delete_notification(
    db: Session,
    user_id: uuid.UUID,
    notification_id: uuid.UUID,
) -> bool:
    """Permanently delete one deletable notification. Returns False if not found."""
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user_id)
        .first()
    )
    if not notif:
        return False
    if not is_notification_deletable(notif):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This notification cannot be deleted.",
        )
    db.delete(notif)
    db.commit()
    return True


def delete_deletable_notifications(db: Session, user_id: uuid.UUID) -> int:
    """Permanently delete all deletable notifications for the user."""
    rows = (
        db.query(Notification)
        .filter(Notification.user_id == user_id)
        .all()
    )
    deleted = 0
    for notif in rows:
        if is_notification_deletable(notif):
            db.delete(notif)
            deleted += 1
    if deleted:
        db.commit()
    return deleted


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

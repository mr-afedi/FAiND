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


def notify_verification_passed(
    db: Session,
    lost_owner_id: uuid.UUID,
    found_owner_id: uuid.UUID,
    match_id: uuid.UUID,
    conversation_id: uuid.UUID,
    lost_item_id: uuid.UUID,
    found_item_id: uuid.UUID,
) -> None:
    """Section 11.1 — verification passed: both parties notified, chat unlocked."""
    lost_body = "Your ownership verification passed. You can now chat with the finder."
    found_body = "The lost item owner verified ownership. Chat is now unlocked."
    lost_link = f"/messages/{conversation_id}"
    found_link = f"/messages/{conversation_id}"

    create_notification(
        db, lost_owner_id, NotificationType.VERIFICATION_PASSED,
        title="Verification passed!",
        body=lost_body, link=lost_link, reference_id=match_id,
    )
    create_notification(
        db, found_owner_id, NotificationType.VERIFICATION_PASSED,
        title="Chat unlocked!",
        body=found_body, link=found_link, reference_id=match_id,
    )
    db.flush()
    _fire_push(db, lost_owner_id, "FAiND", lost_body, lost_link)
    _fire_push(db, found_owner_id, "FAiND", found_body, found_link)


def notify_verification_failed(
    db: Session,
    user_id: uuid.UUID,
    match_id: uuid.UUID,
    lost_item_id: uuid.UUID,
    attempts_remaining: int,
) -> None:
    """Section 11.1 — verification failed: claimant only."""
    body = (
        f"Your verification answers did not match. "
        f"{attempts_remaining} attempt(s) remaining in the next 24 hours."
    )
    link = f"/verify-ownership/{match_id}"
    create_notification(
        db, user_id, NotificationType.VERIFICATION_FAILED,
        title="Verification failed",
        body=body, link=link, reference_id=match_id,
    )
    db.flush()
    _fire_push(db, user_id, "FAiND", body, link)


def notify_verification_review(
    db: Session,
    user_id: uuid.UUID,
    match_id: uuid.UUID,
    lost_item_id: uuid.UUID,
) -> None:
    """Section 11.1 — sent to admin review: claimant only."""
    body = (
        "Your verification score is in the review range. "
        "An admin will review your answers — we'll notify you when decided."
    )
    link = f"/items/{lost_item_id}"
    create_notification(
        db, user_id, NotificationType.VERIFICATION_REVIEW,
        title="Verification under review",
        body=body, link=link, reference_id=match_id,
    )
    db.flush()
    _fire_push(db, user_id, "FAiND", body, link)


def notify_claim_received(
    db: Session,
    lost_owner_id: uuid.UUID,
    lost_item_id: uuid.UUID,
    claim_id: uuid.UUID,
) -> None:
    """Path B (V4.3): generic claim notice — no finder identity or answers revealed."""
    body = (
        "Someone claims to have found your item. We are verifying their claim."
    )
    link = f"/items/{lost_item_id}"
    create_notification(
        db,
        lost_owner_id,
        NotificationType.CLAIM_RECEIVED,
        title="New claim on your lost item",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, lost_owner_id, "FAiND", body, link)


def notify_claim_under_review(
    db: Session,
    lost_owner_id: uuid.UUID,
    lost_item_id: uuid.UUID,
    claim_id: uuid.UUID,
) -> None:
    """Path B claim in admin review range — inform lost owner."""
    body = "A finder claim on your lost item needs admin review."
    link = f"/items/{lost_item_id}"
    create_notification(
        db,
        lost_owner_id,
        NotificationType.VERIFICATION_REVIEW,
        title="Claim under review",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, lost_owner_id, "FAiND", body, link)


def notify_path_b_failed(
    db: Session,
    user_id: uuid.UUID,
    lost_item_id: uuid.UUID,
    attempts_remaining: int,
) -> None:
    """Path B claim rejected — notify finder only."""
    body = (
        f"Your I Have This Item claim was not approved. "
        f"{attempts_remaining} attempt(s) remaining for this item."
    )
    link = f"/i-have-this-item/{lost_item_id}"
    create_notification(
        db,
        user_id,
        NotificationType.VERIFICATION_FAILED,
        title="Claim not approved",
        body=body,
        link=link,
        reference_id=lost_item_id,
    )
    db.flush()
    _fire_push(db, user_id, "FAiND", body, link)


def notify_path_c_claim_received(
    db: Session,
    finder_id: uuid.UUID,
    found_item_id: uuid.UUID,
    claim_id: uuid.UUID,
) -> None:
    """Path C — finder notified when someone claims their found item."""
    body = (
        "Someone believes your found item may be theirs. "
        "We are verifying their claim."
    )
    link = f"/items/{found_item_id}"
    create_notification(
        db,
        finder_id,
        NotificationType.CLAIM_RECEIVED,
        title="New claim on your found item",
        body=body,
        link=link,
        reference_id=claim_id,
    )
    db.flush()
    _fire_push(db, finder_id, "FAiND", body, link)


def notify_path_c_under_review(
    db: Session,
    claimant_id: uuid.UUID,
    finder_id: uuid.UUID,
    found_item_id: uuid.UUID,
    match_id: uuid.UUID,
) -> None:
    """Path C — both parties notified when claim is in admin review."""
    claimant_body = (
        "Your This Might Be Mine claim is under admin review. "
        "We'll notify you when a decision is made."
    )
    finder_body = (
        "A claim on your found item is under admin review. "
        "We'll notify you when a decision is made."
    )
    claimant_link = f"/this-might-be-mine/{found_item_id}"
    finder_link = f"/items/{found_item_id}"
    create_notification(
        db, claimant_id, NotificationType.VERIFICATION_REVIEW,
        title="Claim under review", body=claimant_body,
        link=claimant_link, reference_id=match_id,
    )
    create_notification(
        db, finder_id, NotificationType.VERIFICATION_REVIEW,
        title="Claim under review", body=finder_body,
        link=finder_link, reference_id=match_id,
    )
    db.flush()
    _fire_push(db, claimant_id, "FAiND", claimant_body, claimant_link)
    _fire_push(db, finder_id, "FAiND", finder_body, finder_link)


def notify_path_c_rejected(
    db: Session,
    claimant_id: uuid.UUID,
    finder_id: uuid.UUID,
    found_item_id: uuid.UUID,
    match_id: uuid.UUID,
    attempts_remaining: int,
) -> None:
    """Path C — both parties notified when claim is rejected."""
    claimant_body = (
        f"Your This Might Be Mine claim was not approved. "
        f"{attempts_remaining} attempt(s) remaining for this item."
    )
    finder_body = "A claim on your found item was not approved."
    claimant_link = f"/this-might-be-mine/{found_item_id}"
    finder_link = f"/items/{found_item_id}"
    create_notification(
        db, claimant_id, NotificationType.VERIFICATION_FAILED,
        title="Claim not approved", body=claimant_body,
        link=claimant_link, reference_id=match_id,
    )
    create_notification(
        db, finder_id, NotificationType.VERIFICATION_FAILED,
        title="Claim not approved", body=finder_body,
        link=finder_link, reference_id=match_id,
    )
    db.flush()
    _fire_push(db, claimant_id, "FAiND", claimant_body, claimant_link)
    _fire_push(db, finder_id, "FAiND", finder_body, finder_link)


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
    finder_body = "The owner confirmed the return. You earned +5 trust points!"
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


def notify_appreciation_received(
    db: Session,
    *,
    finder_id: uuid.UUID,
    return_id: uuid.UUID,
) -> None:
    """Section 20.2 — finder notified (no amount disclosed)."""
    body = "The owner expressed appreciation to you for helping return their item."
    link = f"/returns/{return_id}"
    create_notification(
        db,
        finder_id,
        NotificationType.GENERAL,
        title="Appreciation received",
        body=body,
        link=link,
        reference_id=return_id,
    )
    db.flush()
    _fire_push(db, finder_id, "FAiND", body, link)


def notify_appreciation_sent(
    db: Session,
    *,
    owner_id: uuid.UUID,
    return_id: uuid.UUID,
) -> None:
    """Section 20 — owner confirmation after successful payment."""
    body = "Your appreciation was sent successfully. Thank you for supporting the finder!"
    link = f"/returns/{return_id}"
    create_notification(
        db,
        owner_id,
        NotificationType.GENERAL,
        title="Appreciation sent",
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
    tip_frozen: bool,
) -> None:
    """Section 16.4 — both parties notified when a return is disputed."""
    link = f"/returns/{record.id}"
    filer_is_owner = filed_by_id == record.lost_owner_id
    other_id = record.found_owner_id if filer_is_owner else record.lost_owner_id
    filer_body = (
        "Your dispute was submitted. An admin will review this return."
        + (" Any appreciation payment is frozen pending review." if tip_frozen else "")
    )
    other_body = (
        "The other party disputed this return. An admin will review the case."
        + (" Any tip on this return is frozen pending review." if tip_frozen else "")
    )
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
    target_id: uuid.UUID,
) -> None:
    """Section 13 — auto-escalation at 3+ distinct reporters."""
    from app.models.user import User, UserRole, AccountStatus

    admins = (
        db.query(User)
        .filter(
            User.role.in_((UserRole.ROOT_ADMIN, UserRole.ASSISTANT_ROOT_ADMIN)),
            User.status == AccountStatus.ACTIVE,
        )
        .all()
    )
    label = "post" if report_type == "post" else "user"
    body = (
        f"A {label} report was auto-escalated after {_ESCALATION_LABEL} "
        "distinct reports. Priority review required."
    )
    link = f"/admin/reports?type={label}&target={target_id}"
    for admin in admins:
        create_notification(
            db,
            admin.id,
            NotificationType.GENERAL,
            title="Priority report — review needed",
            body=body,
            link=link,
            reference_id=target_id,
        )
    db.flush()


_ESCALATION_LABEL = "three or more"


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
    body = "Your account has been suspended following a moderation review. Contact support if you believe this is an error."
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


def notify_fraud_alert(
    db: Session,
    *,
    admin_id: uuid.UUID,
    user_id: uuid.UUID,
    title: str,
    body: str,
    link: str,
    reference_id: uuid.UUID,
) -> None:
    """Section 18 — admin fraud monitoring alert (in-app + push)."""
    create_notification(
        db,
        admin_id,
        NotificationType.GENERAL,
        title=title,
        body=body,
        link=link,
        reference_id=reference_id,
    )
    db.flush()
    _fire_push(db, admin_id, "FAiND", body, link)


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

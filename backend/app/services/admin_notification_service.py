"""
Admin notification helpers — Feature R reinforcement.

Links use format admin:{section}:{resource_id} for in-dashboard deep links.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models.notification import NotificationType
from app.models.user import User, UserRole, AccountStatus
from app.services import notification_service

ADMIN_SECTIONS = frozenset(
    {
        "claims",
        "disputes",
        "reports",
        "posts",
        "users",
        "logs",
        "authorities",
        "supervisors",
        "redemption",
        "returned",
        "drop_points",
    }
)


def admin_link(section: str, resource_id: uuid.UUID) -> str:
    if section not in ADMIN_SECTIONS:
        raise ValueError(f"Invalid admin section: {section}")
    return f"admin:{section}:{resource_id}"


def _active_admins(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(
            User.role == UserRole.ROOT_ADMIN,
            User.status == AccountStatus.ACTIVE,
        )
        .all()
    )


def notify_all_admins(
    db: Session,
    *,
    title: str,
    body: str,
    link: str,
    reference_id: uuid.UUID,
    send_push: bool = False,
) -> None:
    from app.services import push_service

    for admin in _active_admins(db):
        notification_service.create_notification(
            db,
            admin.id,
            NotificationType.GENERAL,
            title=title,
            body=body,
            link=link,
            reference_id=reference_id,
        )
        if send_push:
            push_service.send_push_to_admin(
                db,
                admin_user_id=admin.id,
                title=title,
                body=body,
                url=_admin_push_url(link),
            )
    db.flush()


def _admin_push_url(link: str) -> str:
    if link.startswith("admin:"):
        parts = link.split(":")
        if len(parts) >= 2:
            return f"/admin?section={parts[1]}"
    return "/admin"


def notify_admins_claim_in_review(
    db: Session,
    *,
    match_id: uuid.UUID,
    path: str,
) -> None:
    path_label = path.replace("_", " ").upper()
    notify_all_admins(
        db,
        title="Claim awaiting admin review",
        body=f"A {path_label} claim scored in the 0.50–0.75 review range and needs your decision.",
        link=admin_link("claims", match_id),
        reference_id=match_id,
    )


def notify_admins_verification_dispute(
    db: Session,
    *,
    match_id: uuid.UUID,
    lost_item_id: uuid.UUID,
) -> None:
    notify_all_admins(
        db,
        title="Verification dispute — multiple claimants",
        body=(
            "Two claimants both exceeded the approval threshold on the same item. "
            "Review evidence and pick the legitimate match."
        ),
        link=admin_link("disputes", match_id),
        reference_id=match_id,
    )


def notify_admins_return_disputed(
    db: Session,
    *,
    return_id: uuid.UUID,
) -> None:
    notify_all_admins(
        db,
        title="Return disputed",
        body="A completed return was disputed within the 7-day window. Review return evidence.",
        link=admin_link("disputes", return_id),
        reference_id=return_id,
    )


def notify_admins_manual_dispute(
    db: Session,
    *,
    return_id: uuid.UUID,
) -> None:
    notify_all_admins(
        db,
        title="Return flagged for admin review",
        body="A return confirmation was flagged for manual admin review.",
        link=admin_link("disputes", return_id),
        reference_id=return_id,
    )


def notify_admins_user_reported_multiple(
    db: Session,
    *,
    user_id: uuid.UUID,
) -> None:
    notify_all_admins(
        db,
        title="User reported multiple times",
        body="A user received 3+ reports from different reporters. Priority review recommended.",
        link=admin_link("users", user_id),
        reference_id=user_id,
    )


def notify_admins_report_escalated(
    db: Session,
    *,
    report_type: str,
    report_id: uuid.UUID,
) -> None:
    """Auto-escalation at 3+ distinct reporters — links to the report queue item."""
    if report_type not in ("post", "user"):
        raise ValueError(f"Invalid report_type: {report_type}")
    label = "post" if report_type == "post" else "user"
    notify_all_admins(
        db,
        title="Priority report — review needed",
        body=(
            f"A {label} report was auto-escalated after three or more "
            "distinct reports. Priority review required."
        ),
        link=f"admin:reports:{report_type}:{report_id}",
        reference_id=report_id,
    )


def notify_admins_new_claim(
    db: Session,
    *,
    claim_id: uuid.UUID,
    found_item_id: uuid.UUID,
    drop_point_name: str,
    path: str,
) -> None:
    notify_all_admins(
        db,
        title="New claim submitted",
        body=(
            f"A Path {path} claim was submitted for an item at {drop_point_name}. "
            "Review the claims overview."
        ),
        link=admin_link("claims", found_item_id),
        reference_id=claim_id,
    )


def notify_admins_item_overdue(
    db: Session,
    *,
    item_id: uuid.UUID,
    drop_point_name: str,
) -> None:
    notify_all_admins(
        db,
        title="Item overdue for drop-off",
        body=(
            f"A found item at {drop_point_name} passed the 48-hour drop-off deadline "
            "without being received."
        ),
        link=admin_link("posts", item_id),
        reference_id=item_id,
        send_push=True,
    )


def notify_admins_item_unconfirmed(
    db: Session,
    *,
    item_id: uuid.UUID,
    drop_point_name: str,
) -> None:
    notify_all_admins(
        db,
        title="Item unconfirmed after 72 hours",
        body=(
            f"A found item at {drop_point_name} was hidden as UNCONFIRMED after 72 hours "
            "with no drop-off."
        ),
        link=admin_link("posts", item_id),
        reference_id=item_id,
        send_push=True,
    )


def notify_admins_handover_override(
    db: Session,
    *,
    handover_id: uuid.UUID,
    item_id: uuid.UUID,
    drop_point_name: str,
) -> None:
    notify_all_admins(
        db,
        title="Authority handover override",
        body=(
            f"An authority at {drop_point_name} completed a handover without owner "
            "digital sign-off. Review the admin log for details."
        ),
        link=admin_link("logs", handover_id),
        reference_id=item_id,
        send_push=True,
    )


def notify_admins_redemption_used(
    db: Session,
    *,
    redemption_code_id: uuid.UUID,
    code: str,
    token_amount: int,
) -> None:
    notify_all_admins(
        db,
        title="Redemption code used",
        body=f"Redemption code {code} was redeemed for {token_amount} tokens.",
        link=admin_link("redemption", redemption_code_id),
        reference_id=redemption_code_id,
    )


def notify_admins_authority_created(
    db: Session,
    *,
    authority_id: uuid.UUID,
    email: str,
    drop_point_name: str,
) -> None:
    notify_all_admins(
        db,
        title="Authority account created",
        body=f"New authority account {email} was created for {drop_point_name}.",
        link=admin_link("authorities", authority_id),
        reference_id=authority_id,
        send_push=True,
    )


def notify_admins_authority_deactivated(
    db: Session,
    *,
    authority_id: uuid.UUID,
    email: str,
    drop_point_name: str,
) -> None:
    notify_all_admins(
        db,
        title="Authority account deactivated",
        body=f"Authority account {email} at {drop_point_name} was deactivated.",
        link=admin_link("authorities", authority_id),
        reference_id=authority_id,
        send_push=True,
    )


def notify_admins_supervisor_created(
    db: Session,
    *,
    supervisor_id: uuid.UUID,
    email: str,
) -> None:
    notify_all_admins(
        db,
        title="Supervisor account created",
        body=f"A new drop point supervisor account was created: {email}.",
        link=admin_link("supervisors", supervisor_id),
        reference_id=supervisor_id,
        send_push=True,
    )


def notify_admins_supervisor_modified(
    db: Session,
    *,
    supervisor_id: uuid.UUID,
    email: str,
) -> None:
    notify_all_admins(
        db,
        title="Supervisor account updated",
        body=f"Supervisor account {email} was updated.",
        link=admin_link("supervisors", supervisor_id),
        reference_id=supervisor_id,
        send_push=True,
    )

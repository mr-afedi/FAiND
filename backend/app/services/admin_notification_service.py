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
    {"claims", "disputes", "reports", "fraud", "posts", "users", "logs"}
)


def admin_link(section: str, resource_id: uuid.UUID) -> str:
    if section not in ADMIN_SECTIONS:
        raise ValueError(f"Invalid admin section: {section}")
    return f"admin:{section}:{resource_id}"


def _active_admins(db: Session) -> list[User]:
    return (
        db.query(User)
        .filter(
            User.role.in_((UserRole.ROOT_ADMIN, UserRole.ASSISTANT_ROOT_ADMIN)),
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
) -> None:
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
    db.flush()


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

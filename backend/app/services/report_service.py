"""
ReportService — post and user reporting (Section 13).

All report creation and admin resolution flows go through this module.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemStatus
from app.models.user import User, AccountStatus
from app.models.conversation import Conversation
from app.models.report import (
    PostReport,
    UserReport,
    ReportStatus,
    AdminReportAction,
)
from app.schemas.report import SubmitPostReportRequest, SubmitUserReportRequest
from app.services import trust_service, fraud_service, notification_service
from app.services import matching_service
from app.services.trust_service import get_trust_tier

_ESCALATION_DISTINCT_REPORTERS = 3
_DUPLICATE_MSG = "You have already reported this. Each post or user can only be reported once."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _reporter_deprioritized(reporter: User) -> bool:
    return (
        reporter.status == AccountStatus.SUSPENDED
        or reporter.reports_suppressed
    )


def submit_post_report(
    db: Session,
    *,
    item_id: uuid.UUID,
    reporter: User,
    payload: SubmitPostReportRequest,
) -> PostReport:
    if reporter.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot submit reports.",
        )

    item = db.query(Item).filter(Item.id == item_id).first()
    if not item or item.status == ItemStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")

    if item.posted_by_id == reporter.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot report your own post.",
        )

    if item.university_id != reporter.university_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")

    existing = (
        db.query(PostReport)
        .filter(PostReport.reporter_id == reporter.id, PostReport.item_id == item_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_DUPLICATE_MSG)

    report = PostReport(
        university_id=reporter.university_id,
        reporter_id=reporter.id,
        item_id=item_id,
        reason=payload.reason,
        detail_text=payload.detail_text,
        status=ReportStatus.PENDING,
    )
    db.add(report)
    db.flush()

    _maybe_escalate_post_reports(db, item_id)
    db.commit()
    db.refresh(report)
    return report


def submit_user_report(
    db: Session,
    *,
    reported_user_id: uuid.UUID,
    reporter: User,
    payload: SubmitUserReportRequest,
) -> UserReport:
    if reporter.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Suspended accounts cannot submit reports.",
        )

    if reported_user_id == reporter.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot report yourself.",
        )

    reported = db.query(User).filter(User.id == reported_user_id).first()
    if not reported or reported.status == AccountStatus.DELETED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if reported.university_id != reporter.university_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if payload.conversation_id:
        conv = (
            db.query(Conversation)
            .filter(Conversation.id == payload.conversation_id)
            .first()
        )
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found.",
            )
        parties = {conv.lost_owner_id, conv.found_owner_id}
        if reporter.id not in parties or reported_user_id not in parties:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a participant in this conversation.",
            )

    existing = (
        db.query(UserReport)
        .filter(
            UserReport.reporter_id == reporter.id,
            UserReport.reported_user_id == reported_user_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=_DUPLICATE_MSG)

    report = UserReport(
        university_id=reporter.university_id,
        reporter_id=reporter.id,
        reported_user_id=reported_user_id,
        reason=payload.reason,
        detail_text=payload.detail_text,
        context_conversation_id=payload.conversation_id,
        status=ReportStatus.PENDING,
    )
    db.add(report)
    db.flush()

    report_count = (
        db.query(UserReport)
        .filter(UserReport.reported_user_id == reported_user_id)
        .count()
    )
    trust_service.penalise_user_report_received(
        db, reported_user_id, report_count, reporter_id=reporter.id
    )
    fraud_service.record_user_report(
        db,
        reported_user_id=reported_user_id,
        report_id=report.id,
        report_count=report_count,
    )

    _maybe_escalate_user_reports(db, reported_user_id)
    db.commit()
    db.refresh(report)
    return report


def _distinct_post_reporters(db: Session, item_id: uuid.UUID) -> int:
    return (
        db.query(func.count(func.distinct(PostReport.reporter_id)))
        .filter(PostReport.item_id == item_id)
        .scalar()
    ) or 0


def _distinct_user_reporters(db: Session, reported_user_id: uuid.UUID) -> int:
    return (
        db.query(func.count(func.distinct(UserReport.reporter_id)))
        .filter(UserReport.reported_user_id == reported_user_id)
        .scalar()
    ) or 0


def _maybe_escalate_post_reports(db: Session, item_id: uuid.UUID) -> None:
    if _distinct_post_reporters(db, item_id) < _ESCALATION_DISTINCT_REPORTERS:
        return
    pending = (
        db.query(PostReport)
        .filter(
            PostReport.item_id == item_id,
            PostReport.status == ReportStatus.PENDING,
            PostReport.auto_escalated.is_(False),
        )
        .all()
    )
    if not pending:
        return
    for row in pending:
        row.auto_escalated = True
    db.flush()
    notification_service.notify_admins_report_escalated(
        db, report_type="post", target_id=item_id
    )


def _maybe_escalate_user_reports(db: Session, reported_user_id: uuid.UUID) -> None:
    if _distinct_user_reporters(db, reported_user_id) < _ESCALATION_DISTINCT_REPORTERS:
        return
    pending = (
        db.query(UserReport)
        .filter(
            UserReport.reported_user_id == reported_user_id,
            UserReport.status == ReportStatus.PENDING,
            UserReport.auto_escalated.is_(False),
        )
        .all()
    )
    if not pending:
        return
    for row in pending:
        row.auto_escalated = True
    db.flush()
    notification_service.notify_admins_report_escalated(
        db, report_type="user", target_id=reported_user_id
    )


def _resolve_post_report(
    db: Session,
    report: PostReport,
    admin: User,
    action: AdminReportAction,
) -> None:
    now = _now()
    report.status = (
        ReportStatus.DISMISSED
        if action == AdminReportAction.DISMISS
        else ReportStatus.RESOLVED
    )
    report.admin_action = action
    report.resolved_by_id = admin.id
    report.resolved_at = now
    notification_service.notify_report_reviewed(db, report.reporter_id, report.id)


def _resolve_user_report(
    db: Session,
    report: UserReport,
    admin: User,
    action: AdminReportAction,
) -> None:
    now = _now()
    report.status = (
        ReportStatus.DISMISSED
        if action == AdminReportAction.DISMISS
        else ReportStatus.RESOLVED
    )
    report.admin_action = action
    report.resolved_by_id = admin.id
    report.resolved_at = now
    notification_service.notify_report_reviewed(db, report.reporter_id, report.id)


def admin_dismiss_post_report(db: Session, report_id: uuid.UUID, admin: User) -> PostReport:
    report = _get_post_report(db, report_id)
    _resolve_post_report(db, report, admin, AdminReportAction.DISMISS)
    db.commit()
    db.refresh(report)
    return report


def admin_remove_post(db: Session, report_id: uuid.UUID, admin: User) -> PostReport:
    report = _get_post_report(db, report_id)
    item = db.query(Item).filter(Item.id == report.item_id).first()
    if item and item.status != ItemStatus.ARCHIVED:
        item.status = ItemStatus.ARCHIVED
        item.updated_at = _now()
        matching_service.cleanup_on_item_archive(db, item.id)
    _resolve_post_report(db, report, admin, AdminReportAction.REMOVE_POST)
    _resolve_sibling_post_reports(db, report.item_id, admin, AdminReportAction.REMOVE_POST)
    db.commit()
    db.refresh(report)
    return report


def _resolve_sibling_post_reports(
    db: Session,
    item_id: uuid.UUID,
    admin: User,
    action: AdminReportAction,
) -> None:
    siblings = (
        db.query(PostReport)
        .filter(
            PostReport.item_id == item_id,
            PostReport.status == ReportStatus.PENDING,
        )
        .all()
    )
    for sib in siblings:
        _resolve_post_report(db, sib, admin, action)
        notification_service.notify_report_reviewed(db, sib.reporter_id, sib.id)


def admin_dismiss_user_report(db: Session, report_id: uuid.UUID, admin: User) -> UserReport:
    report = _get_user_report(db, report_id)
    _resolve_user_report(db, report, admin, AdminReportAction.DISMISS)
    db.commit()
    db.refresh(report)
    return report


def admin_warn_user(db: Session, report_id: uuid.UUID, admin: User) -> UserReport:
    report = _get_user_report(db, report_id)
    notification_service.notify_user_warned(db, report.reported_user_id)
    _resolve_user_report(db, report, admin, AdminReportAction.WARN_USER)
    db.commit()
    db.refresh(report)
    return report


def admin_suspend_user(db: Session, report_id: uuid.UUID, admin: User) -> UserReport:
    report = _get_user_report(db, report_id)
    target = db.query(User).filter(User.id == report.reported_user_id).first()
    if target and target.status == AccountStatus.ACTIVE:
        target.status = AccountStatus.SUSPENDED
        target.suspended_at = _now()
        target.suspended_by_id = admin.id
        notification_service.notify_account_suspended(db, target.id)
    _resolve_user_report(db, report, admin, AdminReportAction.SUSPEND_USER)
    db.commit()
    db.refresh(report)
    return report


def admin_suppress_reporter(db: Session, user_id: uuid.UUID, admin: User) -> User:
    """Section 13.3 — mark reporter as bad-faith (suppress future report priority)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    user.reports_suppressed = True
    db.commit()
    db.refresh(user)
    return user


def _get_post_report(db: Session, report_id: uuid.UUID) -> PostReport:
    report = (
        db.query(PostReport)
        .options(joinedload(PostReport.reporter), joinedload(PostReport.item))
        .filter(PostReport.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report


def _get_user_report(db: Session, report_id: uuid.UUID) -> UserReport:
    report = (
        db.query(UserReport)
        .options(
            joinedload(UserReport.reporter),
            joinedload(UserReport.reported_user),
        )
        .filter(UserReport.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return report


def list_admin_report_queue(
    db: Session,
    *,
    status_filter: Optional[ReportStatus] = ReportStatus.PENDING,
    limit: int = 100,
) -> list[dict]:
    """Unified admin queue — escalated first, suspended reporters deprioritized."""
    items: list[dict] = []

    post_q = (
        db.query(PostReport)
        .options(
            joinedload(PostReport.reporter),
            joinedload(PostReport.item),
        )
        .order_by(PostReport.created_at.desc())
    )
    if status_filter:
        post_q = post_q.filter(PostReport.status == status_filter)
    for r in post_q.limit(limit).all():
        items.append(_serialize_post_report(r))

    user_q = (
        db.query(UserReport)
        .options(
            joinedload(UserReport.reporter),
            joinedload(UserReport.reported_user),
        )
        .order_by(UserReport.created_at.desc())
    )
    if status_filter:
        user_q = user_q.filter(UserReport.status == status_filter)
    for r in user_q.limit(limit).all():
        items.append(_serialize_user_report(r))

    def sort_key(row: dict) -> tuple:
        deprioritized = 1 if row["deprioritized"] else 0
        escalated = 0 if row["auto_escalated"] else 1
        return (escalated, deprioritized, row["created_at"].timestamp() * -1)

    items.sort(key=sort_key)
    return items[:limit]


def _serialize_post_report(r: PostReport) -> dict:
    reporter = r.reporter
    item = r.item
    return {
        "id": r.id,
        "report_type": "post",
        "status": r.status.value,
        "reason": r.reason.value,
        "detail_text": r.detail_text,
        "auto_escalated": r.auto_escalated,
        "deprioritized": _reporter_deprioritized(reporter),
        "created_at": r.created_at,
        "reporter": {
            "user_id": reporter.id,
            "display_name": reporter.full_name,
            "trust_tier": get_trust_tier(reporter.trust_score),
            "status": reporter.status.value,
            "reports_suppressed": reporter.reports_suppressed,
        },
        "target_item_id": r.item_id,
        "target_item_description": item.public_description[:200] if item else None,
        "target_user_id": item.posted_by_id if item else None,
        "target_user_display_name": None,
        "context_conversation_id": None,
    }


def _serialize_user_report(r: UserReport) -> dict:
    reporter = r.reporter
    target = r.reported_user
    return {
        "id": r.id,
        "report_type": "user",
        "status": r.status.value,
        "reason": r.reason.value,
        "detail_text": r.detail_text,
        "auto_escalated": r.auto_escalated,
        "deprioritized": _reporter_deprioritized(reporter),
        "created_at": r.created_at,
        "reporter": {
            "user_id": reporter.id,
            "display_name": reporter.full_name,
            "trust_tier": get_trust_tier(reporter.trust_score),
            "status": reporter.status.value,
            "reports_suppressed": reporter.reports_suppressed,
        },
        "target_item_id": None,
        "target_item_description": None,
        "target_user_id": r.reported_user_id,
        "target_user_display_name": target.full_name if target else None,
        "context_conversation_id": r.context_conversation_id,
    }

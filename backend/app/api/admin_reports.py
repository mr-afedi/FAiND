"""
Admin report queue API (Section 13.4).

Full admin dashboard UI is Feature R; these endpoints power the queue now.
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin_access
from app.models.report import ReportStatus
from app.models.user import User
from app.schemas.report import AdminReportActionResponse, AdminReportsResponse, ReportQueueItem
from app.services import report_service

router = APIRouter(prefix="/admin/reports", tags=["admin-reports"])


@router.get("", response_model=AdminReportsResponse)
def list_reports(
    status: Optional[str] = Query("pending", description="pending, dismissed, resolved, or all"),
    limit: int = Query(100, ge=1, le=200),
    _admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    status_filter = None if status == "all" else ReportStatus(status)
    rows = report_service.list_admin_report_queue(
        db, status_filter=status_filter, limit=limit
    )
    return AdminReportsResponse(
        reports=[ReportQueueItem.model_validate(r) for r in rows]
    )


@router.post("/posts/{report_id}/dismiss", response_model=AdminReportActionResponse)
def dismiss_post_report(
    report_id: uuid.UUID,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    report = report_service.admin_dismiss_post_report(db, report_id, admin)
    return AdminReportActionResponse(
        report_id=report.id,
        status=report.status.value,
        admin_action=report.admin_action.value,
        message="Post report dismissed.",
    )


@router.post("/posts/{report_id}/remove-post", response_model=AdminReportActionResponse)
def remove_reported_post(
    report_id: uuid.UUID,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    report = report_service.admin_remove_post(db, report_id, admin)
    return AdminReportActionResponse(
        report_id=report.id,
        status=report.status.value,
        admin_action=report.admin_action.value,
        message="Post removed and report resolved.",
    )


@router.post("/users/{report_id}/dismiss", response_model=AdminReportActionResponse)
def dismiss_user_report(
    report_id: uuid.UUID,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    report = report_service.admin_dismiss_user_report(db, report_id, admin)
    return AdminReportActionResponse(
        report_id=report.id,
        status=report.status.value,
        admin_action=report.admin_action.value,
        message="User report dismissed.",
    )


@router.post("/users/{report_id}/warn", response_model=AdminReportActionResponse)
def warn_reported_user(
    report_id: uuid.UUID,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    report = report_service.admin_warn_user(db, report_id, admin)
    return AdminReportActionResponse(
        report_id=report.id,
        status=report.status.value,
        admin_action=report.admin_action.value,
        message="User warned and report resolved.",
    )


@router.post("/users/{report_id}/suspend", response_model=AdminReportActionResponse)
def suspend_reported_user(
    report_id: uuid.UUID,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    report = report_service.admin_suspend_user(db, report_id, admin)
    return AdminReportActionResponse(
        report_id=report.id,
        status=report.status.value,
        admin_action=report.admin_action.value,
        message="User suspended and report resolved.",
    )


@router.post("/reporters/{user_id}/suppress", response_model=dict)
def suppress_reporter(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    user = report_service.admin_suppress_reporter(db, user_id, admin)
    return {
        "user_id": str(user.id),
        "reports_suppressed": user.reports_suppressed,
        "message": "Future reports from this user will be deprioritized.",
    }

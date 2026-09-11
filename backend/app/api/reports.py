"""User-facing report endpoints (Section 13)."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.report import (
    ReportSubmittedResponse,
    SubmitPostReportRequest,
    SubmitUserReportRequest,
)
from app.services import report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/items/{item_id}", response_model=ReportSubmittedResponse)
def report_item(
    item_id: uuid.UUID,
    payload: SubmitPostReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = report_service.submit_post_report(
        db, item_id=item_id, reporter=current_user, payload=payload
    )
    return ReportSubmittedResponse(
        id=report.id,
        message="Thank you. Your report has been submitted for review.",
        auto_escalated=report.auto_escalated,
    )


@router.post("/users/{user_id}", response_model=ReportSubmittedResponse)
def report_user(
    user_id: uuid.UUID,
    payload: SubmitUserReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    report = report_service.submit_user_report(
        db, reported_user_id=user_id, reporter=current_user, payload=payload
    )
    return ReportSubmittedResponse(
        id=report.id,
        message="Thank you. Your report has been submitted for review.",
        auto_escalated=report.auto_escalated,
    )

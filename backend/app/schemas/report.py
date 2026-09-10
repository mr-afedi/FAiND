"""Report schemas (Section 13)."""
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator, model_validator

from app.models.report import PostReportReason, UserReportReason


def _normalize_detail(v: Optional[str]) -> Optional[str]:
    if v is None:
        return None
    v = v.strip()
    if len(v) > 200:
        raise ValueError("Details must be 200 characters or fewer.")
    return v or None


class SubmitPostReportRequest(BaseModel):
    reason: PostReportReason
    detail_text: Optional[str] = None

    @field_validator("detail_text")
    @classmethod
    def strip_detail(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_detail(v)

    @model_validator(mode="after")
    def require_other_detail(self):
        if self.reason == PostReportReason.OTHER and not self.detail_text:
            raise ValueError("Please provide details when selecting Other.")
        return self


class SubmitUserReportRequest(BaseModel):
    reason: UserReportReason
    detail_text: Optional[str] = None

    @field_validator("detail_text")
    @classmethod
    def strip_detail(cls, v: Optional[str]) -> Optional[str]:
        return _normalize_detail(v)

    @model_validator(mode="after")
    def require_other_detail(self):
        if self.reason == UserReportReason.OTHER and not self.detail_text:
            raise ValueError("Please provide details when selecting Other.")
        return self


class ReportSubmittedResponse(BaseModel):
    id: uuid.UUID
    message: str
    auto_escalated: bool


class ReportQueueReporter(BaseModel):
    user_id: uuid.UUID
    display_name: str
    status: str
    reports_suppressed: bool


class ReportQueueItem(BaseModel):
    id: uuid.UUID
    report_type: Literal["post", "user"]
    status: str
    reason: str
    detail_text: Optional[str] = None
    auto_escalated: bool
    deprioritized: bool
    created_at: datetime
    reporter: ReportQueueReporter
    target_item_id: Optional[uuid.UUID] = None
    target_item_description: Optional[str] = None
    target_user_id: Optional[uuid.UUID] = None
    target_user_display_name: Optional[str] = None


class AdminReportsResponse(BaseModel):
    reports: list[ReportQueueItem]


class AdminReportActionResponse(BaseModel):
    report_id: uuid.UUID
    status: str
    admin_action: str
    message: str

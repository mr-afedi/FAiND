"""Admin dashboard schemas (Section 26)."""
import uuid
from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class AdminGateResponse(BaseModel):
    ok: bool = True
    role: str
    is_root: bool


class PlatformAnalytics(BaseModel):
    total_lost_items: int
    total_found_items: int
    total_returned: int
    return_rate_percent: float
    claims_pending_review: int
    disputes_open: int
    reports_pending: int
    fraud_alerts: int
    active_users_7d: int
    active_users_30d: int
    trust_distribution: dict[str, int]
    lost_items_this_week: int = 0
    found_items_this_week: int = 0
    returned_this_week: int = 0
    avg_days_post_to_return: Optional[float] = None
    claims_path_a: int = 0
    claims_path_b: int = 0
    claims_path_c: int = 0
    disputes_opened_total: int = 0
    disputes_resolved_total: int = 0
    active_users_daily: int = 0
    active_users_weekly: int = 0
    active_users_monthly: int = 0
    fraud_events_this_week: int = 0


class AdminUserListItem(BaseModel):
    id: uuid.UUID
    email: str
    username: str
    full_name: str
    role: str
    status: str
    trust_score: int
    fraud_risk_score: int
    created_at: datetime
    suspended_at: Optional[datetime] = None


class AdminUsersResponse(BaseModel):
    users: list[AdminUserListItem]
    total: int


class ClaimQueueItem(BaseModel):
    match_id: uuid.UUID
    path: str
    ownership_score: float
    match_score: float
    status: str
    created_at: datetime
    claimant_id: Optional[uuid.UUID] = None
    claimant_name: str
    claimant_trust_tier: str = ""
    lost_item_id: uuid.UUID
    found_item_id: uuid.UUID
    lost_description: str
    found_description: str
    item_label: str = ""
    university_id: Optional[uuid.UUID] = None
    score_breakdown: dict[str, Any] = Field(default_factory=dict)


class ClaimsQueueResponse(BaseModel):
    claims: list[ClaimQueueItem]
    total: int = 0


class DisputeQueueItem(BaseModel):
    dispute_id: uuid.UUID
    dispute_type: str
    return_id: Optional[uuid.UUID] = None
    match_id: Optional[uuid.UUID] = None
    returned_at: Optional[datetime] = None
    dispute_filed_at: Optional[datetime] = None
    dispute_reason: str
    filed_by_id: Optional[uuid.UUID] = None
    filed_by_name: str
    lost_owner_name: str
    found_owner_name: str
    tip_frozen: bool
    item_label: str


class DisputesQueueResponse(BaseModel):
    disputes: list[DisputeQueueItem]


class PostModerationItem(BaseModel):
    item_id: uuid.UUID
    item_type: str
    category: str
    status: str
    public_description: str
    posted_by_name: str
    posted_by_id: uuid.UUID
    admin_locked: bool
    pending_reports: int
    disputes_count: int = 0
    flagged: bool = False
    created_at: datetime


class PostsModerationResponse(BaseModel):
    posts: list[PostModerationItem]
    total: int = 0


class AdminLogItem(BaseModel):
    id: uuid.UUID
    admin_id: Optional[uuid.UUID] = None
    admin_email: Optional[str] = None
    action: str
    target_type: str
    target_id: Optional[uuid.UUID] = None
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AdminLogsResponse(BaseModel):
    logs: list[AdminLogItem]


class AdminActionResult(BaseModel):
    success: bool = True
    message: str


class PromoteAdminRequest(BaseModel):
    user_id: uuid.UUID


class SuspendUserRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class ResolveDisputeRequest(BaseModel):
    outcome: Literal["approved", "rejected", "more_info", "flagged"]
    note: str = Field(..., min_length=10, max_length=2000)


class ResolveVerificationDisputeRequest(BaseModel):
    winner_match_id: uuid.UUID
    note: str = Field(..., min_length=10, max_length=2000)


class RejectClaimRequest(BaseModel):
    note: Optional[str] = Field(None, max_length=500)


class ForceClosePostRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=500)


class RequestMoreInfoRequest(BaseModel):
    note: str = Field(..., min_length=10, max_length=2000)


class TrustAdjustRequest(BaseModel):
    delta: int = Field(..., ge=-100, le=100)
    reason: str = Field(..., min_length=10, max_length=500)


class LockDisputeItemRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)


class EscalateDisputeRequest(BaseModel):
    note: str = Field(..., min_length=10, max_length=2000)


class AdminSearchUserHit(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: str


class AdminSearchItemHit(BaseModel):
    id: uuid.UUID
    item_type: str
    public_description: str
    status: str


class AdminSearchClaimHit(BaseModel):
    match_id: uuid.UUID
    path: str
    claimant_name: str
    match_score: float
    status: str


class AdminSearchResponse(BaseModel):
    query: str
    users: list[AdminSearchUserHit] = Field(default_factory=list)
    items: list[AdminSearchItemHit] = Field(default_factory=list)
    claims: list[AdminSearchClaimHit] = Field(default_factory=list)


class ReturnedItemListItem(BaseModel):
    return_id: uuid.UUID
    item_description: str
    category: str
    owner_name: str
    owner_username: str
    finder_name: str
    finder_username: str
    date_lost: datetime
    date_found: datetime
    date_returned: datetime
    tipped: bool
    university_id: uuid.UUID


class ReturnedItemsResponse(BaseModel):
    items: list[ReturnedItemListItem]
    total: int


class OpenReturnDisputeRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=2000)


class AdminDetailResponse(BaseModel):
    detail: dict[str, Any]

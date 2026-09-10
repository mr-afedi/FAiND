import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.authority import AUTHORITY_EMAIL_DOMAIN, AuthorityListItem


class SupervisorLoginRequest(BaseModel):
    email: EmailStr
    password: str


class SupervisorTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SupervisorDropPointSummary(BaseModel):
    id: uuid.UUID
    name: str
    type: str
    operating_hours: str
    is_temporarily_closed: bool


class SupervisorProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    university_id: uuid.UUID
    is_active: bool
    created_at: datetime
    drop_points: list[SupervisorDropPointSummary]


class SupervisorDashboardItem(BaseModel):
    id: uuid.UUID
    drop_point_id: uuid.UUID
    drop_point_name: str
    status: str
    category: str
    public_description: str
    location_label: str
    created_at: datetime
    tracking_reference: Optional[str] = None


class SupervisorItemsResponse(BaseModel):
    items: list[SupervisorDashboardItem]


class SupervisorClaimItemSummary(BaseModel):
    found_item_id: uuid.UUID
    drop_point_id: uuid.UUID
    drop_point_name: str
    found_item_status: str
    found_item_category: str
    found_item_description: str
    claim_count: int
    pending_count: int
    has_dispute: bool = False


class SupervisorClaimsListResponse(BaseModel):
    items: list[SupervisorClaimItemSummary]


class SupervisorOverviewStats(BaseModel):
    total_incoming: int
    at_drop_point: int
    active_claims: int
    completed_handovers: int


class SupervisorOverviewResponse(BaseModel):
    stats: SupervisorOverviewStats


class SupervisorScopedDashboardItem(BaseModel):
    id: uuid.UUID
    drop_point_id: uuid.UUID
    drop_point_name: str
    status: str
    category: str
    public_description: str
    location_label: str
    image_urls: list[str]
    date_occurred: Optional[datetime] = None
    created_at: datetime
    tracking_reference: Optional[str] = None
    dropoff_hours_remaining: int
    dropoff_hours_until_unconfirmed: int
    dropoff_late: bool
    dropoff_phase: str
    finder_dropped_off_at: Optional[datetime] = None
    authority_received_at: Optional[datetime] = None
    dropoff_confirmed_at: Optional[datetime] = None
    can_authority_confirm: bool


class SupervisorScopedDashboardListResponse(BaseModel):
    items: list[SupervisorScopedDashboardItem]


class SupervisorEscalateDisputeRequest(BaseModel):
    note: str = Field(min_length=10, max_length=2000)


class SupervisorAlertsActionResponse(BaseModel):
    message: str


class CreateSupervisorRequest(BaseModel):
    email: EmailStr
    password: str
    university_id: uuid.UUID
    drop_point_ids: list[uuid.UUID] = Field(default_factory=list)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UpdateSupervisorRequest(BaseModel):
    drop_point_ids: Optional[list[uuid.UUID]] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class SupervisorListItem(BaseModel):
    id: uuid.UUID
    email: str
    university_id: uuid.UUID
    is_active: bool
    created_at: datetime
    drop_point_ids: list[uuid.UUID]
    drop_point_names: list[str]


class SupervisorListResponse(BaseModel):
    supervisors: list[SupervisorListItem]


class ResetAuthorityPasswordRequest(BaseModel):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class SupervisorAuthoritiesResponse(BaseModel):
    authorities: list[AuthorityListItem]


class SupervisorAlertResponse(BaseModel):
    id: uuid.UUID
    alert_type: str
    title: str
    body: str
    link: Optional[str] = None
    read: bool
    created_at: datetime
    deletable: bool


class SupervisorAlertsListResponse(BaseModel):
    alerts: list[SupervisorAlertResponse]
    unread_count: int

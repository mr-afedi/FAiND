import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


AUTHORITY_EMAIL_DOMAIN = "@gctu.edu.gh"


class AuthorityLoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_institutional_email(cls, v: str) -> str:
        email = v.strip().lower()
        if not email.endswith(AUTHORITY_EMAIL_DOMAIN):
            raise ValueError(f"Authority email must be a {AUTHORITY_EMAIL_DOMAIN} address")
        return email


class AuthorityOtpStepResponse(BaseModel):
    session_token: str
    message: str = "A 6-digit code has been sent to your email."


class AuthorityVerifyOtpRequest(BaseModel):
    session_token: str
    code: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip()
        if len(v) != 6 or not v.isdigit():
            raise ValueError("Code must be a 6-digit number")
        return v


class AuthorityTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthorityProfileResponse(BaseModel):
    id: uuid.UUID
    email: str
    university_id: uuid.UUID
    drop_point_id: uuid.UUID
    drop_point_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateAuthorityRequest(BaseModel):
    email: EmailStr
    password: str
    drop_point_id: uuid.UUID

    @field_validator("email")
    @classmethod
    def validate_institutional_email(cls, v: str) -> str:
        email = v.strip().lower()
        if not email.endswith(AUTHORITY_EMAIL_DOMAIN):
            raise ValueError(f"Authority email must be a {AUTHORITY_EMAIL_DOMAIN} address")
        return email

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class AuthorityListItem(BaseModel):
    id: uuid.UUID
    email: str
    university_id: uuid.UUID
    drop_point_id: uuid.UUID
    drop_point_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AuthorityListResponse(BaseModel):
    authorities: list[AuthorityListItem]


class ReassignAuthorityRequest(BaseModel):
    drop_point_id: uuid.UUID


class AuthorityScopedItemResponse(BaseModel):
    id: uuid.UUID
    status: str
    category: str
    public_description: str
    drop_point_id: uuid.UUID


class AuthorityDashboardItem(BaseModel):
    id: uuid.UUID
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


class AuthorityDashboardListResponse(BaseModel):
    items: list[AuthorityDashboardItem]


class AuthorityDropOffActionResponse(BaseModel):
    message: str
    item: AuthorityDashboardItem


class AuthorityScanQrRequest(BaseModel):
    token: str

    @field_validator("token")
    @classmethod
    def token_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("QR token is required")
        return v


class AuthorityDropPointSettingsResponse(BaseModel):
    drop_point_id: uuid.UUID
    drop_point_name: str
    operating_hours: str
    is_temporarily_closed: bool
    closed_reason: Optional[str] = None


class AuthorityDropPointSettingsUpdate(BaseModel):
    operating_hours: Optional[str] = None
    is_temporarily_closed: Optional[bool] = None
    closed_reason: Optional[str] = None


from app.schemas.messaging import InquirySummary


class AuthorityClaimDetail(BaseModel):
    id: uuid.UUID
    claim_path: str
    status: str
    photo_url: Optional[str] = None
    date_lost: Optional[date] = None
    time_lost: Optional[str] = None
    description: str
    lost_location: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    created_at: datetime
    claimant_name: str
    claimant_email: str
    student_id: Optional[str] = None
    inquiry: Optional[InquirySummary] = None


class AuthorityClaimsComparisonResponse(BaseModel):
    found_item_id: uuid.UUID
    found_item_status: str
    found_item_category: str
    found_item_description: str
    found_item_image_urls: list[str]
    drop_point_operating_hours: Optional[str] = None
    claims: list[AuthorityClaimDetail]


class AuthorityClaimItemSummary(BaseModel):
    found_item_id: uuid.UUID
    found_item_status: str
    found_item_category: str
    found_item_description: str
    claim_count: int
    pending_count: int


class AuthorityClaimsListResponse(BaseModel):
    items: list[AuthorityClaimItemSummary]


class AuthorityClaimActionResponse(BaseModel):
    message: str
    comparison: AuthorityClaimsComparisonResponse


class AuthorityAlertResponse(BaseModel):
    id: uuid.UUID
    alert_type: str
    title: str
    body: str
    link: str | None
    reference_id: uuid.UUID | None
    read: bool
    deletable: bool
    created_at: str

    model_config = {"from_attributes": True}


class AuthorityAlertsListResponse(BaseModel):
    alerts: list[AuthorityAlertResponse]
    unread_count: int


class AuthorityAlertsActionResponse(BaseModel):
    message: str
    deleted_count: int | None = None

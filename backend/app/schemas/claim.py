import re
import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class ClaimFormSubmit(BaseModel):
    photo_url: Optional[str] = None
    date_lost: Optional[date] = None
    time_lost: Optional[str] = None
    description: str
    lost_location: Optional[str] = None

    @field_validator("time_lost")
    @classmethod
    def validate_time_lost(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if not _TIME_RE.match(v):
            raise ValueError("Time must be in HH:MM (24-hour) format")
        return v

    @field_validator("description")
    @classmethod
    def description_not_empty(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Description must be at least 10 characters")
        return v

    @field_validator("photo_url")
    @classmethod
    def photo_url_optional(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


class ClaimSubmitResponse(BaseModel):
    claim_id: uuid.UUID
    message: str
    collection_phase: Literal["not_at_drop_point", "ready_for_collection"]
    drop_point_name: Optional[str] = None
    operating_hours: Optional[str] = None
    claim_status: str
    created_at: datetime


class ViewerClaimSummary(BaseModel):
    """Authenticated viewer's claim on a found item — drives UI claim state."""

    claim_id: uuid.UUID
    claim_status: Literal["pending", "verified", "rejected"]
    claim_path: Literal["A", "C"]
    viewer_state: Literal["pending_review", "called_to_collect", "verified", "rejected"]
    message: str
    drop_point_name: Optional[str] = None
    operating_hours: Optional[str] = None


class MyClaimCard(BaseModel):
    claim_id: uuid.UUID
    found_item_id: uuid.UUID
    thumbnail_url: Optional[str] = None
    category: str
    description_preview: str
    status_label: str
    viewer_state: Literal["pending_review", "called_to_collect", "rejected"]
    drop_point_name: str
    operating_hours: Optional[str] = None


class MyClaimsListResponse(BaseModel):
    claims: list[MyClaimCard]


class AwaitingConfirmationCard(BaseModel):
    claim_id: uuid.UUID
    handover_id: Optional[uuid.UUID] = None
    found_item_id: uuid.UUID
    thumbnail_url: Optional[str] = None
    category: str
    description_preview: str
    status_label: str = "You have been verified as the owner"
    drop_point_name: str
    drop_point_address: Optional[str] = None
    operating_hours: Optional[str] = None
    can_confirm: bool = False


class AwaitingConfirmationListResponse(BaseModel):
    items: list[AwaitingConfirmationCard]

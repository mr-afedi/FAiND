import uuid
from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, field_validator


class HandoverStartRequest(BaseModel):
    condition_photo_url: str
    claimant_name: str
    claimant_phone: str
    claimant_student_id: str
    claimant_photo_url: str

    @field_validator(
        "condition_photo_url",
        "claimant_name",
        "claimant_phone",
        "claimant_student_id",
        "claimant_photo_url",
    )
    @classmethod
    def required_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required")
        return v


class HandoverOverrideRequest(BaseModel):
    note: str

    @field_validator("note")
    @classmethod
    def note_not_blank(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Override note must be at least 10 characters")
        return v


class HandoverOwnerResponse(BaseModel):
    id: uuid.UUID
    item_id: uuid.UUID
    condition_photo_url: str
    claimant_name: str
    owner_confirmed: bool
    owner_confirmed_at: Optional[datetime] = None
    authority_override: bool
    found_item_description: str
    found_item_category: str
    can_confirm: bool


class HandoverConfirmResponse(BaseModel):
    message: str
    handover_id: uuid.UUID
    item_status: str


class HandoverAuthorityDetail(BaseModel):
    id: uuid.UUID
    claim_id: uuid.UUID
    item_id: uuid.UUID
    condition_photo_url: str
    claimant_name: str
    claimant_phone: str
    claimant_student_id: Optional[str] = None
    claimant_photo_url: Optional[str] = None
    owner_confirmed: bool
    owner_confirmed_at: Optional[datetime] = None
    authority_override_note: Optional[str] = None
    authority_override: bool
    handover_status: Literal["awaiting_owner", "completed"]
    found_item_description: str
    found_item_category: str
    created_at: datetime
    # Extended fields for completed handover detail panel
    found_item_image_urls: list[str] = []
    found_item_location_label: Optional[str] = None
    found_item_date_occurred: Optional[date] = None
    finder_display_name: Optional[str] = None
    finder_username: Optional[str] = None
    owner_display_name: Optional[str] = None
    claim_path: Optional[str] = None
    ai_confidence_score: Optional[float] = None
    completed_at: Optional[datetime] = None
    drop_point_name: Optional[str] = None


class HandoverQueueItem(BaseModel):
    claim_id: uuid.UUID
    handover_id: Optional[uuid.UUID] = None
    found_item_id: uuid.UUID
    found_item_description: str
    found_item_category: str
    claimant_name: str
    queue_status: Literal["ready_to_start", "awaiting_owner", "completed"]
    owner_confirmed: bool = False
    authority_override: bool = False
    condition_photo_url: Optional[str] = None
    created_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    drop_point_id: Optional[uuid.UUID] = None
    drop_point_name: Optional[str] = None


class HandoverQueueResponse(BaseModel):
    items: list[HandoverQueueItem]


class HandoverStartResponse(BaseModel):
    message: str
    handover: HandoverAuthorityDetail

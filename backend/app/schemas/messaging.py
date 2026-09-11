import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


InquiryMessageTypeValue = Literal["still_available", "on_my_way", "collect_tomorrow"]
ReplyMessageTypeValue = Literal[
    "yes_here", "come_during_hours", "already_collected", "no_response_needed"
]


class SendInquiryRequest(BaseModel):
    message_type: InquiryMessageTypeValue


class InquiryReplySummary(BaseModel):
    reply_type: str
    reply_label: str
    created_at: datetime


class InquirySummary(BaseModel):
    id: uuid.UUID
    message_type: str
    message_label: str
    created_at: datetime
    reply: Optional[InquiryReplySummary] = None


class SendInquiryResponse(BaseModel):
    inquiry: InquirySummary
    message: str


class OwnerClaimStatusResponse(BaseModel):
    claim_id: uuid.UUID
    claim_status: str
    claim_path: str
    collection_phase: Literal["not_at_drop_point", "ready_for_collection"]
    found_item_id: uuid.UUID
    found_item_status: str
    found_item_description: str
    drop_point_name: Optional[str] = None
    operating_hours: Optional[str] = None
    can_send_inquiry: bool
    inquiry: Optional[InquirySummary] = None


class ReplyToInquiryRequest(BaseModel):
    reply_type: ReplyMessageTypeValue = Field(..., description="Authority quick reply type")

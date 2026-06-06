"""Pydantic schemas — Return confirmation (Feature M)."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.item import ItemCategory
from app.models.item_return import ReturnMethod


class ReturnPartySummary(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    trust_tier: str


class ReturnItemSummary(BaseModel):
    id: uuid.UUID
    item_type: str
    category: ItemCategory
    public_description: str
    location_label: str
    date_occurred: datetime
    image_urls: list[str]


class ReturnStatusResponse(BaseModel):
    return_id: uuid.UUID
    match_id: uuid.UUID
    conversation_id: Optional[uuid.UUID] = None
    lost_item: ReturnItemSummary
    found_item: ReturnItemSummary
    lost_owner: ReturnPartySummary
    found_owner: ReturnPartySummary
    viewer_role: str  # lost_owner | found_owner
    finder_handed_over: bool
    owner_received: bool
    is_complete: bool
    returned_at: Optional[datetime] = None
    method: Optional[ReturnMethod] = None
    qr_active: bool = False
    qr_expires_at: Optional[datetime] = None
    tipping_window_ends_at: Optional[datetime] = None
    dispute_window_ends_at: Optional[datetime] = None
    can_confirm_finder: bool = False
    can_confirm_owner: bool = False
    can_generate_qr: bool = False
    awaiting_owner_receipt: bool = False
    awaiting_finder_handover: bool = False


class ReturnActionResponse(BaseModel):
    status: ReturnStatusResponse
    message: str
    completed: bool = False


class QrGenerateResponse(BaseModel):
    token: str
    expires_at: datetime
    qr_payload: str
    status: ReturnStatusResponse


class QrRedeemRequest(BaseModel):
    token: str = Field(..., min_length=16, max_length=128)


class DisputeReturnRequest(BaseModel):
    reason: str = Field(..., min_length=10, max_length=2000)


class ReturnedListItem(BaseModel):
    return_id: uuid.UUID
    match_id: uuid.UUID
    item_label: str
    category: ItemCategory
    returned_at: datetime
    other_user_display_name: str
    other_user_trust_tier: str
    viewer_role: str
    is_owner: bool
    appreciation_sent: bool = False
    appreciation_received: bool = False
    dispute_active: bool = False


class ReturnedListResponse(BaseModel):
    items: list[ReturnedListItem]


class ReturnedDetailResponse(BaseModel):
    return_id: uuid.UUID
    match_id: uuid.UUID
    conversation_id: Optional[uuid.UUID] = None
    returned_at: datetime
    method: ReturnMethod
    item_label: str
    category: ItemCategory
    lost_item: ReturnItemSummary
    found_item: ReturnItemSummary
    other_user: ReturnPartySummary
    viewer_role: str
    dates_summary: dict
    tipping_window_ends_at: Optional[datetime] = None
    dispute_window_ends_at: Optional[datetime] = None
    tipping_window_open: bool = False
    dispute_window_open: bool = False
    dispute_active: bool = False
    appreciation_sent: bool = False
    appreciation_skipped_until: Optional[datetime] = None
    tip_frozen: bool = False
    tipping_days_left: int = 0
    dispute_days_left: int = 0
    can_send_appreciation: bool = False
    can_skip_appreciation: bool = False
    can_dispute: bool = False
    chat_read_only: bool = True
    paystack_ready: bool = False
    summary_note: Optional[str] = None
    appreciation_message: Optional[str] = None
    dispute_reason: Optional[str] = None

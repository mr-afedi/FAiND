"""Pydantic schemas — Messages inbox + chat (Feature L)."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.conversation import ConversationStatus


class ChatUserSummary(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str
    profile_photo_url: Optional[str] = None
    trust_tier: str

    model_config = {"from_attributes": True}


class ChatItemSummary(BaseModel):
    lost_item_id: uuid.UUID
    found_item_id: uuid.UUID
    category: str
    item_label: str

    model_config = {"from_attributes": True}


class ConversationListItem(BaseModel):
    id: uuid.UUID
    status: ConversationStatus
    other_user: ChatUserSummary
    item: ChatItemSummary
    last_message_preview: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0
    can_send: bool = True
    is_frozen: bool = False


class ConversationListResponse(BaseModel):
    conversations: list[ConversationListItem]
    total_unread: int


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    status: ConversationStatus
    other_user: ChatUserSummary
    item: ChatItemSummary
    can_send: bool
    is_frozen: bool
    frozen_message: Optional[str] = None


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    created_at: datetime
    read_at: Optional[datetime] = None
    is_mine: bool = False
    is_seen: bool = False

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    has_more: bool = False


class SendMessageRequest(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class UnreadCountResponse(BaseModel):
    total_unread: int

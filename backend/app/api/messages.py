"""
Messages inbox + chat REST API (Feature L).
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_for_chat
from app.models.user import User
from app.schemas.message import (
    ConversationDetailResponse,
    ConversationListResponse,
    MessageListResponse,
    MessageResponse,
    SendMessageRequest,
    UnreadCountResponse,
)
from app.services import chat_service

router = APIRouter(prefix="/messages", tags=["messages"])


@router.get("/conversations", response_model=ConversationListResponse)
def list_conversations(
    current_user: User = Depends(get_current_user_for_chat),
    db: Session = Depends(get_db),
):
    return chat_service.list_conversations(db, current_user)


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(
    current_user: User = Depends(get_current_user_for_chat),
    db: Session = Depends(get_db),
):
    return UnreadCountResponse(total_unread=chat_service.get_total_unread(db, current_user))


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user_for_chat),
    db: Session = Depends(get_db),
):
    return chat_service.get_conversation_detail(db, conversation_id, current_user)


@router.get("/conversations/{conversation_id}/messages", response_model=MessageListResponse)
def list_messages(
    conversation_id: uuid.UUID,
    before_id: uuid.UUID | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user_for_chat),
    db: Session = Depends(get_db),
):
    return chat_service.list_messages(
        db, conversation_id, current_user, before_id=before_id, limit=limit
    )


@router.post("/conversations/{conversation_id}/read", status_code=204)
async def mark_read(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user_for_chat),
    db: Session = Depends(get_db),
):
    await chat_service.mark_read_and_notify(db, conversation_id, current_user)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
)
async def send_message(
    conversation_id: uuid.UUID,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user_for_chat),
    db: Session = Depends(get_db),
):
    msg = chat_service.send_message(db, conversation_id, current_user, payload)
    await chat_service.broadcast_message_event(conversation_id, msg, current_user.id)
    return msg

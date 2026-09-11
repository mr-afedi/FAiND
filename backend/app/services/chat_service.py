"""
Chat service — inbox, messages, read receipts (Section 14, Feature L).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.conversation import Conversation, ConversationStatus
from app.models.message import Message
from app.models.item import Item, ItemCategory
from app.models.user import User, AccountStatus
from app.schemas.message import (
    ChatItemSummary,
    ChatUserSummary,
    ConversationDetailResponse,
    ConversationListItem,
    ConversationListResponse,
    MessageListResponse,
    MessageResponse,
    SendMessageRequest,
)
from app.services import trust_service, returned_items_service
from app.services.ws_manager import chat_manager

_CATEGORY_LABELS: dict[ItemCategory, str] = {
    ItemCategory.ELECTRONICS: "Electronics",
    ItemCategory.BAG: "Bag",
    ItemCategory.ID_CARD: "ID/Card",
    ItemCategory.KEYS: "Keys",
    ItemCategory.CLOTHING: "Clothing",
    ItemCategory.BOOKS_NOTES: "Books/Notes",
    ItemCategory.WALLET: "Wallet",
    ItemCategory.JEWELLERY: "Jewellery",
    ItemCategory.OTHER: "Other",
}

_FROZEN_BANNER = (
    "This conversation is currently paused pending a platform review."
)
_RETURN_READONLY_BANNER = "This return is complete. Chat is read-only."


def _item_label(item: Item) -> str:
    cat = _CATEGORY_LABELS.get(item.category, "Item")
    desc = (item.public_description or "").strip()
    if len(desc) > 48:
        desc = desc[:45] + "..."
    return f"{cat}: {desc}" if desc else cat


def _user_summary(user: User) -> ChatUserSummary:
    return ChatUserSummary(
        id=user.id,
        username=user.username,
        display_name=user.full_name or user.username,
        profile_photo_url=user.profile_photo_url,
        trust_tier=trust_service.get_trust_tier(user.trust_score),
    )


def _other_user_id(conv: Conversation, viewer_id: uuid.UUID) -> uuid.UUID:
    if conv.lost_owner_id == viewer_id:
        return conv.found_owner_id
    return conv.lost_owner_id


def _get_conversation_for_user(
    db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation:
    conv = (
        db.query(Conversation)
        .options(
            joinedload(Conversation.potential_match),
        )
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")
    if user_id not in (conv.lost_owner_id, conv.found_owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if conv.status == ConversationStatus.LOCKED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chat is not unlocked for this conversation.",
        )
    return conv


def _chat_accessible_statuses() -> list[ConversationStatus]:
    return [
        ConversationStatus.UNLOCKED,
        ConversationStatus.FROZEN,
        ConversationStatus.PAUSED,
    ]


def _other_user(db: Session, conv: Conversation, viewer_id: uuid.UUID) -> User:
    other_id = _other_user_id(conv, viewer_id)
    other = db.query(User).filter(User.id == other_id).first()
    if not other:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return other


def _send_permissions(
    conv: Conversation,
    viewer: User,
    other: User,
    db: Session | None = None,
) -> tuple[bool, bool, str | None]:
    if db and returned_items_service.is_return_chat_readonly(db, conv.potential_match_id):
        return False, True, _RETURN_READONLY_BANNER

    is_frozen = (
        conv.status in (ConversationStatus.FROZEN, ConversationStatus.PAUSED)
        or viewer.status == AccountStatus.SUSPENDED
        or other.status == AccountStatus.SUSPENDED
    )
    can_send = (
        conv.status == ConversationStatus.UNLOCKED
        and viewer.status == AccountStatus.ACTIVE
        and other.status == AccountStatus.ACTIVE
        and not is_frozen
    )
    frozen_message = None
    if is_frozen:
        frozen_message = _FROZEN_BANNER
    elif not can_send:
        frozen_message = "You cannot send messages in this conversation."
    return can_send, is_frozen, frozen_message


def _message_to_response(msg: Message, viewer_id: uuid.UUID) -> MessageResponse:
    is_mine = msg.sender_id == viewer_id
    is_seen = bool(is_mine and msg.read_at is not None)
    return MessageResponse(
        id=msg.id,
        conversation_id=msg.conversation_id,
        sender_id=msg.sender_id,
        body=msg.body,
        created_at=msg.created_at,
        read_at=msg.read_at,
        is_mine=is_mine,
        is_seen=is_seen,
    )


def list_conversations(db: Session, user: User) -> ConversationListResponse:
    convs = (
        db.query(Conversation)
        .filter(
            Conversation.university_id == user.university_id,
            Conversation.status.in_(_chat_accessible_statuses()),
            (Conversation.lost_owner_id == user.id) | (Conversation.found_owner_id == user.id),
        )
        .order_by(Conversation.created_at.desc())
        .all()
    )
    if not convs:
        return ConversationListResponse(conversations=[], total_unread=0)

    conv_ids = [c.id for c in convs]
    item_ids = {c.lost_item_id for c in convs} | {c.found_item_id for c in convs}
    items = {
        i.id: i for i in db.query(Item).filter(Item.id.in_(item_ids)).all()
    }
    other_ids = {_other_user_id(c, user.id) for c in convs}
    others = {u.id: u for u in db.query(User).filter(User.id.in_(other_ids)).all()}

    last_msg_subq = (
        db.query(
            Message.conversation_id,
            func.max(Message.created_at).label("max_at"),
        )
        .filter(Message.conversation_id.in_(conv_ids))
        .group_by(Message.conversation_id)
        .subquery()
    )
    last_messages = {
        m.conversation_id: m
        for m in (
            db.query(Message)
            .join(
                last_msg_subq,
                (Message.conversation_id == last_msg_subq.c.conversation_id)
                & (Message.created_at == last_msg_subq.c.max_at),
            )
            .all()
        )
    }

    unread_rows = (
        db.query(Message.conversation_id, func.count(Message.id))
        .filter(
            Message.conversation_id.in_(conv_ids),
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .group_by(Message.conversation_id)
        .all()
    )
    unread_map = {row[0]: int(row[1]) for row in unread_rows}

    rows: list[ConversationListItem] = []
    total_unread = 0
    for conv in convs:
        other = others.get(_other_user_id(conv, user.id))
        if not other:
            continue
        lost = items.get(conv.lost_item_id)
        found = items.get(conv.found_item_id)
        if not lost or not found:
            continue
        can_send, is_frozen, _ = _send_permissions(conv, user, other, db)
        unread = unread_map.get(conv.id, 0)
        total_unread += unread
        last = last_messages.get(conv.id)
        preview = None
        last_at = None
        if last:
            preview = last.body[:80] + ("…" if len(last.body) > 80 else "")
            last_at = last.created_at
        rows.append(
            ConversationListItem(
                id=conv.id,
                status=conv.status,
                other_user=_user_summary(other),
                item=ChatItemSummary(
                    lost_item_id=conv.lost_item_id,
                    found_item_id=conv.found_item_id,
                    category=lost.category.value,
                    item_label=_item_label(lost),
                ),
                last_message_preview=preview,
                last_message_at=last_at,
                unread_count=unread,
                can_send=can_send,
                is_frozen=is_frozen,
            )
        )

    rows.sort(
        key=lambda r: (r.last_message_at or datetime.min.replace(tzinfo=timezone.utc)),
        reverse=True,
    )
    return ConversationListResponse(conversations=rows, total_unread=total_unread)


def get_conversation_detail(
    db: Session, conversation_id: uuid.UUID, user: User
) -> ConversationDetailResponse:
    conv = _get_conversation_for_user(db, conversation_id, user.id)
    other = _other_user(db, conv, user.id)
    lost = db.query(Item).filter(Item.id == conv.lost_item_id).first()
    found = db.query(Item).filter(Item.id == conv.found_item_id).first()
    if not lost or not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    can_send, is_frozen, frozen_message = _send_permissions(conv, user, other, db)
    return ConversationDetailResponse(
        id=conv.id,
        status=conv.status,
        other_user=_user_summary(other),
        item=ChatItemSummary(
            lost_item_id=conv.lost_item_id,
            found_item_id=conv.found_item_id,
            category=lost.category.value,
            item_label=_item_label(lost),
        ),
        can_send=can_send,
        is_frozen=is_frozen,
        frozen_message=frozen_message if is_frozen or not can_send else None,
    )


def list_messages(
    db: Session,
    conversation_id: uuid.UUID,
    user: User,
    *,
    before_id: uuid.UUID | None = None,
    limit: int = 50,
) -> MessageListResponse:
    conv = _get_conversation_for_user(db, conversation_id, user.id)
    _ = conv
    q = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc())
    )
    if before_id:
        pivot = db.query(Message).filter(Message.id == before_id).first()
        if pivot and pivot.conversation_id == conversation_id:
            q = q.filter(Message.created_at < pivot.created_at)
    rows = q.limit(limit + 1).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    rows.reverse()
    return MessageListResponse(
        messages=[_message_to_response(m, user.id) for m in rows],
        has_more=has_more,
    )


def mark_messages_read(
    db: Session, conversation_id: uuid.UUID, user: User
) -> list[uuid.UUID]:
    conv = _get_conversation_for_user(db, conversation_id, user.id)
    now = datetime.now(timezone.utc)
    unread = (
        db.query(Message)
        .filter(
            Message.conversation_id == conv.id,
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .all()
    )
    if not unread:
        return []
    ids = [m.id for m in unread]
    for m in unread:
        m.read_at = now
    db.commit()
    return ids


async def broadcast_message_event(
    conversation_id: uuid.UUID, message: MessageResponse, sender_id: uuid.UUID
) -> None:
    await chat_manager.broadcast(
        conversation_id,
        {"type": "new_message", "message": message.model_dump(mode="json")},
        exclude_user_id=sender_id,
    )


def send_message(
    db: Session,
    conversation_id: uuid.UUID,
    user: User,
    payload: SendMessageRequest,
) -> MessageResponse:
    conv = _get_conversation_for_user(db, conversation_id, user.id)
    other = _other_user(db, conv, user.id)
    can_send, is_frozen, frozen_message = _send_permissions(conv, user, other, db)
    if not can_send:
        detail = frozen_message or "You cannot send messages in this conversation."
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

    body = payload.body.strip()
    if not body:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message cannot be empty.",
        )

    msg = Message(
        conversation_id=conv.id,
        sender_id=user.id,
        body=body,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return _message_to_response(msg, user.id)


def get_total_unread(db: Session, user: User) -> int:
    return (
        db.query(func.count(Message.id))
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            Conversation.status.in_(_chat_accessible_statuses()),
            (Conversation.lost_owner_id == user.id) | (Conversation.found_owner_id == user.id),
            Message.sender_id != user.id,
            Message.read_at.is_(None),
        )
        .scalar()
        or 0
    )


async def mark_read_and_notify(
    db: Session, conversation_id: uuid.UUID, user: User
) -> None:
    message_ids = mark_messages_read(db, conversation_id, user)
    if not message_ids:
        return
    await chat_manager.broadcast(
        conversation_id,
        {
            "type": "messages_read",
            "conversation_id": str(conversation_id),
            "reader_id": str(user.id),
            "message_ids": [str(mid) for mid in message_ids],
            "read_at": datetime.now(timezone.utc).isoformat(),
        },
        exclude_user_id=user.id,
    )

"""
Return confirmation service — dual confirm + QR (Section 15, Feature M).
"""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemType, ItemStatus, ItemCategory
from app.models.user import User, AccountStatus
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.conversation import Conversation, ConversationStatus
from app.models.item_return import ItemReturn, ReturnMethod
from app.schemas.return_confirmation import (
    ReturnActionResponse,
    ReturnItemSummary,
    ReturnPartySummary,
    ReturnStatusResponse,
    ReturnedDetailResponse,
    ReturnedListItem,
    ReturnedListResponse,
    QrGenerateResponse,
)
from app.services import trust_service, notification_service, returned_items_service, tipping_service

RETURN_WINDOW_DAYS = 7
QR_VALID_HOURS = 24
OWNER_REMINDER_DAYS = 7
ADMIN_REVIEW_DAYS = 14

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


def _item_label(item: Item) -> str:
    cat = _CATEGORY_LABELS.get(item.category, "Item")
    desc = (item.public_description or "").strip()
    if len(desc) > 48:
        desc = desc[:45] + "..."
    return f"{cat}: {desc}" if desc else cat


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _item_summary(item: Item) -> ReturnItemSummary:
    return ReturnItemSummary(
        id=item.id,
        item_type=item.item_type.value,
        category=item.category,
        public_description=item.public_description,
        location_label=item.location_label,
        date_occurred=item.date_occurred,
        image_urls=item.image_urls or [],
    )


def _party(user: User) -> ReturnPartySummary:
    return ReturnPartySummary(
        id=user.id,
        username=user.username,
        display_name=user.full_name or user.username,
        trust_tier=trust_service.get_trust_tier(user.trust_score),
    )


def _get_verified_match(
    db: Session, match_id: uuid.UUID, user: User
) -> tuple[PotentialMatch, Conversation | None]:
    match = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(PotentialMatch.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    if match.university_id != user.university_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if user.id not in (match.lost_item.posted_by_id, match.found_item.posted_by_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if match.status != PotentialMatchStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Return confirmation is only available after ownership verification passes.",
        )
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.potential_match_id == match.id,
            Conversation.status == ConversationStatus.UNLOCKED,
        )
        .first()
    )
    return match, conv


def _get_or_create_return(db: Session, match: PotentialMatch) -> ItemReturn:
    existing = (
        db.query(ItemReturn)
        .filter(ItemReturn.potential_match_id == match.id)
        .first()
    )
    if existing:
        return existing
    record = ItemReturn(
        university_id=match.university_id,
        potential_match_id=match.id,
        lost_item_id=match.lost_item_id,
        found_item_id=match.found_item_id,
        lost_owner_id=match.lost_item.posted_by_id,
        found_owner_id=match.found_item.posted_by_id,
    )
    db.add(record)
    db.flush()
    return record


def _finalize_return(
    db: Session,
    record: ItemReturn,
    method: ReturnMethod,
) -> None:
    if record.returned_at:
        return

    now = datetime.now(timezone.utc)
    record.returned_at = now
    record.method = method
    record.tipping_window_ends_at = now + timedelta(days=RETURN_WINDOW_DAYS)
    record.dispute_window_ends_at = now + timedelta(days=RETURN_WINDOW_DAYS)

    lost = db.query(Item).filter(Item.id == record.lost_item_id).first()
    found = db.query(Item).filter(Item.id == record.found_item_id).first()
    if lost:
        lost.status = ItemStatus.RETURNED
        lost.updated_at = now
    if found:
        found.status = ItemStatus.RETURNED
        found.updated_at = now

    trust_service.award_successful_return(
        db, record.found_owner_id, record.found_item_id
    )

    notification_service.notify_item_returned(
        db,
        lost_owner_id=record.lost_owner_id,
        found_owner_id=record.found_owner_id,
        return_id=record.id,
        lost_item_id=record.lost_item_id,
        found_item_id=record.found_item_id,
    )


def _build_status(
    db: Session,
    record: ItemReturn,
    match: PotentialMatch,
    conv: Conversation | None,
    viewer: User,
) -> ReturnStatusResponse:
    lost = match.lost_item
    found = match.found_item
    lost_owner = db.query(User).filter(User.id == record.lost_owner_id).first()
    found_owner = db.query(User).filter(User.id == record.found_owner_id).first()
    if not lost_owner or not found_owner:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    is_lost_owner = viewer.id == record.lost_owner_id
    viewer_role = "lost_owner" if is_lost_owner else "found_owner"
    complete = record.returned_at is not None

    now = datetime.now(timezone.utc)
    qr_active = bool(
        record.qr_token_hash
        and not record.qr_consumed_at
        and record.qr_expires_at
        and record.qr_expires_at > now
        and not complete
    )

    return ReturnStatusResponse(
        return_id=record.id,
        match_id=match.id,
        conversation_id=conv.id if conv else None,
        lost_item=_item_summary(lost),
        found_item=_item_summary(found),
        lost_owner=_party(lost_owner),
        found_owner=_party(found_owner),
        viewer_role=viewer_role,
        finder_handed_over=record.finder_handed_over_at is not None,
        owner_received=record.owner_received_at is not None,
        is_complete=complete,
        returned_at=record.returned_at,
        method=record.method,
        qr_active=qr_active,
        qr_expires_at=record.qr_expires_at,
        tipping_window_ends_at=record.tipping_window_ends_at,
        dispute_window_ends_at=record.dispute_window_ends_at,
        can_confirm_finder=(
            not complete
            and viewer.id == record.found_owner_id
            and record.finder_handed_over_at is None
        ),
        can_confirm_owner=(
            not complete
            and viewer.id == record.lost_owner_id
            and record.owner_received_at is None
        ),
        can_generate_qr=(
            not complete
            and viewer.id == record.found_owner_id
            and not qr_active
        ),
        awaiting_owner_receipt=(
            not complete
            and is_lost_owner
            and record.finder_handed_over_at is not None
            and record.owner_received_at is None
        ),
        awaiting_finder_handover=(
            not complete
            and not is_lost_owner
            and record.finder_handed_over_at is None
            and record.owner_received_at is not None
        ),
    )


def get_return_status(
    db: Session, match_id: uuid.UUID, user: User
) -> ReturnStatusResponse:
    match, conv = _get_verified_match(db, match_id, user)
    record = _get_or_create_return(db, match)
    return _build_status(db, record, match, conv, user)


def get_return_status_by_item(
    db: Session, item_id: uuid.UUID, user: User
) -> ReturnStatusResponse:
    match = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(
            PotentialMatch.status == PotentialMatchStatus.VERIFIED,
            (PotentialMatch.lost_item_id == item_id) | (PotentialMatch.found_item_id == item_id),
        )
        .order_by(PotentialMatch.created_at.desc())
        .first()
    )
    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No verified match found for this item.",
        )
    if user.id not in (match.lost_item.posted_by_id, match.found_item.posted_by_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return get_return_status(db, match.id, user)


def finder_confirm_handed_over(
    db: Session, match_id: uuid.UUID, user: User
) -> ReturnActionResponse:
    match, conv = _get_verified_match(db, match_id, user)
    if user.id != match.found_item.posted_by_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the finder can confirm the item was handed over.",
        )
    record = _get_or_create_return(db, match)
    if record.returned_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Return already completed.")

    if not record.finder_handed_over_at:
        record.finder_handed_over_at = datetime.now(timezone.utc)
        notification_service.notify_finder_handed_over(
            db,
            owner_id=record.lost_owner_id,
            match_id=match.id,
            return_id=record.id,
        )

    completed = False
    message = "You confirmed you handed over the item. Waiting for the owner to confirm receipt."
    if record.owner_received_at:
        _finalize_return(db, record, ReturnMethod.DUAL_CONFIRM)
        completed = True
        message = "Return confirmed! Both parties agreed — the item is marked as returned."

    db.commit()
    status_resp = _build_status(db, record, match, conv, user)
    return ReturnActionResponse(status=status_resp, message=message, completed=completed)


def owner_confirm_received(
    db: Session, match_id: uuid.UUID, user: User
) -> ReturnActionResponse:
    match, conv = _get_verified_match(db, match_id, user)
    if user.id != match.lost_item.posted_by_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the lost item owner can confirm receipt.",
        )
    record = _get_or_create_return(db, match)
    if record.returned_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Return already completed.")

    if not record.owner_received_at:
        record.owner_received_at = datetime.now(timezone.utc)

    completed = False
    message = "You confirmed you received the item. Waiting for the finder to confirm handover."
    if record.finder_handed_over_at:
        _finalize_return(db, record, ReturnMethod.DUAL_CONFIRM)
        completed = True
        message = "Return confirmed! The item is marked as returned."

    db.commit()
    status_resp = _build_status(db, record, match, conv, user)
    return ReturnActionResponse(status=status_resp, message=message, completed=completed)


def generate_qr_token(
    db: Session, match_id: uuid.UUID, user: User
) -> QrGenerateResponse:
    match, conv = _get_verified_match(db, match_id, user)
    if user.id != match.found_item.posted_by_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the finder can generate a return QR code.",
        )
    record = _get_or_create_return(db, match)
    if record.returned_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Return already completed.")

    token = secrets.token_urlsafe(32)
    record.qr_token_hash = _hash_token(token)
    record.qr_expires_at = datetime.now(timezone.utc) + timedelta(hours=QR_VALID_HOURS)
    record.qr_consumed_at = None
    db.commit()

    status_resp = _build_status(db, record, match, conv, user)
    payload = f"faind-return:{record.id}:{token}"
    return QrGenerateResponse(
        token=token,
        expires_at=record.qr_expires_at,
        qr_payload=payload,
        status=status_resp,
    )


def redeem_qr_token(db: Session, user: User, token: str) -> ReturnActionResponse:
    if user.status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active.")

    token = token.strip()
    if token.startswith("faind-return:"):
        parts = token.split(":")
        if len(parts) >= 3:
            token = parts[-1]

    token_hash = _hash_token(token)
    now = datetime.now(timezone.utc)

    record = (
        db.query(ItemReturn)
        .filter(ItemReturn.qr_token_hash == token_hash)
        .first()
    )
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired QR code.")

    if user.id != record.lost_owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the lost item owner can scan this return QR code.",
        )
    if record.returned_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Return already completed.")
    if record.qr_consumed_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This QR code was already used.")
    if not record.qr_expires_at or record.qr_expires_at < now:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="This QR code has expired.")

    match = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(PotentialMatch.id == record.potential_match_id)
        .first()
    )
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.potential_match_id == record.potential_match_id,
            Conversation.status == ConversationStatus.UNLOCKED,
        )
        .first()
    )

    record.qr_consumed_at = now
    record.finder_handed_over_at = record.finder_handed_over_at or now
    record.owner_received_at = now
    _finalize_return(db, record, ReturnMethod.QR_SCAN)
    db.commit()

    status_resp = _build_status(db, record, match, conv, user)
    return ReturnActionResponse(
        status=status_resp,
        message="QR scan successful — the item is marked as returned.",
        completed=True,
    )


def list_my_returns(db: Session, user: User) -> ReturnedListResponse:
    rows = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.returned_at.isnot(None),
            (ItemReturn.lost_owner_id == user.id) | (ItemReturn.found_owner_id == user.id),
        )
        .order_by(ItemReturn.returned_at.desc())
        .all()
    )
    items: list[ReturnedListItem] = []
    for record in rows:
        is_owner = user.id == record.lost_owner_id
        other_id = record.found_owner_id if is_owner else record.lost_owner_id
        other = db.query(User).filter(User.id == other_id).first()
        item_id = record.lost_item_id if is_owner else record.found_item_id
        item = db.query(Item).filter(Item.id == item_id).first()
        if not other or not item:
            continue
        items.append(
            ReturnedListItem(
                return_id=record.id,
                match_id=record.potential_match_id,
                item_label=_item_label(item),
                category=item.category,
                returned_at=record.returned_at,
                other_user_display_name=other.full_name or other.username,
                other_user_trust_tier=trust_service.get_trust_tier(other.trust_score),
                viewer_role="lost_owner" if is_owner else "found_owner",
                is_owner=is_owner,
                appreciation_sent=is_owner and record.appreciation_sent_at is not None,
                appreciation_received=(not is_owner) and record.appreciation_sent_at is not None,
                dispute_active=returned_items_service.is_dispute_active(record),
            )
        )
    return ReturnedListResponse(items=items)


def get_return_detail(
    db: Session, return_id: uuid.UUID, user: User
) -> ReturnedDetailResponse:
    record = db.query(ItemReturn).filter(ItemReturn.id == return_id).first()
    if not record or not record.returned_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found.")
    if user.id not in (record.lost_owner_id, record.found_owner_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    match = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(PotentialMatch.id == record.potential_match_id)
        .first()
    )
    conv = (
        db.query(Conversation)
        .filter(Conversation.potential_match_id == record.potential_match_id)
        .first()
    )
    other_id = record.found_owner_id if user.id == record.lost_owner_id else record.lost_owner_id
    other = db.query(User).filter(User.id == other_id).first()
    if not match or not other:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found.")

    now = datetime.now(timezone.utc)
    is_owner = user.id == record.lost_owner_id
    if tipping_service._sync_appreciation_from_success_tip(db, record):
        db.commit()
        db.refresh(record)
    lifecycle = returned_items_service.build_lifecycle_flags(record, user, now)
    return ReturnedDetailResponse(
        return_id=record.id,
        match_id=record.potential_match_id,
        conversation_id=conv.id if conv else None,
        returned_at=record.returned_at,
        method=record.method or ReturnMethod.DUAL_CONFIRM,
        item_label=_item_label(match.lost_item),
        category=match.lost_item.category,
        lost_item=_item_summary(match.lost_item),
        found_item=_item_summary(match.found_item),
        other_user=_party(other),
        viewer_role="lost_owner" if is_owner else "found_owner",
        dates_summary={
            "lost": match.lost_item.date_occurred.isoformat(),
            "found": match.found_item.date_occurred.isoformat(),
            "returned": record.returned_at.isoformat(),
        },
        tipping_window_ends_at=record.tipping_window_ends_at,
        dispute_window_ends_at=record.dispute_window_ends_at,
        dispute_reason=record.dispute_reason if lifecycle["dispute_active"] else None,
        paystack_ready=tipping_service.paystack_configured(),
        summary_note=record.summary_note,
        appreciation_message=(
            APPRECIATION_MESSAGE_FINDER
            if not is_owner and lifecycle.get("appreciation_sent")
            else None
        ),
        **lifecycle,
    )


APPRECIATION_MESSAGE_FINDER = "The owner expressed appreciation to the finder."


def count_user_returns(db: Session, user_id: uuid.UUID) -> int:
    return (
        db.query(ItemReturn)
        .filter(
            ItemReturn.returned_at.isnot(None),
            (ItemReturn.lost_owner_id == user_id) | (ItemReturn.found_owner_id == user_id),
        )
        .count()
    )


def archive_expired_returned_items(db: Session) -> int:
    """Section 16.7 — RETURNED → ARCHIVED after tipping/dispute windows close."""
    return returned_items_service.archive_completed_returns(db)


def process_return_reminders(db: Session) -> int:
    """Section 15.1 — reminder at 7d; admin flag at 14d if owner never confirmed."""
    now = datetime.now(timezone.utc)
    updated = 0
    pending = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.returned_at.is_(None),
            ItemReturn.finder_handed_over_at.isnot(None),
            ItemReturn.owner_received_at.is_(None),
        )
        .all()
    )
    for record in pending:
        handed = record.finder_handed_over_at
        if not handed:
            continue
        age_days = (now - handed).days
        if age_days >= ADMIN_REVIEW_DAYS and not record.admin_review_flagged:
            record.admin_review_flagged = True
            updated += 1
        elif age_days >= OWNER_REMINDER_DAYS and not record.owner_reminder_sent_at:
            notification_service.notify_return_receipt_reminder(
                db,
                owner_id=record.lost_owner_id,
                match_id=record.potential_match_id,
                return_id=record.id,
                lost_item_id=record.lost_item_id,
            )
            record.owner_reminder_sent_at = now
            updated += 1
    if updated:
        db.commit()
    return updated

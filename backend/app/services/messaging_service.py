"""
Structured claim messaging — Section 13.2 / 13.3 (W13).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.authority import Authority
from app.models.claim import Claim, ClaimStatus
from app.models.claim_inquiry import (
    INQUIRY_LABELS,
    REPLY_LABELS,
    ClaimInquiry,
    ClaimInquiryReply,
    InquiryMessageType,
    ReplyMessageType,
)
from app.models.item import Item, ItemStatus, ItemType
from app.models.user import User
from app.schemas.messaging import (
    InquiryReplySummary,
    InquirySummary,
    OwnerClaimStatusResponse,
    SendInquiryRequest,
    SendInquiryResponse,
)
from app.services import authority_notification_service, notification_service

_ACTIVE_CLAIM_STATUSES = frozenset({ClaimStatus.PENDING, ClaimStatus.VERIFIED})
_AT_DROPPOINT_STATUSES = frozenset({
    ItemStatus.AT_DROPPOINT,
    ItemStatus.UNDER_CLAIM_REVIEW,
})


def _inquiry_label(message_type: InquiryMessageType) -> str:
    return INQUIRY_LABELS[message_type]


def _reply_label(reply_type: ReplyMessageType, *, operating_hours: str | None = None) -> str:
    if reply_type == ReplyMessageType.COME_DURING_HOURS and operating_hours:
        return f"Please come between {operating_hours}"
    return REPLY_LABELS[reply_type]


def _to_inquiry_summary(
    inquiry: ClaimInquiry,
    *,
    operating_hours: str | None = None,
) -> InquirySummary:
    reply_summary = None
    if inquiry.reply:
        reply_summary = InquiryReplySummary(
            reply_type=inquiry.reply.reply_type.value,
            reply_label=_reply_label(inquiry.reply.reply_type, operating_hours=operating_hours),
            created_at=inquiry.reply.created_at,
        )
    return InquirySummary(
        id=inquiry.id,
        message_type=inquiry.message_type.value,
        message_label=_inquiry_label(inquiry.message_type),
        created_at=inquiry.created_at,
        reply=reply_summary,
    )


def inquiry_summaries_for_claims(
    db: Session,
    claim_ids: list[uuid.UUID],
    *,
    operating_hours: str | None = None,
) -> dict[uuid.UUID, InquirySummary]:
    if not claim_ids:
        return {}
    rows = (
        db.query(ClaimInquiry)
        .options(joinedload(ClaimInquiry.reply))
        .filter(ClaimInquiry.claim_id.in_(claim_ids))
        .all()
    )
    return {
        row.claim_id: _to_inquiry_summary(row, operating_hours=operating_hours)
        for row in rows
    }


def _get_owner_claim(db: Session, user: User, claim_id: uuid.UUID) -> Claim:
    claim = (
        db.query(Claim)
        .options(joinedload(Claim.found_item).joinedload(Item.drop_point))
        .filter(Claim.id == claim_id, Claim.claimant_user_id == user.id)
        .first()
    )
    if not claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")
    return claim


def get_owner_claim_status(
    db: Session,
    user: User,
    claim_id: uuid.UUID,
) -> OwnerClaimStatusResponse:
    claim = _get_owner_claim(db, user, claim_id)
    item = claim.found_item
    drop_point = item.drop_point if item else None
    hours = drop_point.operating_hours if drop_point else None

    inquiry_row = (
        db.query(ClaimInquiry)
        .options(joinedload(ClaimInquiry.reply))
        .filter(ClaimInquiry.claim_id == claim.id)
        .first()
    )
    inquiry = _to_inquiry_summary(inquiry_row, operating_hours=hours) if inquiry_row else None

    if item and item.status in (ItemStatus.FOUND, ItemStatus.OVERDUE):
        collection_phase = "not_at_drop_point"
    else:
        collection_phase = "ready_for_collection"

    can_send = (
        claim.status in _ACTIVE_CLAIM_STATUSES
        and inquiry_row is None
    )

    return OwnerClaimStatusResponse(
        claim_id=claim.id,
        claim_status=claim.status.value,
        claim_path=claim.claim_path.value,
        collection_phase=collection_phase,
        found_item_id=claim.found_item_id,
        found_item_status=item.status.value if item else "unknown",
        found_item_description=item.public_description if item else "",
        drop_point_name=drop_point.name if drop_point else None,
        operating_hours=hours,
        can_send_inquiry=can_send,
        inquiry=inquiry,
    )


def send_owner_inquiry(
    db: Session,
    user: User,
    claim_id: uuid.UUID,
    payload: SendInquiryRequest,
) -> SendInquiryResponse:
    claim = _get_owner_claim(db, user, claim_id)
    if claim.status not in _ACTIVE_CLAIM_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Inquiries can only be sent on active claims.",
        )

    existing = (
        db.query(ClaimInquiry.id)
        .filter(ClaimInquiry.claim_id == claim.id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already sent an inquiry for this claim.",
        )

    try:
        message_type = InquiryMessageType(payload.message_type)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid inquiry message type.",
        ) from exc

    inquiry = ClaimInquiry(
        claim_id=claim.id,
        message_type=message_type,
        created_at=datetime.now(timezone.utc),
    )
    db.add(inquiry)
    db.flush()

    item = claim.found_item
    drop_point = item.drop_point if item else None
    authority_notification_service.notify_authority_claim_inquiry(
        db,
        claim=claim,
        item=item,
        inquiry=inquiry,
        drop_point=drop_point,
    )

    hours = drop_point.operating_hours if drop_point else None
    return SendInquiryResponse(
        inquiry=_to_inquiry_summary(inquiry, operating_hours=hours),
        message="Your inquiry has been sent to the drop point authority.",
    )


def _get_scoped_inquiry(
    db: Session,
    authority: Authority,
    inquiry_id: uuid.UUID,
) -> ClaimInquiry:
    inquiry = (
        db.query(ClaimInquiry)
        .options(
            joinedload(ClaimInquiry.reply),
            joinedload(ClaimInquiry.claim).joinedload(Claim.found_item).joinedload(Item.drop_point),
            joinedload(ClaimInquiry.claim).joinedload(Claim.claimant),
        )
        .filter(ClaimInquiry.id == inquiry_id)
        .first()
    )
    if not inquiry or not inquiry.claim or not inquiry.claim.found_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found.")
    item = inquiry.claim.found_item
    if item.drop_point_id != authority.drop_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This inquiry belongs to a different drop point.",
        )
    return inquiry


def reply_to_inquiry(
    db: Session,
    authority: Authority,
    inquiry_id: uuid.UUID,
    reply_type_value: str,
) -> ClaimInquiry:
    inquiry = _get_scoped_inquiry(db, authority, inquiry_id)
    if inquiry.reply:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This inquiry has already been answered.",
        )

    try:
        reply_type = ReplyMessageType(reply_type_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid reply type.",
        ) from exc

    reply = ClaimInquiryReply(
        inquiry_id=inquiry.id,
        reply_type=reply_type,
        replied_by_authority_id=authority.id,
        created_at=datetime.now(timezone.utc),
    )
    db.add(reply)
    db.flush()
    db.refresh(inquiry)

    claim = inquiry.claim
    item = claim.found_item
    drop_point = item.drop_point if item else authority.drop_point
    hours = drop_point.operating_hours if drop_point else None
    reply_label = _reply_label(reply_type, operating_hours=hours)

    notification_service.notify_owner_inquiry_reply(
        db,
        owner_id=claim.claimant_user_id,
        claim_id=claim.id,
        found_item_id=claim.found_item_id,
        reply_label=reply_label,
    )
    return inquiry

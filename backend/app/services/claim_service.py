"""
Claim submission — Path A and Path C (Section 8).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.authority import Authority
from app.models.claim import Claim, ClaimPath, ClaimStatus
from app.models.drop_point import DropPoint
from app.models.item import Item, ItemStatus, ItemType
from app.models.handover import Handover
from app.models.notification import Notification
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.user import User
from app.schemas.claim import (
    ClaimFormSubmit,
    ClaimSubmitResponse,
    ViewerClaimSummary,
    MyClaimCard,
    MyClaimsListResponse,
    AwaitingConfirmationCard,
    AwaitingConfirmationListResponse,
)
from app.services import authority_notification_service, notification_service

_CLAIMABLE_STATUSES = frozenset({
    ItemStatus.FOUND,
    ItemStatus.OVERDUE,
    ItemStatus.AT_DROPPOINT,
    ItemStatus.UNDER_CLAIM_REVIEW,
})

_PATH_A_MATCH_STATUSES = frozenset({
    PotentialMatchStatus.ACTIVE,
    PotentialMatchStatus.PENDING_REVIEW,
})

_AT_DROPPOINT_STATUSES = frozenset({
    ItemStatus.AT_DROPPOINT,
    ItemStatus.UNDER_CLAIM_REVIEW,
})


def _get_found_item(db: Session, found_item_id: uuid.UUID) -> Item:
    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(Item.id == found_item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found.")
    return item


def _assert_claimable(item: Item) -> None:
    if item.status not in _CLAIMABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This item is not accepting claims.",
        )


def _existing_claim(db: Session, found_item_id: uuid.UUID, user_id: uuid.UUID) -> Claim | None:
    return (
        db.query(Claim)
        .filter(
            Claim.found_item_id == found_item_id,
            Claim.claimant_user_id == user_id,
        )
        .first()
    )


def _path_a_match(
    db: Session,
    user: User,
    found_item_id: uuid.UUID,
) -> PotentialMatch:
    match = (
        db.query(PotentialMatch)
        .join(Item, PotentialMatch.lost_item_id == Item.id)
        .filter(
            PotentialMatch.found_item_id == found_item_id,
            Item.posted_by_id == user.id,
            PotentialMatch.status.in_(_PATH_A_MATCH_STATUSES),
        )
        .first()
    )
    if not match:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No AI match links your lost item to this found item.",
        )
    return match


def _build_response(claim: Claim, item: Item) -> ClaimSubmitResponse:
    drop_point: DropPoint | None = item.drop_point
    if item.status in (ItemStatus.FOUND, ItemStatus.OVERDUE):
        message = (
            "Your claim has been submitted. This item has not been dropped off at the "
            "drop point yet — we will notify you when it is ready for collection."
        )
        return ClaimSubmitResponse(
            claim_id=claim.id,
            message=message,
            collection_phase="not_at_drop_point",
            claim_status=claim.status.value,
            created_at=claim.created_at,
        )

    dp_name = drop_point.name if drop_point else "the drop point"
    hours = drop_point.operating_hours if drop_point else None
    message = (
        f"Your claim has been submitted. The item is at {dp_name}. "
        f"Please bring your student ID during operating hours"
        f"{f' ({hours})' if hours else ''} to collect it."
    )
    return ClaimSubmitResponse(
        claim_id=claim.id,
        message=message,
        collection_phase="ready_for_collection",
        drop_point_name=drop_point.name if drop_point else None,
        operating_hours=hours,
        claim_status=claim.status.value,
        created_at=claim.created_at,
    )


def _notify_parties(
    db: Session,
    *,
    claim: Claim,
    item: Item,
    claimant: User,
) -> None:
    authority_notification_service.notify_authority_new_claim(
        db, claim=claim, item=item, claimant=claimant
    )
    from app.services import admin_notification_service

    if item.drop_point:
        admin_notification_service.notify_admins_new_claim(
            db,
            claim_id=claim.id,
            found_item_id=item.id,
            drop_point_name=item.drop_point.name,
            path=claim.claim_path.value,
        )
    if item.status in (ItemStatus.FOUND, ItemStatus.OVERDUE):
        notification_service.notify_owner_claim_not_at_drop_point(
            db,
            owner_id=claimant.id,
            found_item_id=item.id,
            claim_id=claim.id,
        )
    elif item.status in _AT_DROPPOINT_STATUSES:
        notification_service.notify_owner_claim_ready_for_collection(
            db,
            owner_id=claimant.id,
            found_item_id=item.id,
            claim_id=claim.id,
            drop_point=item.drop_point,
        )


def _finalize_claim(
    db: Session,
    *,
    claim: Claim,
    item: Item,
    claimant: User,
) -> ClaimSubmitResponse:
    if item.status == ItemStatus.AT_DROPPOINT:
        item.status = ItemStatus.UNDER_CLAIM_REVIEW
        item.updated_at = datetime.now(timezone.utc)

    db.flush()
    _notify_parties(db, claim=claim, item=item, claimant=claimant)
    return _build_response(claim, item)


def submit_path_a(
    db: Session,
    user: User,
    found_item_id: uuid.UUID,
    payload: ClaimFormSubmit,
) -> ClaimSubmitResponse:
    """Path A — AI match required (Section 8.1)."""
    item = _get_found_item(db, found_item_id)
    _assert_claimable(item)

    if user.university_id != item.university_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    existing = _existing_claim(db, found_item_id, user.id)
    if existing:
        if existing.status == ClaimStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a pending claim on this item.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a claim on this item.",
        )

    match = _path_a_match(db, user, found_item_id)

    claim = Claim(
        found_item_id=found_item_id,
        claimant_user_id=user.id,
        claim_path=ClaimPath.A,
        photo_url=payload.photo_url,
        date_lost=payload.date_lost,
        time_lost=payload.time_lost,
        description=payload.description,
        ai_confidence_score=match.match_score,
        status=ClaimStatus.PENDING,
    )
    db.add(claim)
    db.flush()

    return _finalize_claim(db, claim=claim, item=item, claimant=user)


def submit_path_c(
    db: Session,
    user: User,
    found_item_id: uuid.UUID,
    payload: ClaimFormSubmit,
) -> ClaimSubmitResponse:
    """Path C — browse and claim, no match required (Section 8.3)."""
    item = _get_found_item(db, found_item_id)
    _assert_claimable(item)

    if user.university_id != item.university_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    if item.status in (ItemStatus.FOUND, ItemStatus.OVERDUE):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This item has not been dropped off yet. Register your interest "
                "to be notified when it arrives at the drop point."
            ),
        )

    if item.posted_by_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot claim your own found item post.",
        )

    lost_location = (payload.lost_location or "").strip()
    if not lost_location:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Where you lost the item is required for this claim path.",
        )
    if not payload.date_lost or not payload.time_lost:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Date and time lost are required for this claim path.",
        )

    existing = _existing_claim(db, found_item_id, user.id)
    if existing:
        if existing.status == ClaimStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a pending claim on this item.",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already submitted a claim on this item.",
        )

    claim = Claim(
        found_item_id=found_item_id,
        claimant_user_id=user.id,
        claim_path=ClaimPath.C,
        photo_url=payload.photo_url,
        date_lost=payload.date_lost,
        time_lost=payload.time_lost,
        description=payload.description,
        lost_location=lost_location,
        status=ClaimStatus.PENDING,
    )
    db.add(claim)
    db.flush()

    return _finalize_claim(db, claim=claim, item=item, claimant=user)


def _called_to_collect_claim_ids(
    db: Session,
    user_id: uuid.UUID,
    claim_ids: list[uuid.UUID],
) -> set[uuid.UUID]:
    if not claim_ids:
        return set()
    rows = (
        db.query(Notification.reference_id)
        .filter(
            Notification.user_id == user_id,
            Notification.reference_id.in_(claim_ids),
            Notification.title == "Please come to collect",
        )
        .all()
    )
    return {row[0] for row in rows if row[0]}


def _build_viewer_claim_summary(
    claim: Claim,
    *,
    called_to_collect: bool,
) -> ViewerClaimSummary:
    item = claim.found_item
    drop_point = item.drop_point if item else None
    dp_name = drop_point.name if drop_point else "the drop point"
    hours = drop_point.operating_hours if drop_point else None

    if claim.status == ClaimStatus.REJECTED:
        return ViewerClaimSummary(
            claim_id=claim.id,
            claim_status="rejected",
            claim_path=claim.claim_path.value,
            viewer_state="rejected",
            message=(
                "Your claim was not verified. The item was "
                "awarded to another claimant."
            ),
            drop_point_name=dp_name,
            operating_hours=hours,
        )
    if claim.status == ClaimStatus.VERIFIED:
        return ViewerClaimSummary(
            claim_id=claim.id,
            claim_status="verified",
            claim_path=claim.claim_path.value,
            viewer_state="verified",
            message=f"You have been verified as the owner. Please collect from {dp_name}",
            drop_point_name=dp_name,
            operating_hours=hours,
        )
    if called_to_collect:
        hours_part = f" Operating hours: {hours}" if hours else ""
        return ViewerClaimSummary(
            claim_id=claim.id,
            claim_status="pending",
            claim_path=claim.claim_path.value,
            viewer_state="called_to_collect",
            message=(
                f"You have been called to collect this item at {dp_name}.{hours_part}"
            ),
            drop_point_name=dp_name,
            operating_hours=hours,
        )
    return ViewerClaimSummary(
        claim_id=claim.id,
        claim_status="pending",
        claim_path=claim.claim_path.value,
        viewer_state="pending_review",
        message=f"Your claim is being reviewed by the authority at {dp_name}",
        drop_point_name=dp_name,
        operating_hours=hours,
    )


def get_viewer_claim_for_found_item(
    db: Session,
    user: User | None,
    found_item_id: uuid.UUID,
) -> ViewerClaimSummary | None:
    if not user:
        return None
    claim = (
        db.query(Claim)
        .options(joinedload(Claim.found_item).joinedload(Item.drop_point))
        .filter(
            Claim.found_item_id == found_item_id,
            Claim.claimant_user_id == user.id,
        )
        .first()
    )
    if not claim:
        return None
    called = _called_to_collect_claim_ids(db, user.id, [claim.id])
    return _build_viewer_claim_summary(claim, called_to_collect=claim.id in called)


def get_viewer_claims_for_found_items(
    db: Session,
    user: User | None,
    found_item_ids: list[uuid.UUID],
) -> dict[uuid.UUID, ViewerClaimSummary]:
    if not user or not found_item_ids:
        return {}
    claims = (
        db.query(Claim)
        .options(joinedload(Claim.found_item).joinedload(Item.drop_point))
        .filter(
            Claim.found_item_id.in_(found_item_ids),
            Claim.claimant_user_id == user.id,
        )
        .all()
    )
    if not claims:
        return {}
    called = _called_to_collect_claim_ids(db, user.id, [c.id for c in claims])
    return {
        c.found_item_id: _build_viewer_claim_summary(
            c, called_to_collect=c.id in called
        )
        for c in claims
    }


_STATUS_LABELS = {
    "pending_review": "Pending Review",
    "called_to_collect": "Called to Collect",
    "rejected": "Rejected",
}


def _description_preview(text: str, limit: int = 120) -> str:
    text = (text or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _thumbnail_url(item: Item) -> str | None:
    urls = item.image_urls or []
    return urls[0] if urls else None


def list_my_claims(db: Session, user: User) -> MyClaimsListResponse:
    """Pending / called-to-collect claims and rejected claims within 7 days."""
    now = datetime.now(timezone.utc)
    rejected_cutoff = now - timedelta(days=7)
    claims = (
        db.query(Claim)
        .options(joinedload(Claim.found_item).joinedload(Item.drop_point))
        .filter(Claim.claimant_user_id == user.id)
        .order_by(Claim.created_at.desc())
        .all()
    )
    if not claims:
        return MyClaimsListResponse(claims=[])

    called = _called_to_collect_claim_ids(db, user.id, [c.id for c in claims])
    cards: list[MyClaimCard] = []
    for claim in claims:
        if claim.status == ClaimStatus.VERIFIED:
            continue
        if claim.status == ClaimStatus.REJECTED:
            rejected_at = claim.rejected_at or claim.created_at
            if rejected_at < rejected_cutoff:
                continue
        item = claim.found_item
        if not item:
            continue
        summary = _build_viewer_claim_summary(
            claim, called_to_collect=claim.id in called
        )
        if summary.viewer_state == "verified":
            continue
        drop_point = item.drop_point
        cards.append(
            MyClaimCard(
                claim_id=claim.id,
                found_item_id=item.id,
                thumbnail_url=_thumbnail_url(item),
                category=item.category.value,
                description_preview=_description_preview(item.public_description),
                status_label=_STATUS_LABELS.get(summary.viewer_state, "Pending Review"),
                viewer_state=summary.viewer_state,
                drop_point_name=summary.drop_point_name or "Drop point",
                operating_hours=summary.operating_hours,
            )
        )
    return MyClaimsListResponse(claims=cards)


def list_awaiting_confirmation(db: Session, user: User) -> AwaitingConfirmationListResponse:
    """Verified claims awaiting owner digital sign-off or collection."""
    claims = (
        db.query(Claim)
        .options(joinedload(Claim.found_item).joinedload(Item.drop_point))
        .filter(
            Claim.claimant_user_id == user.id,
            Claim.status == ClaimStatus.VERIFIED,
        )
        .order_by(Claim.created_at.desc())
        .all()
    )
    if not claims:
        return AwaitingConfirmationListResponse(items=[])

    claim_ids = [c.id for c in claims]
    handovers = {
        h.claim_id: h
        for h in db.query(Handover).filter(Handover.claim_id.in_(claim_ids)).all()
    }

    items: list[AwaitingConfirmationCard] = []
    for claim in claims:
        item = claim.found_item
        if not item:
            continue
        handover = handovers.get(claim.id)
        if handover and (handover.owner_confirmed or handover.authority_override_note):
            continue
        drop_point = item.drop_point
        dp_name = drop_point.name if drop_point else "Drop point"
        can_confirm = bool(
            handover
            and not handover.owner_confirmed
            and not handover.authority_override_note
        )
        items.append(
            AwaitingConfirmationCard(
                claim_id=claim.id,
                handover_id=handover.id if handover else None,
                found_item_id=item.id,
                thumbnail_url=_thumbnail_url(item),
                category=item.category.value,
                description_preview=_description_preview(item.public_description),
                drop_point_name=dp_name,
                drop_point_address=dp_name,
                operating_hours=drop_point.operating_hours if drop_point else None,
                can_confirm=can_confirm,
            )
        )
    return AwaitingConfirmationListResponse(items=items)

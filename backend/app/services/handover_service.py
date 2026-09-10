"""
Handover flow — Section 11 (W10).
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.models.authority import Authority
from app.models.claim import Claim, ClaimPath, ClaimStatus
from app.models.handover import Handover
from app.models.admin_log import AdminActionType
from app.models.item import Item, ItemStatus, ItemType
from app.models.item_return import ItemReturn, ReturnMethod
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.user import User
from app.schemas.handover import (
    HandoverAuthorityDetail,
    HandoverConfirmResponse,
    HandoverOwnerResponse,
    HandoverQueueItem,
    HandoverQueueResponse,
    HandoverStartRequest,
    HandoverStartResponse,
    HandoverOverrideRequest,
)

RETURN_WINDOW_DAYS = 7
from app.services import notification_service, token_service
from app.utils.encryption import decrypt, encrypt

_VERIFIED = ClaimStatus.VERIFIED


def _is_complete(handover: Handover) -> bool:
    return handover.owner_confirmed or bool(handover.authority_override_note)


def _handover_status(handover: Handover | None) -> str:
    if handover is None:
        return "ready_to_start"
    if _is_complete(handover):
        return "completed"
    return "awaiting_owner"


def _build_authority_detail(
    handover: Handover,
    item: Item,
    *,
    claim: Claim | None = None,
) -> HandoverAuthorityDetail:
    student_id = None
    if handover.claimant_student_id_encrypted:
        student_id = decrypt(handover.claimant_student_id_encrypted)

    claim = claim or handover.claim
    complete = _is_complete(handover)
    completed_at = None
    if complete:
        completed_at = handover.owner_confirmed_at or handover.created_at

    finder_display_name = None
    finder_username = None
    if item.posted_by:
        finder_display_name = item.posted_by.full_name or item.posted_by.username
        finder_username = item.posted_by.username
    elif item.posted_by_id is None:
        finder_display_name = "Anonymous finder"

    owner_display_name = None
    if claim and claim.claimant:
        owner_display_name = claim.claimant.full_name or claim.claimant.username

    drop_point_name = item.drop_point.name if item.drop_point else None

    return HandoverAuthorityDetail(
        id=handover.id,
        claim_id=handover.claim_id,
        item_id=handover.item_id,
        condition_photo_url=handover.condition_photo_url,
        claimant_name=handover.claimant_name,
        claimant_phone=decrypt(handover.claimant_phone_encrypted),
        claimant_student_id=student_id,
        claimant_photo_url=handover.claimant_photo_url,
        owner_confirmed=handover.owner_confirmed,
        owner_confirmed_at=handover.owner_confirmed_at,
        authority_override_note=handover.authority_override_note,
        authority_override=bool(handover.authority_override_note),
        handover_status="completed" if complete else "awaiting_owner",
        found_item_description=item.public_description,
        found_item_category=item.category.value,
        created_at=handover.created_at,
        found_item_image_urls=item.image_urls or [],
        found_item_location_label=item.location_label,
        found_item_date_occurred=item.date_occurred.date() if item.date_occurred else None,
        finder_display_name=finder_display_name,
        finder_username=finder_username,
        owner_display_name=owner_display_name,
        claim_path=claim.claim_path.value if claim else None,
        ai_confidence_score=claim.ai_confidence_score if claim else None,
        completed_at=completed_at,
        drop_point_name=drop_point_name,
    )


def _get_scoped_claim_for_authority(
    db: Session,
    authority: Authority,
    claim_id: uuid.UUID,
) -> Claim:
    claim = (
        db.query(Claim)
        .options(joinedload(Claim.claimant), joinedload(Claim.found_item))
        .filter(Claim.id == claim_id)
        .first()
    )
    if not claim or not claim.found_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")
    if claim.found_item.drop_point_id != authority.drop_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This claim belongs to a different drop point.",
        )
    return claim


def _get_scoped_handover_for_authority(
    db: Session,
    authority: Authority,
    handover_id: uuid.UUID,
) -> tuple[Handover, Item]:
    handover = (
        db.query(Handover)
        .options(
            joinedload(Handover.claim).joinedload(Claim.found_item),
            joinedload(Handover.item).joinedload(Item.drop_point),
            joinedload(Handover.item).joinedload(Item.posted_by),
        )
        .filter(Handover.id == handover_id)
        .first()
    )
    if not handover or not handover.claim or not handover.claim.found_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handover not found.")
    if handover.claim.found_item.drop_point_id != authority.drop_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This handover belongs to a different drop point.",
        )
    return handover, handover.item


def _get_scoped_handover_for_owner(
    db: Session,
    user: User,
    handover_id: uuid.UUID,
) -> tuple[Handover, Item]:
    handover = (
        db.query(Handover)
        .options(joinedload(Handover.claim), joinedload(Handover.item))
        .filter(Handover.id == handover_id)
        .first()
    )
    if not handover or not handover.claim:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handover not found.")
    if handover.claim.claimant_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return handover, handover.item


def _record_item_return_for_handover(
    db: Session,
    *,
    handover: Handover,
    item: Item,
    claim: Claim,
) -> ItemReturn:
    """Create/update ItemReturn when authority handover completes (V5 flow)."""
    existing = (
        db.query(ItemReturn)
        .filter(ItemReturn.handover_id == handover.id)
        .first()
    )
    if existing and existing.returned_at:
        return existing

    now = datetime.now(timezone.utc)
    potential_match_id: uuid.UUID | None = None
    lost_item_id = item.id

    if claim.claim_path == ClaimPath.A:
        match = (
            db.query(PotentialMatch)
            .join(Item, PotentialMatch.lost_item_id == Item.id)
            .filter(
                PotentialMatch.found_item_id == item.id,
                Item.posted_by_id == claim.claimant_user_id,
            )
            .order_by(PotentialMatch.created_at.desc())
            .first()
        )
        if match:
            potential_match_id = match.id
            lost_item_id = match.lost_item_id

    if existing:
        record = existing
    else:
        record = ItemReturn(
            university_id=item.university_id,
            potential_match_id=potential_match_id,
            lost_item_id=lost_item_id,
            found_item_id=item.id,
            lost_owner_id=claim.claimant_user_id,
            found_owner_id=item.posted_by_id,
            handover_id=handover.id,
        )
        db.add(record)

    record.returned_at = now
    record.method = ReturnMethod.HANDOVER
    record.dispute_window_ends_at = now + timedelta(days=RETURN_WINDOW_DAYS)
    record.owner_received_at = handover.owner_confirmed_at or now
    record.finder_handed_over_at = item.authority_received_at or handover.created_at

    if lost_item_id != item.id:
        lost = db.query(Item).filter(Item.id == lost_item_id).first()
        if lost and lost.status != ItemStatus.RETURNED:
            lost.status = ItemStatus.RETURNED
            lost.updated_at = now

    if potential_match_id:
        match = db.query(PotentialMatch).filter(PotentialMatch.id == potential_match_id).first()
        if match and match.status != PotentialMatchStatus.EXPIRED:
            match.status = PotentialMatchStatus.EXPIRED

    db.flush()
    return record


def _finalize_handover(db: Session, handover: Handover, item: Item) -> None:
    if item.status == ItemStatus.RETURNED:
        return
    if not handover.claim:
        db.refresh(handover, attribute_names=["claim"])
    claim = handover.claim
    now = datetime.now(timezone.utc)
    item.status = ItemStatus.RETURNED
    item.updated_at = now
    token_service.award_item_claimed(db, item)
    _record_item_return_for_handover(db, handover=handover, item=item, claim=claim)
    notification_service.notify_handover_completed(
        db,
        claimant_id=handover.claim.claimant_user_id,
        item_id=item.id,
        handover_id=handover.id,
        owner_confirmed=handover.owner_confirmed,
        authority_override=bool(handover.authority_override_note),
    )
    if item.drop_point:
        from app.services import authority_notification_service

        authority_notification_service.notify_authority_handover_complete(
            db,
            item=item,
            drop_point=item.drop_point,
            handover_id=handover.id,
        )
    if item.posted_by_id:
        notification_service.notify_finder_handover_complete(
            db,
            finder_id=item.posted_by_id,
            item_id=item.id,
            handover_id=handover.id,
        )


def list_handover_queue(db: Session, authority: Authority) -> HandoverQueueResponse:
    claims = (
        db.query(Claim)
        .options(joinedload(Claim.claimant), joinedload(Claim.found_item))
        .join(Item, Claim.found_item_id == Item.id)
        .filter(
            Item.drop_point_id == authority.drop_point_id,
            Claim.status == _VERIFIED,
        )
        .order_by(Claim.created_at.desc())
        .all()
    )

    handover_by_claim: dict[uuid.UUID, Handover] = {}
    claim_ids = [c.id for c in claims]
    if claim_ids:
        handover_by_claim = {
            h.claim_id: h
            for h in db.query(Handover).filter(Handover.claim_id.in_(claim_ids)).all()
        }

    items: list[HandoverQueueItem] = []
    seen_claim_ids: set[uuid.UUID] = set()

    for claim in claims:
        handover = handover_by_claim.get(claim.id)
        status_key = _handover_status(handover)
        seen_claim_ids.add(claim.id)
        completed_at = None
        if handover and status_key == "completed":
            completed_at = handover.owner_confirmed_at or handover.created_at
        items.append(
            HandoverQueueItem(
                claim_id=claim.id,
                handover_id=handover.id if handover else None,
                found_item_id=claim.found_item_id,
                found_item_description=claim.found_item.public_description,
                found_item_category=claim.found_item.category.value,
                claimant_name=handover.claimant_name if handover else (claim.claimant.full_name or claim.claimant.username),
                queue_status=status_key,
                owner_confirmed=handover.owner_confirmed if handover else False,
                authority_override=bool(handover.authority_override_note) if handover else False,
                condition_photo_url=handover.condition_photo_url if handover else None,
                created_at=handover.created_at if handover else None,
                completed_at=completed_at,
            )
        )

    completed_handovers = (
        db.query(Handover)
        .join(Item, Handover.item_id == Item.id)
        .options(joinedload(Handover.claim).joinedload(Claim.claimant), joinedload(Handover.item))
        .filter(
            Item.drop_point_id == authority.drop_point_id,
            or_(
                Handover.owner_confirmed.is_(True),
                Handover.authority_override_note.isnot(None),
            ),
        )
        .order_by(Handover.created_at.desc())
        .limit(200)
        .all()
    )
    for handover in completed_handovers:
        if handover.claim_id in seen_claim_ids:
            continue
        claim = handover.claim
        item = handover.item
        if not claim or not item:
            continue
        items.append(
            HandoverQueueItem(
                claim_id=handover.claim_id,
                handover_id=handover.id,
                found_item_id=item.id,
                found_item_description=item.public_description,
                found_item_category=item.category.value,
                claimant_name=handover.claimant_name,
                queue_status="completed",
                owner_confirmed=handover.owner_confirmed,
                authority_override=bool(handover.authority_override_note),
                condition_photo_url=handover.condition_photo_url,
                created_at=handover.created_at,
                completed_at=handover.owner_confirmed_at or handover.created_at,
            )
        )

    return HandoverQueueResponse(items=items)


def start_handover(
    db: Session,
    authority: Authority,
    claim_id: uuid.UUID,
    payload: HandoverStartRequest,
) -> HandoverStartResponse:
    claim = _get_scoped_claim_for_authority(db, authority, claim_id)
    if claim.status != _VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only verified claims can begin handover.",
        )

    existing = db.query(Handover).filter(Handover.claim_id == claim_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Handover has already been started for this claim.",
        )

    item = claim.found_item
    if item.status == ItemStatus.RETURNED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This item has already been returned.",
        )

    phone_enc = encrypt(payload.claimant_phone.strip())
    student_enc = (
        encrypt(payload.claimant_student_id.strip())
        if payload.claimant_student_id
        else None
    )

    handover = Handover(
        claim_id=claim.id,
        item_id=item.id,
        condition_photo_url=payload.condition_photo_url.strip(),
        claimant_name=payload.claimant_name.strip(),
        claimant_phone_encrypted=phone_enc,
        claimant_student_id_encrypted=student_enc,
        claimant_photo_url=payload.claimant_photo_url,
        owner_confirmed=False,
    )
    db.add(handover)
    db.flush()

    notification_service.notify_handover_awaiting_owner(
        db,
        claimant_id=claim.claimant_user_id,
        handover_id=handover.id,
        item_id=item.id,
    )

    detail = _build_authority_detail(handover, item)
    return HandoverStartResponse(
        message="Handover recorded. Waiting for the owner's digital confirmation.",
        handover=detail,
    )


def get_handover_for_authority(
    db: Session,
    authority: Authority,
    handover_id: uuid.UUID,
) -> HandoverAuthorityDetail:
    handover, item = _get_scoped_handover_for_authority(db, authority, handover_id)
    return _build_authority_detail(handover, item, claim=handover.claim)


def override_handover(
    db: Session,
    authority: Authority,
    handover_id: uuid.UUID,
    payload: HandoverOverrideRequest,
) -> HandoverAuthorityDetail:
    handover, item = _get_scoped_handover_for_authority(db, authority, handover_id)
    if _is_complete(handover):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This handover is already complete.",
        )

    handover.authority_override_note = payload.note.strip()
    db.flush()
    _finalize_handover(db, handover, item)
    from app.services.admin_dashboard_service import log_actor_action

    log_actor_action(
        db,
        action=AdminActionType.HANDOVER_OVERRIDE,
        target_type="handover",
        target_id=handover.id,
        authority_id=authority.id,
        detail={
            "item_id": str(handover.item_id),
            "claim_id": str(handover.claim_id),
            "note": handover.authority_override_note,
        },
    )
    if item.drop_point:
        from app.services import admin_notification_service

        admin_notification_service.notify_admins_handover_override(
            db,
            handover_id=handover.id,
            item_id=item.id,
            drop_point_name=item.drop_point.name,
        )
    db.refresh(handover)
    return _build_authority_detail(handover, item, claim=handover.claim)


def get_handover_for_supervisor(
    db: Session,
    supervisor,
    handover_id: uuid.UUID,
) -> HandoverAuthorityDetail:
    from app.services import supervisor_service

    handover = (
        db.query(Handover)
        .options(
            joinedload(Handover.claim),
            joinedload(Handover.item).joinedload(Item.drop_point),
        )
        .filter(Handover.id == handover_id)
        .first()
    )
    if not handover or not handover.item or handover.item.drop_point_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Handover not found.")
    supervisor_service.assert_drop_point_in_scope(supervisor, handover.item.drop_point_id)
    return _build_authority_detail(handover, handover.item, claim=handover.claim)


def get_handover_for_owner(
    db: Session,
    user: User,
    handover_id: uuid.UUID,
) -> HandoverOwnerResponse:
    handover, item = _get_scoped_handover_for_owner(db, user, handover_id)
    complete = _is_complete(handover)
    return HandoverOwnerResponse(
        id=handover.id,
        item_id=handover.item_id,
        condition_photo_url=handover.condition_photo_url,
        claimant_name=handover.claimant_name,
        owner_confirmed=handover.owner_confirmed,
        owner_confirmed_at=handover.owner_confirmed_at,
        authority_override=bool(handover.authority_override_note),
        found_item_description=item.public_description,
        found_item_category=item.category.value,
        can_confirm=not complete and not handover.owner_confirmed,
    )


def confirm_handover(
    db: Session,
    user: User,
    handover_id: uuid.UUID,
) -> HandoverConfirmResponse:
    handover, item = _get_scoped_handover_for_owner(db, user, handover_id)
    if handover.authority_override_note:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This handover was already completed by the authority.",
        )
    if handover.owner_confirmed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already confirmed this handover.",
        )

    now = datetime.now(timezone.utc)
    handover.owner_confirmed = True
    handover.owner_confirmed_at = now
    db.flush()
    _finalize_handover(db, handover, item)
    db.refresh(item)

    return HandoverConfirmResponse(
        message="Thank you — your confirmation has been recorded. This item is now marked as returned.",
        handover_id=handover.id,
        item_status=item.status.value,
    )

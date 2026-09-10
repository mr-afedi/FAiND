"""
Authority claim review — comparison dashboard (Section 8.5, W9).
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from datetime import datetime, timezone

from app.models.authority import Authority
from app.models.claim import Claim, ClaimStatus
from app.models.item import Item, ItemStatus, ItemType
from app.models.admin_log import AdminActionType
from app.schemas.authority import (
    AuthorityClaimActionResponse,
    AuthorityClaimDetail,
    AuthorityClaimItemSummary,
    AuthorityClaimsComparisonResponse,
    AuthorityClaimsListResponse,
)
from app.schemas.messaging import InquirySummary
from app.services import messaging_service, notification_service

_PENDING = ClaimStatus.PENDING
_VERIFIED = ClaimStatus.VERIFIED
_REJECTED = ClaimStatus.REJECTED


def _get_scoped_found_item(
    db: Session,
    authority: Authority,
    found_item_id: uuid.UUID,
) -> Item:
    item = (
        db.query(Item)
        .filter(Item.id == found_item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item or item.drop_point_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    if item.drop_point_id != authority.drop_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This item belongs to a different drop point.",
        )
    return item


def _get_scoped_claim(
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


def _build_claim_detail(
    claim: Claim,
    inquiry: InquirySummary | None = None,
) -> AuthorityClaimDetail:
    user = claim.claimant
    return AuthorityClaimDetail(
        id=claim.id,
        claim_path=claim.claim_path.value,
        status=claim.status.value,
        photo_url=claim.photo_url,
        date_lost=claim.date_lost,
        time_lost=claim.time_lost,
        description=claim.description,
        lost_location=claim.lost_location,
        ai_confidence_score=claim.ai_confidence_score,
        created_at=claim.created_at,
        claimant_name=user.full_name or user.username,
        claimant_email=user.email,
        student_id=user.student_id,
        inquiry=inquiry,
    )


def _build_comparison(db: Session, item: Item, claims: list[Claim]) -> AuthorityClaimsComparisonResponse:
    hours = item.drop_point.operating_hours if item.drop_point else None
    summaries = messaging_service.inquiry_summaries_for_claims(
        db,
        [c.id for c in claims],
        operating_hours=hours,
    )
    return AuthorityClaimsComparisonResponse(
        found_item_id=item.id,
        found_item_status=item.status.value,
        found_item_category=item.category.value,
        found_item_description=item.public_description,
        found_item_image_urls=item.image_urls or [],
        drop_point_operating_hours=hours,
        claims=[_build_claim_detail(c, summaries.get(c.id)) for c in claims],
    )


def _load_claims_for_item(db: Session, found_item_id: uuid.UUID) -> list[Claim]:
    return (
        db.query(Claim)
        .options(joinedload(Claim.claimant))
        .filter(Claim.found_item_id == found_item_id)
        .order_by(Claim.created_at.asc())
        .all()
    )


def list_claim_items(db: Session, authority: Authority) -> AuthorityClaimsListResponse:
    """Found items at this drop point that have at least one claim."""
    rows = (
        db.query(
            Item,
            func.count(Claim.id).label("claim_count"),
            func.count(Claim.id).filter(Claim.status == _PENDING).label("pending_count"),
        )
        .join(Claim, Claim.found_item_id == Item.id)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id == authority.drop_point_id,
            Item.status != ItemStatus.RETURNED,
        )
        .group_by(Item.id)
        .order_by(func.max(Claim.created_at).desc())
        .all()
    )
    items = [
        AuthorityClaimItemSummary(
            found_item_id=item.id,
            found_item_status=item.status.value,
            found_item_category=item.category.value,
            found_item_description=item.public_description,
            claim_count=int(claim_count),
            pending_count=int(pending_count),
        )
        for item, claim_count, pending_count in rows
    ]
    return AuthorityClaimsListResponse(items=items)


def get_claims_for_item(
    db: Session,
    authority: Authority,
    found_item_id: uuid.UUID,
) -> AuthorityClaimsComparisonResponse:
    item = _get_scoped_found_item(db, authority, found_item_id)
    claims = _load_claims_for_item(db, found_item_id)
    return _build_comparison(db, item, claims)


def call_to_collect(
    db: Session,
    authority: Authority,
    claim_id: uuid.UUID,
) -> AuthorityClaimActionResponse:
    claim = _get_scoped_claim(db, authority, claim_id)
    if claim.status != _PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending claims can be called to collect.",
        )

    drop_point = authority.drop_point
    notification_service.notify_claim_call_to_collect(
        db,
        claimant_id=claim.claimant_user_id,
        found_item_id=claim.found_item_id,
        claim_id=claim.id,
        drop_point=drop_point,
    )
    db.flush()

    item = _get_scoped_found_item(db, authority, claim.found_item_id)
    claims = _load_claims_for_item(db, claim.found_item_id)
    return AuthorityClaimActionResponse(
        message="Claimant notified to come and collect.",
        comparison=_build_comparison(db, item, claims),
    )


def verify_claim(
    db: Session,
    authority: Authority,
    claim_id: uuid.UUID,
) -> AuthorityClaimActionResponse:
    claim = _get_scoped_claim(db, authority, claim_id)
    if claim.status != _PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending claims can be verified.",
        )

    claim.status = _VERIFIED
    found_item_id = claim.found_item_id

    siblings = (
        db.query(Claim)
        .options(joinedload(Claim.claimant))
        .filter(
            Claim.found_item_id == found_item_id,
            Claim.id != claim.id,
            Claim.status == _PENDING,
        )
        .all()
    )
    for sibling in siblings:
        sibling.status = _REJECTED
        sibling.rejected_at = datetime.now(timezone.utc)
        notification_service.notify_claim_rejected_other_verified(
            db,
            claimant_id=sibling.claimant_user_id,
            found_item_id=found_item_id,
            claim_id=sibling.id,
        )

    notification_service.notify_claim_verified(
        db,
        claimant_id=claim.claimant_user_id,
        found_item_id=found_item_id,
        claim_id=claim.id,
        drop_point=authority.drop_point,
    )
    from app.services.admin_dashboard_service import log_actor_action

    log_actor_action(
        db,
        action=AdminActionType.APPROVE_CLAIM,
        target_type="claim",
        target_id=claim.id,
        authority_id=authority.id,
        detail={
            "found_item_id": str(found_item_id),
            "claim_path": claim.claim_path.value,
            "rejected_sibling_count": len(siblings),
        },
    )
    db.flush()

    item = _get_scoped_found_item(db, authority, found_item_id)
    claims = _load_claims_for_item(db, found_item_id)
    return AuthorityClaimActionResponse(
        message="Claimant verified as owner. Other pending claims were rejected.",
        comparison=_build_comparison(db, item, claims),
    )


def reject_claim(
    db: Session,
    authority: Authority,
    claim_id: uuid.UUID,
) -> AuthorityClaimActionResponse:
    claim = _get_scoped_claim(db, authority, claim_id)
    if claim.status != _PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending claims can be rejected.",
        )

    claim.status = _REJECTED
    claim.rejected_at = datetime.now(timezone.utc)
    notification_service.notify_claim_rejected_manual(
        db,
        claimant_id=claim.claimant_user_id,
        found_item_id=claim.found_item_id,
        claim_id=claim.id,
    )
    from app.services.admin_dashboard_service import log_actor_action

    log_actor_action(
        db,
        action=AdminActionType.REJECT_CLAIM,
        target_type="claim",
        target_id=claim.id,
        authority_id=authority.id,
        detail={
            "found_item_id": str(claim.found_item_id),
            "claim_path": claim.claim_path.value,
        },
    )
    db.flush()

    item = _get_scoped_found_item(db, authority, claim.found_item_id)
    claims = _load_claims_for_item(db, claim.found_item_id)
    return AuthorityClaimActionResponse(
        message="Claim rejected.",
        comparison=_build_comparison(db, item, claims),
    )


def reply_to_inquiry(
    db: Session,
    authority: Authority,
    inquiry_id: uuid.UUID,
    reply_type: str,
) -> AuthorityClaimActionResponse:
    inquiry = messaging_service.reply_to_inquiry(db, authority, inquiry_id, reply_type)
    found_item_id = inquiry.claim.found_item_id
    item = _get_scoped_found_item(db, authority, found_item_id)
    claims = _load_claims_for_item(db, found_item_id)
    return AuthorityClaimActionResponse(
        message="Reply sent to claimant.",
        comparison=_build_comparison(db, item, claims),
    )

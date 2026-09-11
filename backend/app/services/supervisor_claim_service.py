"""
Supervisor claim actions — scoped to assigned drop points (Section 15.2).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.admin_log import AdminActionType
from app.models.claim import Claim, ClaimStatus
from app.models.item import Item, ItemType
from app.models.supervisor import Supervisor
from app.schemas.authority import AuthorityClaimActionResponse
from app.services import authority_claim_service, messaging_service, notification_service, supervisor_service
from app.services.admin_dashboard_service import log_actor_action

_PENDING = ClaimStatus.PENDING
_VERIFIED = ClaimStatus.VERIFIED
_REJECTED = ClaimStatus.REJECTED


def _get_scoped_claim(db: Session, supervisor: Supervisor, claim_id: uuid.UUID) -> Claim:
    claim = (
        db.query(Claim)
        .options(
            joinedload(Claim.claimant),
            joinedload(Claim.found_item).joinedload(Item.drop_point),
        )
        .filter(Claim.id == claim_id)
        .first()
    )
    if not claim or not claim.found_item or claim.found_item.drop_point_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")
    supervisor_service.assert_drop_point_in_scope(supervisor, claim.found_item.drop_point_id)
    return claim


def _get_scoped_item(db: Session, supervisor: Supervisor, found_item_id: uuid.UUID) -> Item:
    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(Item.id == found_item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item or item.drop_point_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    supervisor_service.assert_drop_point_in_scope(supervisor, item.drop_point_id)
    return item


def call_claim_to_collect(
    db: Session,
    supervisor: Supervisor,
    claim_id: uuid.UUID,
) -> AuthorityClaimActionResponse:
    claim = _get_scoped_claim(db, supervisor, claim_id)
    if claim.status != _PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending claims can be called to collect.",
        )
    drop_point = claim.found_item.drop_point
    notification_service.notify_claim_call_to_collect(
        db,
        claimant_id=claim.claimant_user_id,
        found_item_id=claim.found_item_id,
        claim_id=claim.id,
        drop_point=drop_point,
    )
    db.flush()
    item = _get_scoped_item(db, supervisor, claim.found_item_id)
    claims = authority_claim_service._load_claims_for_item(db, claim.found_item_id)
    return AuthorityClaimActionResponse(
        message="Claimant notified to come and collect.",
        comparison=authority_claim_service._build_comparison(db, item, claims),
    )


def verify_claim(
    db: Session,
    supervisor: Supervisor,
    claim_id: uuid.UUID,
) -> AuthorityClaimActionResponse:
    claim = _get_scoped_claim(db, supervisor, claim_id)
    if claim.status != _PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only pending claims can be verified.",
        )

    claim.status = _VERIFIED
    found_item_id = claim.found_item_id
    drop_point = claim.found_item.drop_point

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
        drop_point=drop_point,
    )
    log_actor_action(
        db,
        action=AdminActionType.APPROVE_CLAIM,
        target_type="claim",
        target_id=claim.id,
        detail={
            "found_item_id": str(found_item_id),
            "claim_path": claim.claim_path.value,
            "rejected_sibling_count": len(siblings),
            "resolved_by": "supervisor",
            "supervisor_id": str(supervisor.id),
        },
    )
    db.flush()

    item = _get_scoped_item(db, supervisor, found_item_id)
    claims = authority_claim_service._load_claims_for_item(db, found_item_id)
    return AuthorityClaimActionResponse(
        message="Claimant verified as owner. Other pending claims were rejected.",
        comparison=authority_claim_service._build_comparison(db, item, claims),
    )


def reject_claim(
    db: Session,
    supervisor: Supervisor,
    claim_id: uuid.UUID,
) -> AuthorityClaimActionResponse:
    claim = _get_scoped_claim(db, supervisor, claim_id)
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
    log_actor_action(
        db,
        action=AdminActionType.REJECT_CLAIM,
        target_type="claim",
        target_id=claim.id,
        detail={
            "found_item_id": str(claim.found_item_id),
            "claim_path": claim.claim_path.value,
            "resolved_by": "supervisor",
            "supervisor_id": str(supervisor.id),
        },
    )
    db.flush()

    item = _get_scoped_item(db, supervisor, claim.found_item_id)
    claims = authority_claim_service._load_claims_for_item(db, claim.found_item_id)
    return AuthorityClaimActionResponse(
        message="Claim rejected.",
        comparison=authority_claim_service._build_comparison(db, item, claims),
    )


def reply_to_inquiry(
    db: Session,
    supervisor: Supervisor,
    inquiry_id: uuid.UUID,
    reply_type: str,
) -> AuthorityClaimActionResponse:
    from app.models.authority import Authority
    from app.models.claim_inquiry import ClaimInquiry

    inquiry = (
        db.query(ClaimInquiry)
        .options(
            joinedload(ClaimInquiry.claim)
            .joinedload(Claim.found_item)
            .joinedload(Item.drop_point),
        )
        .filter(ClaimInquiry.id == inquiry_id)
        .first()
    )
    if not inquiry or not inquiry.claim or not inquiry.claim.found_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inquiry not found.")
    supervisor_service.assert_drop_point_in_scope(
        supervisor, inquiry.claim.found_item.drop_point_id
    )

    authority = (
        db.query(Authority)
        .filter(
            Authority.drop_point_id == inquiry.claim.found_item.drop_point_id,
            Authority.is_active.is_(True),
        )
        .first()
    )
    if not authority:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No active authority at this drop point to send the reply.",
        )

    inquiry = messaging_service.reply_to_inquiry(db, authority, inquiry_id, reply_type)
    found_item_id = inquiry.claim.found_item_id
    item = _get_scoped_item(db, supervisor, found_item_id)
    claims = authority_claim_service._load_claims_for_item(db, found_item_id)
    return AuthorityClaimActionResponse(
        message="Reply sent to claimant.",
        comparison=authority_claim_service._build_comparison(db, item, claims),
    )


def escalate_dispute(
    db: Session,
    supervisor: Supervisor,
    found_item_id: uuid.UUID,
    note: str,
) -> dict:
    item = _get_scoped_item(db, supervisor, found_item_id)
    note = note.strip()
    if len(note) < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Escalation note must be at least 10 characters.",
        )
    from app.services import admin_notification_service

    admin_notification_service.notify_all_admins(
        db,
        title="Claim dispute escalated by supervisor",
        body=(
            f"Supervisor {supervisor.email} escalated a multi-claim dispute on "
            f"\"{item.public_description[:100]}\" at {item.drop_point.name if item.drop_point else 'drop point'}. "
            f"Note: {note[:500]}"
        ),
        link=f"admin:claims:{found_item_id}",
        reference_id=found_item_id,
    )
    return {"message": "Dispute escalated to Root Admin for review."}

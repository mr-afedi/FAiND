"""
AdminDashboardService — Feature R (Section 26).

Central admin operations: analytics, users, claims, disputes, posts, audit logs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.admin_log import AdminLog, AdminActionType
from app.models.item import Item, ItemStatus, ItemType
from app.models.item_return import ItemReturn
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.conversation import Conversation, ConversationStatus
from app.models.user import User, UserRole, AccountStatus
from app.models.report import PostReport, UserReport, ReportStatus
from app.models.verification_attempt import VerificationAttempt, VerificationResult
from app.models.ihave_this_item_claim import IHaveThisItemClaim
from app.models.this_might_be_mine_claim import ThisMightBeMineClaim
from app.services import (
    notification_service,
    matching_service,
    fraud_service,
    trust_service,
)
from app.services.trust_service import get_trust_tier

MAX_ASSISTANT_ADMINS = 2


def _now() -> datetime:
    return datetime.now(timezone.utc)


def log_action(
    db: Session,
    *,
    admin: User,
    action: AdminActionType,
    target_type: str,
    target_id: uuid.UUID | None = None,
    detail: dict | None = None,
) -> AdminLog:
    entry = AdminLog(
        admin_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
    )
    db.add(entry)
    db.flush()
    return entry


def get_platform_analytics(db: Session) -> dict:
    lost = db.query(func.count(Item.id)).filter(Item.item_type == ItemType.LOST).scalar() or 0
    found = db.query(func.count(Item.id)).filter(Item.item_type == ItemType.FOUND).scalar() or 0
    returned = (
        db.query(func.count(ItemReturn.id))
        .filter(ItemReturn.returned_at.isnot(None))
        .scalar()
        or 0
    )
    denom = lost + found
    return_rate = round((returned / denom) * 100, 1) if denom else 0.0

    claims_pending = (
        db.query(func.count(PotentialMatch.id))
        .filter(PotentialMatch.status == PotentialMatchStatus.PENDING_REVIEW)
        .scalar()
        or 0
    )
    disputes_open = len(list_disputes_queue(db, limit=200))
    reports_pending = (
        db.query(func.count(PostReport.id)).filter(PostReport.status == ReportStatus.PENDING).scalar()
        or 0
    ) + (
        db.query(func.count(UserReport.id)).filter(UserReport.status == ReportStatus.PENDING).scalar()
        or 0
    )
    fraud_alerts = len(fraud_service.list_fraud_alerts(db, limit=50))

    week_ago = _now() - timedelta(days=7)
    month_ago = _now() - timedelta(days=30)
    active_7d = (
        db.query(func.count(func.distinct(Item.posted_by_id)))
        .filter(Item.created_at >= week_ago)
        .scalar()
        or 0
    )
    active_30d = (
        db.query(func.count(func.distinct(Item.posted_by_id)))
        .filter(Item.created_at >= month_ago)
        .scalar()
        or 0
    )

    users = db.query(User.trust_score).filter(User.status == AccountStatus.ACTIVE).all()
    dist = {
        "new_member": 0,
        "trusted_member": 0,
        "reliable_member": 0,
        "community_champion": 0,
    }
    tier_map = {
        "New Member": "new_member",
        "Trusted Member": "trusted_member",
        "Reliable Member": "reliable_member",
        "Community Champion": "community_champion",
    }
    for (score,) in users:
        key = tier_map.get(get_trust_tier(score or 0), "new_member")
        dist[key] += 1

    return {
        "total_lost_items": lost,
        "total_found_items": found,
        "total_returned": returned,
        "return_rate_percent": return_rate,
        "claims_pending_review": claims_pending,
        "disputes_open": disputes_open,
        "reports_pending": reports_pending,
        "fraud_alerts": fraud_alerts,
        "active_users_7d": active_7d,
        "active_users_30d": active_30d,
        "trust_distribution": dist,
    }


def list_admin_users(
    db: Session,
    *,
    search: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    q = db.query(User).order_by(User.created_at.desc())
    if search:
        term = f"%{search.strip().lower()}%"
        q = q.filter(
            or_(
                func.lower(User.email).like(term),
                func.lower(User.username).like(term),
                func.lower(User.full_name).like(term),
            )
        )
    total = q.count()
    rows = q.offset(offset).limit(min(limit, 200)).all()
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role.value,
                "status": u.status.value,
                "trust_score": u.trust_score,
                "fraud_risk_score": u.fraud_risk_score,
                "created_at": u.created_at,
                "suspended_at": u.suspended_at,
            }
            for u in rows
        ],
        "total": total,
    }


def suspend_user(db: Session, user_id: uuid.UUID, admin: User, reason: str | None = None) -> User:
    from app.services import suspension_service

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return suspension_service.suspend_user(
        db,
        target,
        admin,
        reason=reason,
        log_action=log_action,
    )


def unsuspend_user(db: Session, user_id: uuid.UUID, admin: User) -> User:
    from app.services import suspension_service

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return suspension_service.unsuspend_user(
        db,
        target,
        admin,
        log_action=log_action,
    )


def list_claims_queue(db: Session, limit: int = 50) -> list[dict]:
    matches = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(PotentialMatch.status == PotentialMatchStatus.PENDING_REVIEW)
        .order_by(PotentialMatch.created_at.asc())
        .limit(min(limit, 100))
        .all()
    )
    items: list[dict] = []
    for m in matches:
        path = "path_a"
        claimant_id = m.lost_item.posted_by_id if m.lost_item else None
        claimant_name = ""
        claim = (
            db.query(IHaveThisItemClaim)
            .filter(IHaveThisItemClaim.potential_match_id == m.id)
            .order_by(IHaveThisItemClaim.created_at.desc())
            .first()
        )
        if claim:
            path = "path_b"
            claimant_id = claim.user_id
            u = db.query(User).filter(User.id == claim.user_id).first()
            claimant_name = u.full_name if u else ""
        else:
            c_claim = (
                db.query(ThisMightBeMineClaim)
                .filter(ThisMightBeMineClaim.potential_match_id == m.id)
                .order_by(ThisMightBeMineClaim.created_at.desc())
                .first()
            )
            if c_claim:
                path = "path_c"
                claimant_id = c_claim.user_id
                u = db.query(User).filter(User.id == c_claim.user_id).first()
                claimant_name = u.full_name if u else ""
            else:
                attempt = (
                    db.query(VerificationAttempt)
                    .filter(
                        VerificationAttempt.potential_match_id == m.id,
                        VerificationAttempt.result == VerificationResult.REVIEW,
                    )
                    .order_by(VerificationAttempt.created_at.desc())
                    .first()
                )
                if attempt:
                    claimant_id = attempt.user_id
                    u = db.query(User).filter(User.id == attempt.user_id).first()
                    claimant_name = u.full_name if u else ""

        items.append(
            {
                "match_id": m.id,
                "path": path,
                "ownership_score": m.match_score,
                "match_score": m.match_score,
                "status": m.status.value,
                "created_at": m.created_at,
                "claimant_id": claimant_id,
                "claimant_name": claimant_name,
                "lost_item_id": m.lost_item_id,
                "found_item_id": m.found_item_id,
                "lost_description": m.lost_item.public_description if m.lost_item else "",
                "found_description": m.found_item.public_description if m.found_item else "",
                "score_breakdown": m.score_breakdown or {},
            }
        )
    return items


def approve_claim(db: Session, match_id: uuid.UUID, admin: User) -> dict:
    match = (
        db.query(PotentialMatch)
        .options(joinedload(PotentialMatch.lost_item), joinedload(PotentialMatch.found_item))
        .filter(PotentialMatch.id == match_id)
        .first()
    )
    if not match or match.status != PotentialMatchStatus.PENDING_REVIEW:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not in review queue.")

    now = _now()
    match.status = PotentialMatchStatus.VERIFIED
    if match.lost_item:
        match.lost_item.status = ItemStatus.POTENTIAL_MATCH
        match.lost_item.updated_at = now

    conv = (
        db.query(Conversation)
        .filter(Conversation.potential_match_id == match.id)
        .first()
    )
    if not conv:
        conv = Conversation(
            university_id=match.university_id,
            potential_match_id=match.id,
            lost_item_id=match.lost_item_id,
            found_item_id=match.found_item_id,
            lost_owner_id=match.lost_item.posted_by_id,
            found_owner_id=match.found_item.posted_by_id,
            status=ConversationStatus.UNLOCKED,
            unlocked_at=now,
        )
        db.add(conv)
        db.flush()

    notification_service.notify_verification_passed(
        db,
        lost_owner_id=match.lost_item.posted_by_id,
        found_owner_id=match.found_item.posted_by_id,
        match_id=match.id,
        conversation_id=conv.id,
        lost_item_id=match.lost_item_id,
        found_item_id=match.found_item_id,
    )
    matching_service.expire_superseded_matches(db, match.lost_item_id, match.id)
    log_action(
        db,
        admin=admin,
        action=AdminActionType.APPROVE_CLAIM,
        target_type="potential_match",
        target_id=match.id,
        detail={
            "status_before": PotentialMatchStatus.PENDING_REVIEW.value,
            "status_after": PotentialMatchStatus.VERIFIED.value,
        },
    )
    db.commit()
    return {"success": True, "message": "Claim approved. Chat unlocked for both parties."}


def request_more_info_claim(
    db: Session, match_id: uuid.UUID, admin: User, note: str
) -> dict:
    match = (
        db.query(PotentialMatch)
        .options(joinedload(PotentialMatch.lost_item))
        .filter(PotentialMatch.id == match_id)
        .first()
    )
    if not match or match.status != PotentialMatchStatus.PENDING_REVIEW:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not in review queue.")

    note = note.strip()
    if len(note) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least 10 characters.",
        )

    log_action(
        db,
        admin=admin,
        action=AdminActionType.REQUEST_MORE_INFO,
        target_type="potential_match",
        target_id=match.id,
        detail={"note": note, "status_before": match.status.value},
    )
    db.commit()
    return {
        "success": True,
        "message": "Request for more information logged. Claim remains in review queue.",
    }


def reject_claim(
    db: Session, match_id: uuid.UUID, admin: User, note: str | None = None
) -> dict:
    match = (
        db.query(PotentialMatch)
        .options(joinedload(PotentialMatch.lost_item))
        .filter(PotentialMatch.id == match_id)
        .first()
    )
    if not match or match.status != PotentialMatchStatus.PENDING_REVIEW:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not in review queue.")

    status_before = match.status.value
    match.status = PotentialMatchStatus.ACTIVE
    if match.lost_item and match.lost_item.status == ItemStatus.UNDER_VERIFICATION:
        match.lost_item.status = ItemStatus.POTENTIAL_MATCH

    log_action(
        db,
        admin=admin,
        action=AdminActionType.REJECT_CLAIM,
        target_type="potential_match",
        target_id=match.id,
        detail={
            "note": note or "",
            "status_before": status_before,
            "status_after": match.status.value,
        },
    )
    db.commit()
    return {"success": True, "message": "Claim rejected. The claimant may try again if attempts remain."}


def list_disputes_queue(db: Session, limit: int = 50) -> list[dict]:
    items: list[dict] = []
    seen_keys: set[str] = set()

    return_rows = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.dispute_filed_at.isnot(None),
            ItemReturn.dispute_resolved_at.is_(None),
        )
        .order_by(ItemReturn.dispute_filed_at.asc())
        .limit(min(limit, 100))
        .all()
    )
    for r in return_rows:
        key = f"return:{r.id}"
        seen_keys.add(key)
        lost_owner = db.query(User).filter(User.id == r.lost_owner_id).first()
        found_owner = db.query(User).filter(User.id == r.found_owner_id).first()
        filed_by = (
            db.query(User).filter(User.id == r.dispute_filed_by_id).first()
            if r.dispute_filed_by_id
            else None
        )
        lost_item = db.query(Item).filter(Item.id == r.lost_item_id).first()
        label = lost_item.public_description[:80] if lost_item else "Return dispute"
        items.append(
            {
                "dispute_id": r.id,
                "dispute_type": "return",
                "return_id": r.id,
                "match_id": r.potential_match_id,
                "returned_at": r.returned_at,
                "dispute_filed_at": r.dispute_filed_at,
                "dispute_reason": r.dispute_reason or "",
                "filed_by_id": r.dispute_filed_by_id,
                "filed_by_name": filed_by.full_name if filed_by else "Unknown",
                "lost_owner_name": lost_owner.full_name if lost_owner else "",
                "found_owner_name": found_owner.full_name if found_owner else "",
                "tip_frozen": r.tip_frozen,
                "item_label": label,
            }
        )

    manual_rows = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.admin_review_flagged.is_(True),
            ItemReturn.dispute_filed_at.is_(None),
            ItemReturn.dispute_resolved_at.is_(None),
        )
        .order_by(ItemReturn.created_at.asc())
        .limit(min(limit, 100))
        .all()
    )
    for r in manual_rows:
        key = f"return:{r.id}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        lost_item = db.query(Item).filter(Item.id == r.lost_item_id).first()
        label = lost_item.public_description[:80] if lost_item else "Manual review"
        items.append(
            {
                "dispute_id": r.id,
                "dispute_type": "manual",
                "return_id": r.id,
                "match_id": r.potential_match_id,
                "returned_at": r.returned_at,
                "dispute_filed_at": None,
                "dispute_reason": "Flagged for admin review (unconfirmed return)",
                "filed_by_id": None,
                "filed_by_name": "System",
                "lost_owner_name": "",
                "found_owner_name": "",
                "tip_frozen": r.tip_frozen,
                "item_label": label,
            }
        )

    verification_matches = (
        db.query(PotentialMatch)
        .options(joinedload(PotentialMatch.lost_item))
        .filter(PotentialMatch.status == PotentialMatchStatus.PAUSED)
        .order_by(PotentialMatch.created_at.asc())
        .limit(min(limit, 100))
        .all()
    )
    for m in verification_matches:
        key = f"verification:{m.id}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        label = (
            m.lost_item.public_description[:80]
            if m.lost_item
            else "Verification dispute"
        )
        items.append(
            {
                "dispute_id": m.id,
                "dispute_type": "verification",
                "return_id": None,
                "match_id": m.id,
                "returned_at": None,
                "dispute_filed_at": m.created_at,
                "dispute_reason": "Multiple claimants exceeded approval threshold",
                "filed_by_id": None,
                "filed_by_name": "System",
                "lost_owner_name": "",
                "found_owner_name": "",
                "tip_frozen": False,
                "item_label": label,
            }
        )

    items.sort(
        key=lambda x: (
            x["dispute_filed_at"] or x.get("returned_at") or datetime.min.replace(tzinfo=timezone.utc)
        )
    )
    return items[: min(limit, 100)]


def resolve_dispute(
    db: Session,
    return_id: uuid.UUID,
    admin: User,
    *,
    outcome: str,
    note: str,
) -> dict:
    record = db.query(ItemReturn).filter(ItemReturn.id == return_id).first()
    if not record or record.dispute_resolved_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open dispute not found.")

    is_return_dispute = record.dispute_filed_at is not None
    is_manual_review = record.admin_review_flagged and not record.dispute_filed_at
    if not is_return_dispute and not is_manual_review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open dispute not found.")

    dispute_type = "return" if is_return_dispute else "manual"
    now = _now()
    record.dispute_resolved_at = now
    record.dispute_resolution_note = note.strip()
    record.dispute_resolved_by_id = admin.id
    record.admin_review_flagged = False
    if record.tip_frozen and outcome in ("approved", "rejected"):
        record.tip_frozen = False

    item_status_before: dict[str, str] = {}
    for item_id in (record.lost_item_id, record.found_item_id):
        item = db.query(Item).filter(Item.id == item_id).first()
        if item:
            item_status_before[str(item_id)] = item.status.value
        if item and item.status == ItemStatus.UNDER_DISPUTE:
            if record.returned_at:
                item.status = ItemStatus.RETURNED
            else:
                item.status = ItemStatus.POTENTIAL_MATCH
            item.updated_at = now
        matching_service.resume_matches_for_item(db, item_id)

    log_action(
        db,
        admin=admin,
        action=AdminActionType.RESOLVE_DISPUTE,
        target_type="item_return",
        target_id=record.id,
        detail={
            "dispute_type": dispute_type,
            "outcome": outcome,
            "note": note[:200],
            "item_status_before": item_status_before,
        },
    )
    db.commit()
    return {"success": True, "message": f"Dispute marked as {outcome.replace('_', ' ')}."}


def _claimant_ids_for_match(db: Session, match: PotentialMatch) -> tuple[uuid.UUID, uuid.UUID]:
    """Return (lost_owner_id, found_owner_id) for conversation wiring."""
    lost_owner_id = match.lost_item.posted_by_id if match.lost_item else None
    found_owner_id = match.found_item.posted_by_id if match.found_item else None

    claim_b = (
        db.query(IHaveThisItemClaim)
        .filter(IHaveThisItemClaim.potential_match_id == match.id)
        .order_by(IHaveThisItemClaim.created_at.desc())
        .first()
    )
    if claim_b:
        return lost_owner_id, claim_b.user_id

    claim_c = (
        db.query(ThisMightBeMineClaim)
        .filter(ThisMightBeMineClaim.potential_match_id == match.id)
        .order_by(ThisMightBeMineClaim.created_at.desc())
        .first()
    )
    if claim_c:
        return claim_c.user_id, found_owner_id or claim_c.user_id

    attempt = (
        db.query(VerificationAttempt)
        .filter(VerificationAttempt.potential_match_id == match.id)
        .order_by(VerificationAttempt.created_at.desc())
        .first()
    )
    if attempt:
        return attempt.user_id, found_owner_id or attempt.user_id

    return lost_owner_id, found_owner_id


def resolve_verification_dispute(
    db: Session,
    anchor_match_id: uuid.UUID,
    admin: User,
    *,
    winner_match_id: uuid.UUID,
    note: str,
) -> dict:
    note = note.strip()
    if len(note) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least 10 characters.",
        )

    anchor = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(PotentialMatch.id == anchor_match_id)
        .first()
    )
    if not anchor or not anchor.lost_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Verification dispute not found.",
        )

    lost_item = anchor.lost_item
    if lost_item.status != ItemStatus.UNDER_DISPUTE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item is not under verification dispute.",
        )

    group = (
        db.query(PotentialMatch)
        .options(joinedload(PotentialMatch.lost_item), joinedload(PotentialMatch.found_item))
        .filter(
            PotentialMatch.lost_item_id == lost_item.id,
            PotentialMatch.status.in_(
                (PotentialMatchStatus.PAUSED, PotentialMatchStatus.VERIFIED)
            ),
        )
        .all()
    )
    if len(group) < 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No open verification dispute for this match.",
        )

    winner = next((m for m in group if m.id == winner_match_id), None)
    if not winner:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Winner match is not part of this dispute.",
        )

    now = _now()
    losers = [m for m in group if m.id != winner_match_id]
    status_before = {str(m.id): m.status.value for m in group}

    for loser in losers:
        loser.status = PotentialMatchStatus.ACTIVE
        loser_conv = (
            db.query(Conversation)
            .filter(Conversation.potential_match_id == loser.id)
            .first()
        )
        if loser_conv:
            loser_conv.status = ConversationStatus.FROZEN

    winner.status = PotentialMatchStatus.VERIFIED
    lost_item.status = ItemStatus.POTENTIAL_MATCH
    lost_item.updated_at = now

    winner_conv = (
        db.query(Conversation)
        .filter(Conversation.potential_match_id == winner.id)
        .first()
    )
    if not winner_conv:
        lost_owner_id, found_owner_id = _claimant_ids_for_match(db, winner)
        if not lost_owner_id or not found_owner_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot resolve — missing party information on winning match.",
            )
        winner_conv = Conversation(
            university_id=lost_item.university_id,
            potential_match_id=winner.id,
            lost_item_id=lost_item.id,
            found_item_id=winner.found_item_id,
            lost_owner_id=lost_owner_id,
            found_owner_id=found_owner_id,
            status=ConversationStatus.UNLOCKED,
            unlocked_at=now,
        )
        db.add(winner_conv)
        db.flush()
        notification_service.notify_verification_passed(
            db,
            lost_owner_id=lost_owner_id,
            found_owner_id=found_owner_id,
            match_id=winner.id,
            conversation_id=winner_conv.id,
            lost_item_id=lost_item.id,
            found_item_id=winner.found_item_id,
        )
    else:
        winner_conv.status = ConversationStatus.UNLOCKED

    log_action(
        db,
        admin=admin,
        action=AdminActionType.RESOLVE_DISPUTE,
        target_type="potential_match",
        target_id=anchor_match_id,
        detail={
            "dispute_type": "verification",
            "winner_match_id": str(winner_match_id),
            "outcome": "resolved",
            "note": note[:200],
            "status_before": status_before,
            "status_after": {
                str(winner.id): PotentialMatchStatus.VERIFIED.value,
                **{str(l.id): PotentialMatchStatus.ACTIVE.value for l in losers},
            },
        },
    )
    db.commit()
    return {
        "success": True,
        "message": "Verification dispute resolved. Winner's chat is active.",
    }


def list_posts_moderation(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
) -> dict:
    """All active campus posts — flagged/reported items sorted to the top."""
    q = db.query(Item).filter(
        Item.status.notin_([ItemStatus.ARCHIVED, ItemStatus.EXPIRED])
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(Item.public_description.ilike(term))

    rows = q.order_by(Item.updated_at.desc()).limit(500).all()
    posts: list[dict] = []
    for item in rows:
        report_count = (
            db.query(func.count(PostReport.id))
            .filter(
                PostReport.item_id == item.id,
                PostReport.status == ReportStatus.PENDING,
            )
            .scalar()
            or 0
        )
        poster = db.query(User).filter(User.id == item.posted_by_id).first()
        flagged = (
            int(report_count or 0) > 0
            or bool(item.admin_locked)
            or item.status == ItemStatus.UNDER_DISPUTE
        )
        posts.append(
            {
                "item_id": item.id,
                "item_type": item.item_type.value,
                "category": item.category.value,
                "status": item.status.value,
                "public_description": item.public_description,
                "posted_by_name": poster.full_name if poster else "",
                "posted_by_id": item.posted_by_id,
                "admin_locked": bool(item.admin_locked),
                "pending_reports": int(report_count or 0),
                "flagged": flagged,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
        )

    posts.sort(
        key=lambda p: (
            0 if p["pending_reports"] > 0 else 1,
            0 if p["admin_locked"] else 1,
            0 if p["status"] == ItemStatus.UNDER_DISPUTE.value else 1,
            -(p["updated_at"].timestamp() if p["updated_at"] else 0),
        )
    )
    total = len(posts)
    page = posts[offset : offset + min(limit, 100)]
    return {"posts": page, "total": total}


def remove_post(
    db: Session, item_id: uuid.UUID, admin: User, reason: str | None = None
) -> dict:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item or item.status == ItemStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    before = item.status.value
    item.status = ItemStatus.ARCHIVED
    item.admin_locked = True
    item.updated_at = _now()
    matching_service.cleanup_on_item_archive(db, item.id)
    log_action(
        db,
        admin=admin,
        action=AdminActionType.REMOVE_POST,
        target_type="item",
        target_id=item.id,
        detail={"reason": reason or "", "status_before": before, "status_after": "archived"},
    )
    db.commit()
    return {"success": True, "message": "Post removed."}


def force_close_post(
    db: Session, item_id: uuid.UUID, admin: User, reason: str | None = None
) -> dict:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item or item.status in (ItemStatus.ARCHIVED, ItemStatus.CLOSED):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    before = item.status.value
    item.status = ItemStatus.CLOSED
    item.admin_locked = True
    item.updated_at = _now()
    matching_service.cleanup_on_item_archive(db, item.id)
    log_action(
        db,
        admin=admin,
        action=AdminActionType.FORCE_CLOSE_POST,
        target_type="item",
        target_id=item.id,
        detail={
            "reason": reason or "",
            "status_before": before,
            "status_after": ItemStatus.CLOSED.value,
        },
    )
    db.commit()
    return {"success": True, "message": "Post force-closed."}


def promote_assistant_admin(db: Session, user_id: uuid.UUID, root: User) -> User:
    if root.role != UserRole.ROOT_ADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if target.role != UserRole.USER:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only regular users can be promoted to assistant admin.",
        )
    count = (
        db.query(func.count(User.id))
        .filter(User.role == UserRole.ASSISTANT_ROOT_ADMIN)
        .scalar()
        or 0
    )
    if count >= MAX_ASSISTANT_ADMINS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Maximum of {MAX_ASSISTANT_ADMINS} assistant admins allowed.",
        )
    target.role = UserRole.ASSISTANT_ROOT_ADMIN
    log_action(
        db,
        admin=root,
        action=AdminActionType.PROMOTE_ADMIN,
        target_type="user",
        target_id=target.id,
    )
    db.commit()
    db.refresh(target)
    return target


def demote_assistant_admin(db: Session, user_id: uuid.UUID, root: User) -> User:
    if root.role != UserRole.ROOT_ADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    target = db.query(User).filter(User.id == user_id).first()
    if not target or target.role != UserRole.ASSISTANT_ROOT_ADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assistant admin not found.")
    target.role = UserRole.USER
    log_action(
        db,
        admin=root,
        action=AdminActionType.DEMOTE_ADMIN,
        target_type="user",
        target_id=target.id,
    )
    db.commit()
    db.refresh(target)
    return target


def list_admin_logs(
    db: Session,
    admin: User,
    *,
    limit: int = 100,
    admin_id_filter: Optional[uuid.UUID] = None,
    action_filter: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> list[dict]:
    if admin.role != UserRole.ROOT_ADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    q = db.query(AdminLog).order_by(AdminLog.created_at.desc())
    if admin_id_filter:
        q = q.filter(AdminLog.admin_id == admin_id_filter)
    if action_filter:
        try:
            action_enum = AdminActionType(action_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action filter.",
            )
        q = q.filter(AdminLog.action == action_enum)
    if date_from:
        q = q.filter(AdminLog.created_at >= date_from)
    if date_to:
        q = q.filter(AdminLog.created_at <= date_to)
    rows = q.limit(min(limit, 200)).all()
    out = []
    for row in rows:
        actor = db.query(User).filter(User.id == row.admin_id).first() if row.admin_id else None
        out.append(
            {
                "id": row.id,
                "admin_id": row.admin_id,
                "admin_email": actor.email if actor else None,
                "action": row.action.value,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "detail": row.detail or {},
                "created_at": row.created_at,
            }
        )
    return out

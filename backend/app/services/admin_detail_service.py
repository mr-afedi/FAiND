"""
Admin detail panels — Feature R reinforcement (Section 26).

Builds context for disputes, reports, posts, and users.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.admin_log import AdminLog, AdminActionType
from app.models.authority import Authority
from app.models.claim import Claim, ClaimPath, ClaimStatus
from app.models.handover import Handover
from app.models.item import Item, ItemStatus, ItemType
from app.models.item_return import ItemReturn, ReturnMethod
from app.models.drop_point import DropPoint
from app.models.notification import Notification
from app.models.potential_match import PotentialMatch
from app.models.report import PostReport, UserReport, ReportStatus
from app.models.user import User
from app.utils.encryption import decrypt


def _recent_admin_actions(
    db: Session,
    target_type: str,
    target_id: uuid.UUID,
    *,
    limit: int = 5,
) -> list[dict]:
    rows = (
        db.query(AdminLog)
        .filter(AdminLog.target_type == target_type, AdminLog.target_id == target_id)
        .order_by(AdminLog.created_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for row in rows:
        actor = db.query(User).filter(User.id == row.admin_id).first() if row.admin_id else None
        out.append(
            {
                "action": row.action.value,
                "admin_email": actor.email if actor else "system",
                "admin_id": row.admin_id,
                "detail": row.detail or {},
                "created_at": row.created_at,
            }
        )
    return out


def _user_brief(db: Session, user_id: uuid.UUID | None) -> dict | None:
    if not user_id:
        return None
    u = db.query(User).filter(User.id == user_id).first()
    if not u:
        return None
    return {
        "id": u.id,
        "username": u.username,
        "full_name": u.full_name,
        "email": u.email,
        "status": u.status.value,
        "role": u.role.value,
    }


def _item_detail(db: Session, item: Item | None) -> dict | None:
    if not item:
        return None
    poster = _user_brief(db, item.posted_by_id)
    return {
        "id": item.id,
        "item_type": item.item_type.value,
        "category": item.category.value,
        "status": item.status.value,
        "public_description": item.public_description,
        "location_label": item.location_label,
        "date_occurred": item.date_occurred,
        "image_urls": item.image_urls or [],
        "created_at": item.created_at,
        "updated_at": item.updated_at,
        "admin_locked": bool(item.admin_locked),
        "poster": poster,
    }


def _item_status_history(db: Session, item_id: uuid.UUID) -> list[dict]:
    logs = (
        db.query(AdminLog)
        .filter(
            AdminLog.target_type == "item",
            AdminLog.target_id == item_id,
        )
        .order_by(AdminLog.created_at.asc())
        .limit(50)
        .all()
    )
    history = [
        {
            "at": log.created_at,
            "event": log.action.value,
            "detail": log.detail or {},
        }
        for log in logs
    ]
    item = db.query(Item).filter(Item.id == item_id).first()
    if item:
        history.insert(
            0,
            {
                "at": item.created_at,
                "event": "posted",
                "detail": {"status": item.status.value},
            },
        )
    return history


def get_dispute_detail(
    db: Session,
    dispute_id: uuid.UUID,
    *,
    dispute_type: Optional[str] = None,
) -> dict:
    record = db.query(ItemReturn).filter(ItemReturn.id == dispute_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")

    if record.dispute_filed_at and not record.dispute_resolved_at:
        return _return_dispute_detail(db, record, dispute_type="return")

    if record.admin_review_flagged and not record.dispute_filed_at and not record.dispute_resolved_at:
        return _return_dispute_detail(db, record, dispute_type="manual")

    resolved_type = dispute_type or ("return" if record.dispute_filed_at else "manual")
    return _return_dispute_detail(db, record, dispute_type=resolved_type)


def _return_dispute_detail(db: Session, record: ItemReturn, *, dispute_type: str) -> dict:
    lost_item = db.query(Item).filter(Item.id == record.lost_item_id).first()
    found_item = db.query(Item).filter(Item.id == record.found_item_id).first()
    filed_by = _user_brief(db, record.dispute_filed_by_id)
    return {
        "dispute_type": dispute_type,
        "return_id": record.id,
        "match_id": record.potential_match_id,
        "dispute_filed_at": record.dispute_filed_at,
        "dispute_reason": record.dispute_reason or "",
        "filed_by": filed_by,
        "lost_owner": _user_brief(db, record.lost_owner_id),
        "found_owner": _user_brief(db, record.found_owner_id),
        "return_state": {
            "returned_at": record.returned_at,
            "finder_handed_over_at": record.finder_handed_over_at,
            "owner_received_at": record.owner_received_at,
            "method": record.method.value if record.method else None,
            "admin_review_flagged": record.admin_review_flagged,
            "dispute_resolved_at": record.dispute_resolved_at,
            "dispute_resolution_note": record.dispute_resolution_note,
        },
        "qr_logs": {
            "qr_generated": record.qr_token_hash is not None,
            "qr_expires_at": record.qr_expires_at,
            "qr_consumed_at": record.qr_consumed_at,
        },
        "lost_item": _item_detail(db, lost_item),
        "found_item": _item_detail(db, found_item),
        "reports_on_parties": _reports_for_users(
            db, [record.lost_owner_id, record.found_owner_id]
        ),
        "recent_actions": _recent_admin_actions(db, "item_return", record.id),
    }


def _reports_for_users(db: Session, user_ids: list[uuid.UUID]) -> dict:
    ids = [u for u in user_ids if u]
    if not ids:
        return {"user_reports": [], "post_reports": []}
    user_reports = (
        db.query(UserReport)
        .filter(UserReport.reported_user_id.in_(ids))
        .order_by(UserReport.created_at.desc())
        .limit(50)
        .all()
    )
    items = db.query(Item.id).filter(Item.posted_by_id.in_(ids)).all()
    item_ids = [i[0] for i in items]
    post_reports = []
    if item_ids:
        post_reports = (
            db.query(PostReport)
            .filter(PostReport.item_id.in_(item_ids))
            .order_by(PostReport.created_at.desc())
            .limit(50)
            .all()
        )
    return {
        "user_reports": [
            {
                "id": r.id,
                "reason": r.reason.value,
                "status": r.status.value,
                "created_at": r.created_at,
            }
            for r in user_reports
        ],
        "post_reports": [
            {
                "id": r.id,
                "reason": r.reason.value,
                "status": r.status.value,
                "created_at": r.created_at,
            }
            for r in post_reports
        ],
    }


def get_report_detail(
    db: Session,
    report_id: uuid.UUID,
    *,
    report_type: str,
) -> dict:
    if report_type == "post":
        report = (
            db.query(PostReport)
            .options(joinedload(PostReport.reporter), joinedload(PostReport.item))
            .filter(PostReport.id == report_id)
            .first()
        )
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
        item = report.item
        siblings = (
            db.query(PostReport)
            .filter(PostReport.item_id == report.item_id)
            .order_by(PostReport.created_at.desc())
            .all()
        )
        return {
            "report_type": "post",
            "report": {
                "id": report.id,
                "reason": report.reason.value,
                "detail_text": report.detail_text,
                "status": report.status.value,
                "auto_escalated": report.auto_escalated,
                "created_at": report.created_at,
                "reporter": _user_brief(db, report.reporter_id),
            },
            "target_item": _item_detail(db, item),
            "report_history_on_target": [
                {
                    "id": s.id,
                    "reason": s.reason.value,
                    "status": s.status.value,
                    "reporter_id": s.reporter_id,
                    "created_at": s.created_at,
                    "auto_escalated": s.auto_escalated,
                }
                for s in siblings
            ],
            "distinct_reporters": len({s.reporter_id for s in siblings}),
            "recent_actions": _recent_admin_actions(db, "post_report", report.id),
        }

    report = (
        db.query(UserReport)
        .options(joinedload(UserReport.reporter), joinedload(UserReport.reported_user))
        .filter(UserReport.id == report_id)
        .first()
    )
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    siblings = (
        db.query(UserReport)
        .filter(UserReport.reported_user_id == report.reported_user_id)
        .order_by(UserReport.created_at.desc())
        .all()
    )
    return {
        "report_type": "user",
        "report": {
            "id": report.id,
            "reason": report.reason.value,
            "detail_text": report.detail_text,
            "status": report.status.value,
            "auto_escalated": report.auto_escalated,
            "created_at": report.created_at,
            "reporter": _user_brief(db, report.reporter_id),
        },
        "target_user": _user_brief(db, report.reported_user_id),
        "report_history_on_target": [
            {
                "id": s.id,
                "reason": s.reason.value,
                "status": s.status.value,
                "reporter_id": s.reporter_id,
                "created_at": s.created_at,
                "auto_escalated": s.auto_escalated,
            }
            for s in siblings
        ],
        "distinct_reporters": len({s.reporter_id for s in siblings}),
        "recent_actions": _recent_admin_actions(db, "user_report", report.id),
    }


def get_post_detail(db: Session, item_id: uuid.UUID) -> dict:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    matches = (
        db.query(PotentialMatch)
        .filter(
            (PotentialMatch.lost_item_id == item_id)
            | (PotentialMatch.found_item_id == item_id)
        )
        .order_by(PotentialMatch.created_at.desc())
        .limit(50)
        .all()
    )
    matches_summary = [
        {
            "match_id": m.id,
            "status": m.status.value,
            "match_score": m.match_score,
            "created_at": m.created_at,
        }
        for m in matches
    ]

    reports = (
        db.query(PostReport)
        .filter(PostReport.item_id == item_id)
        .order_by(PostReport.created_at.desc())
        .all()
    )

    return {
        "item": _item_detail(db, item),
        "status_history": _item_status_history(db, item_id),
        "matches": matches_summary,
        "reports": [
            {
                "id": r.id,
                "reason": r.reason.value,
                "status": r.status.value,
                "reporter_id": r.reporter_id,
                "auto_escalated": r.auto_escalated,
                "created_at": r.created_at,
            }
            for r in reports
        ],
        "pending_reports": sum(1 for r in reports if r.status == ReportStatus.PENDING),
        "recent_actions": _recent_admin_actions(db, "item", item_id),
    }


def get_user_detail(db: Session, user_id: uuid.UUID) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    items = (
        db.query(Item)
        .filter(Item.posted_by_id == user_id)
        .order_by(Item.created_at.desc())
        .limit(50)
        .all()
    )
    reports_made_post = (
        db.query(PostReport)
        .filter(PostReport.reporter_id == user_id)
        .order_by(PostReport.created_at.desc())
        .limit(30)
        .all()
    )
    reports_made_user = (
        db.query(UserReport)
        .filter(UserReport.reporter_id == user_id)
        .order_by(UserReport.created_at.desc())
        .limit(30)
        .all()
    )
    reports_received = (
        db.query(UserReport)
        .filter(UserReport.reported_user_id == user_id)
        .order_by(UserReport.created_at.desc())
        .limit(30)
        .all()
    )

    suspension_logs = (
        db.query(AdminLog)
        .filter(
            AdminLog.target_type == "user",
            AdminLog.target_id == user_id,
            AdminLog.action.in_(
                (AdminActionType.SUSPEND_USER, AdminActionType.UNSUSPEND_USER)
            ),
        )
        .order_by(AdminLog.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "profile": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "full_name": user.full_name,
            "bio": user.bio,
            "profile_photo_url": user.profile_photo_url,
            "role": user.role.value,
            "status": user.status.value,
            "created_at": user.created_at,
            "suspended_at": user.suspended_at,
            "reports_suppressed": user.reports_suppressed,
        },
        "items_posted": [_item_detail(db, i) for i in items],
        "reports_made": {
            "post": [{"id": r.id, "reason": r.reason.value, "created_at": r.created_at} for r in reports_made_post],
            "user": [{"id": r.id, "reason": r.reason.value, "created_at": r.created_at} for r in reports_made_user],
        },
        "reports_received": [
            {"id": r.id, "reason": r.reason.value, "status": r.status.value, "created_at": r.created_at}
            for r in reports_received
        ],
        "suspension_history": [
            {
                "action": log.action.value,
                "admin_id": log.admin_id,
                "detail": log.detail or {},
                "created_at": log.created_at,
            }
            for log in suspension_logs
        ],
        "recent_actions": _recent_admin_actions(db, "user", user_id),
    }


def get_returned_item_detail(db: Session, return_id: uuid.UUID) -> dict:
    record = db.query(ItemReturn).filter(ItemReturn.id == return_id).first()
    if not record or not record.returned_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found.")

    lost_item = db.query(Item).filter(Item.id == record.lost_item_id).first()
    found_item = db.query(Item).filter(Item.id == record.found_item_id).first()
    owner = _user_brief(db, record.lost_owner_id)

    dispute_open = bool(
        record.dispute_filed_at
        or (record.admin_review_flagged and not record.dispute_resolved_at)
    )
    dispute_type = None
    if record.dispute_filed_at and not record.dispute_resolved_at:
        dispute_type = "return"
    elif record.admin_review_flagged and not record.dispute_resolved_at:
        dispute_type = "manual"

    method_label = None
    if record.method:
        method_label = {
            "dual_confirm": "Dual confirmation",
            "qr_scan": "QR code scan",
            "handover": "Authority handover",
        }.get(record.method.value, record.method.value)

    handover_detail = None
    claim_detail = None
    drop_point_name = None
    date_dropped_off = None
    if found_item and found_item.drop_point_id:
        dp = db.query(DropPoint).filter(DropPoint.id == found_item.drop_point_id).first()
        drop_point_name = dp.name if dp else None
    if found_item and found_item.authority_received_at:
        date_dropped_off = found_item.authority_received_at

    if record.handover_id:
        handover = db.query(Handover).filter(Handover.id == record.handover_id).first()
        claim = db.query(Claim).filter(Claim.id == handover.claim_id).first() if handover else None
        if handover:
            student_id = None
            if handover.claimant_student_id_encrypted:
                student_id = decrypt(handover.claimant_student_id_encrypted)
            handover_detail = {
                "id": handover.id,
                "condition_photo_url": handover.condition_photo_url,
                "claimant_name": handover.claimant_name,
                "claimant_phone": decrypt(handover.claimant_phone_encrypted),
                "claimant_student_id": student_id,
                "claimant_photo_url": handover.claimant_photo_url,
                "owner_confirmed": handover.owner_confirmed,
                "owner_confirmed_at": handover.owner_confirmed_at,
                "authority_override": bool(handover.authority_override_note),
                "authority_override_note": handover.authority_override_note,
                "completed_at": handover.owner_confirmed_at or handover.created_at,
            }
        if claim:
            claim_detail = {
                "claim_path": claim.claim_path.value,
                "ai_confidence_score": claim.ai_confidence_score,
            }

    finder_brief = _user_brief(db, record.found_owner_id)
    if not finder_brief and found_item and not found_item.posted_by_id:
        finder_brief = {
            "id": None,
            "username": None,
            "full_name": "Anonymous finder",
            "email": None,
            "status": None,
            "role": None,
        }

    return {
        "return_id": record.id,
        "lost_item": _item_detail(db, lost_item if lost_item and lost_item.id != found_item.id else None),
        "found_item": _item_detail(db, found_item),
        "owner": owner,
        "finder": finder_brief,
        "location_lost": lost_item.location_label if lost_item and lost_item.id != found_item.id else None,
        "location_found": found_item.location_label if found_item else None,
        "date_lost": lost_item.date_occurred if lost_item and lost_item.id != found_item.id else None,
        "date_found": found_item.date_occurred if found_item else None,
        "date_posted": found_item.created_at if found_item else None,
        "date_dropped_off": date_dropped_off,
        "date_returned": record.returned_at,
        "drop_point_name": drop_point_name,
        "return_method": method_label,
        "handover": handover_detail,
        "claim": claim_detail,
        "dispute": {
            "had_dispute": bool(
                record.dispute_filed_at or record.dispute_resolved_at or record.admin_review_flagged
            ),
            "open": dispute_open,
            "dispute_type": dispute_type,
            "return_id": record.id,
            "filed_at": record.dispute_filed_at,
            "resolved_at": record.dispute_resolved_at,
            "reason": record.dispute_reason,
            "resolution_note": record.dispute_resolution_note,
        },
        "can_open_dispute": not dispute_open,
    }


def _authority_brief(db: Session, authority_id: uuid.UUID | str | None) -> dict | None:
    if not authority_id:
        return None
    aid = uuid.UUID(str(authority_id)) if not isinstance(authority_id, uuid.UUID) else authority_id
    auth = db.query(Authority).filter(Authority.id == aid).first()
    if not auth:
        return None
    dp = db.query(DropPoint).filter(DropPoint.id == auth.drop_point_id).first()
    return {
        "authority_id": auth.id,
        "email": auth.email,
        "drop_point_name": dp.name if dp else None,
    }


def _handover_detail_dict(handover: Handover) -> dict:
    student_id = None
    if handover.claimant_student_id_encrypted:
        student_id = decrypt(handover.claimant_student_id_encrypted)
    return {
        "id": handover.id,
        "condition_photo_url": handover.condition_photo_url,
        "claimant_name": handover.claimant_name,
        "claimant_phone": decrypt(handover.claimant_phone_encrypted),
        "claimant_student_id": student_id,
        "claimant_photo_url": handover.claimant_photo_url,
        "owner_confirmed": handover.owner_confirmed,
        "owner_confirmed_at": handover.owner_confirmed_at,
        "authority_override": bool(handover.authority_override_note),
        "authority_override_note": handover.authority_override_note,
        "completed_at": handover.owner_confirmed_at or handover.created_at,
    }


def get_claim_overview_detail(db: Session, found_item_id: uuid.UUID) -> dict:
    """Full claim evidence for admin Claims Overview detail panel."""
    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(Item.id == found_item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")

    claims = (
        db.query(Claim)
        .options(joinedload(Claim.claimant))
        .filter(Claim.found_item_id == found_item_id)
        .order_by(Claim.created_at.asc())
        .all()
    )
    if not claims:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No claims found for this item.",
        )

    claim_ids = [c.id for c in claims]
    called_rows = (
        db.query(Notification.reference_id, Notification.created_at)
        .filter(
            Notification.reference_id.in_(claim_ids),
            Notification.title == "Please come to collect",
        )
        .all()
    )
    called_map = {row[0]: row[1] for row in called_rows if row[0]}

    finder = _user_brief(db, item.posted_by_id)
    if not finder and not item.posted_by_id:
        finder = {
            "id": None,
            "username": None,
            "full_name": "Anonymous Finder",
            "email": None,
            "status": None,
            "role": None,
        }

    drop_point = item.drop_point
    drop_point_name = drop_point.name if drop_point else None
    found_item_detail = {
        **_item_detail(db, item),
        "drop_point_id": item.drop_point_id,
        "drop_point_name": drop_point_name,
        "authority_received_at": item.authority_received_at,
        "date_found": item.date_occurred,
    }

    claimants = []
    for claim in claims:
        user = claim.claimant
        display_status = claim.status.value
        if claim.status == ClaimStatus.PENDING and claim.id in called_map:
            display_status = "called_to_collect"
        claimants.append(
            {
                "claim_id": claim.id,
                "username": user.username,
                "full_name": user.full_name,
                "trust_tier": None,
                "description": claim.description,
                "photo_url": claim.photo_url,
                "date_lost": claim.date_lost,
                "time_lost": claim.time_lost,
                "lost_location": claim.lost_location if claim.claim_path == ClaimPath.C else None,
                "ai_confidence_score": claim.ai_confidence_score
                if claim.claim_path == ClaimPath.A
                else None,
                "claim_path": claim.claim_path.value,
                "created_at": claim.created_at,
                "status": claim.status.value,
                "display_status": display_status,
            }
        )

    claim_logs = (
        db.query(AdminLog)
        .filter(
            AdminLog.target_type == "claim",
            AdminLog.target_id.in_(claim_ids),
        )
        .order_by(AdminLog.created_at.asc())
        .all()
    )

    handover = (
        db.query(Handover)
        .filter(Handover.item_id == found_item_id)
        .first()
    )
    handover_logs: list[AdminLog] = []
    if handover:
        handover_logs = (
            db.query(AdminLog)
            .filter(
                AdminLog.target_type == "handover",
                AdminLog.target_id == handover.id,
            )
            .order_by(AdminLog.created_at.asc())
            .all()
        )

    authority_ids: set[uuid.UUID] = set()
    for log in claim_logs + handover_logs:
        aid = (log.detail or {}).get("authority_id")
        if aid:
            authority_ids.add(uuid.UUID(str(aid)))
    if drop_point:
        assigned = db.query(Authority).filter(Authority.drop_point_id == drop_point.id).first()
        if assigned:
            authority_ids.add(assigned.id)

    authorities: list[dict] = []
    seen_auth: set[uuid.UUID] = set()
    for aid in authority_ids:
        if aid in seen_auth:
            continue
        brief = _authority_brief(db, aid)
        if brief:
            authorities.append(brief)
            seen_auth.add(aid)

    timeline: list[dict] = []
    if item.authority_received_at:
        timeline.append(
            {
                "event": "received_item",
                "label": f"Item received at {drop_point_name or 'drop point'}",
                "at": item.authority_received_at,
                "actor": authorities[0]["email"] if authorities else None,
            }
        )

    for claim in claims:
        if claim.id in called_map:
            timeline.append(
                {
                    "event": "called_to_collect",
                    "label": f"Called claimant @{claim.claimant.username} to collect",
                    "at": called_map[claim.id],
                    "claim_id": claim.id,
                    "actor": None,
                }
            )

    verified_at_by_claim: dict[uuid.UUID, datetime] = {}
    for log in claim_logs:
        claim = next((c for c in claims if c.id == log.target_id), None)
        username = claim.claimant.username if claim else "claimant"
        actor = _authority_brief(db, (log.detail or {}).get("authority_id"))
        actor_email = actor["email"] if actor else None

        if log.action == AdminActionType.APPROVE_CLAIM:
            verified_at_by_claim[log.target_id] = log.created_at
            timeline.append(
                {
                    "event": "verified",
                    "label": f"Verified claimant @{username} as owner",
                    "at": log.created_at,
                    "claim_id": log.target_id,
                    "actor": actor_email,
                }
            )
        elif log.action == AdminActionType.REJECT_CLAIM:
            timeline.append(
                {
                    "event": "rejected",
                    "label": f"Rejected claimant @{username}",
                    "at": log.created_at,
                    "claim_id": log.target_id,
                    "actor": actor_email,
                }
            )

    reject_logged = {
        log.target_id
        for log in claim_logs
        if log.action == AdminActionType.REJECT_CLAIM
    }
    for claim in claims:
        if claim.status != ClaimStatus.REJECTED or claim.id in reject_logged:
            continue
        verified_claim = next((c for c in claims if c.status == ClaimStatus.VERIFIED), None)
        at = verified_at_by_claim.get(verified_claim.id) if verified_claim else None
        timeline.append(
            {
                "event": "rejected",
                "label": (
                    f"Rejected claimant @{claim.claimant.username} "
                    "(another claimant verified)"
                ),
                "at": at or claim.created_at,
                "claim_id": claim.id,
                "actor": None,
            }
        )

    handover_detail = None
    if handover:
        handover_detail = _handover_detail_dict(handover)
        if handover.owner_confirmed_at or handover.authority_override_note:
            actor = _authority_brief(
                db,
                (handover_logs[-1].detail or {}).get("authority_id") if handover_logs else None,
            )
            timeline.append(
                {
                    "event": "handover_completed",
                    "label": (
                        "Handover completed"
                        + (" (authority override)" if handover.authority_override_note else "")
                    ),
                    "at": handover_detail["completed_at"],
                    "actor": actor["email"] if actor else None,
                }
            )

    epoch = datetime.min.replace(tzinfo=timezone.utc)
    timeline.sort(key=lambda entry: entry["at"] or epoch)

    return {
        "found_item": found_item_detail,
        "finder": finder,
        "claimants": claimants,
        "authorities": authorities,
        "timeline": timeline,
        "handover": handover_detail,
        "is_returned": item.status == ItemStatus.RETURNED,
    }

"""
Admin detail panels — Feature R reinforcement (Section 26).

Builds rich context for claims, disputes, reports, fraud, posts, and users.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.admin_log import AdminLog, AdminActionType
from app.models.conversation import Conversation
from app.models.fraud_event import FraudEvent
from app.models.ihave_this_item_claim import IHaveThisItemClaim
from app.models.item import Item, ItemStatus, ItemType
from app.models.item_return import ItemReturn
from app.models.message import Message
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.report import PostReport, UserReport, ReportStatus
from app.models.this_might_be_mine_claim import ThisMightBeMineClaim
from app.models.trust_event import TrustEvent
from app.models.user import User
from app.models.verification_attempt import VerificationAttempt, VerificationPath
from app.services.trust_service import get_trust_tier
from app.services.fraud_service import get_risk_tier

SCORING_FORMULAS = {
    "path_a": "Path A: weighted average of hidden-answer semantic similarities (review at 0.50–0.70)",
    "path_b": "Path B: 0.40×hidden + 0.35×image + 0.25×location (review at 0.50–0.75)",
    "path_c": "Path C: 1.0×hidden answer similarity only (review at 0.50–0.70)",
}


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
        "trust_score": u.trust_score,
        "trust_tier": get_trust_tier(u.trust_score),
        "fraud_risk_score": u.fraud_risk_score,
        "fraud_risk_tier": get_risk_tier(u.fraud_risk_score),
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


def _detect_claim_path(
    db: Session, match: PotentialMatch
) -> tuple[str, uuid.UUID | None, Any | None]:
    claim_b = (
        db.query(IHaveThisItemClaim)
        .filter(IHaveThisItemClaim.potential_match_id == match.id)
        .order_by(IHaveThisItemClaim.created_at.desc())
        .first()
    )
    if claim_b:
        return "path_b", claim_b.user_id, claim_b

    claim_c = (
        db.query(ThisMightBeMineClaim)
        .filter(ThisMightBeMineClaim.potential_match_id == match.id)
        .order_by(ThisMightBeMineClaim.created_at.desc())
        .first()
    )
    if claim_c:
        return "path_c", claim_c.user_id, claim_c

    attempt = (
        db.query(VerificationAttempt)
        .filter(VerificationAttempt.potential_match_id == match.id)
        .order_by(VerificationAttempt.created_at.desc())
        .first()
    )
    if attempt:
        return "path_a", attempt.user_id, attempt
    return "path_a", None, None


def _verification_attempts_for_match(db: Session, match_id: uuid.UUID) -> list[dict]:
    rows = (
        db.query(VerificationAttempt)
        .filter(VerificationAttempt.potential_match_id == match_id)
        .order_by(VerificationAttempt.created_at.asc())
        .all()
    )
    return [
        {
            "id": r.id,
            "path": r.path.value if r.path else "path_a",
            "ownership_score": r.ownership_score,
            "result": r.result.value,
            "score_breakdown": r.score_breakdown or {},
            "created_at": r.created_at,
            "user_id": r.user_id,
        }
        for r in rows
    ]


def _sanitize_path_c_detail(detail: dict) -> dict:
    """Strip raw hidden answers — admin sees similarity scores only."""
    if not detail:
        return {}
    out = dict(detail)
    if "finder_questions" in out:
        out["finder_questions"] = [
            {
                "question_id": q.get("question_id"),
                "position": q.get("position"),
                "question": q.get("question"),
            }
            for q in out.get("finder_questions", [])
        ]
    if "owner_answers" in out:
        out["owner_answers"] = [
            {
                "question_id": a.get("question_id"),
                "position": a.get("position"),
                "answer_provided": True,
            }
            for a in out.get("owner_answers", [])
        ]
    return out


def get_claim_detail(db: Session, match_id: uuid.UUID) -> dict:
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found.")

    path, claimant_id, claim_obj = _detect_claim_path(db, match)
    claimant = _user_brief(db, claimant_id)

    evidence: dict[str, Any] = {
        "score_breakdown": match.score_breakdown or {},
        "verification_attempts": _verification_attempts_for_match(db, match.id),
    }

    if path == "path_b" and isinstance(claim_obj, IHaveThisItemClaim):
        evidence["claim_submission"] = {
            "location_label": claim_obj.location_label,
            "image_url": claim_obj.image_url,
            "attempt_scores": claim_obj.attempt_scores or [],
            "result": claim_obj.result.value,
            "ownership_score": claim_obj.ownership_score,
            "score_breakdown": claim_obj.score_breakdown or {},
        }
    elif path == "path_c" and isinstance(claim_obj, ThisMightBeMineClaim):
        evidence["claim_submission"] = {
            "attempt_scores": claim_obj.attempt_scores or [],
            "result": claim_obj.result.value,
            "ownership_score": claim_obj.ownership_score,
            "score_breakdown": claim_obj.score_breakdown or {},
            "verification_detail": _sanitize_path_c_detail(claim_obj.verification_detail or {}),
        }

    return {
        "match_id": match.id,
        "path": path,
        "scoring_formula": SCORING_FORMULAS.get(path, path),
        "status": match.status.value,
        "match_score": match.match_score,
        "created_at": match.created_at,
        "claimant": claimant,
        "lost_item": _item_detail(db, match.lost_item),
        "found_item": _item_detail(db, match.found_item),
        "evidence": evidence,
        "status_history": _item_status_history(db, match.lost_item_id),
    }


def _chat_for_match(db: Session, match_id: uuid.UUID) -> list[dict]:
    conv = (
        db.query(Conversation)
        .filter(Conversation.potential_match_id == match_id)
        .first()
    )
    if not conv:
        return []
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .limit(500)
        .all()
    )
    out = []
    for m in messages:
        sender = db.query(User).filter(User.id == m.sender_id).first()
        out.append(
            {
                "id": m.id,
                "sender_name": sender.full_name if sender else "Unknown",
                "sender_id": m.sender_id,
                "body": m.body,
                "created_at": m.created_at,
                "read_at": m.read_at,
            }
        )
    return out


def get_dispute_detail(
    db: Session,
    dispute_id: uuid.UUID,
    *,
    dispute_type: Optional[str] = None,
) -> dict:
    record = db.query(ItemReturn).filter(ItemReturn.id == dispute_id).first()
    if record and record.dispute_filed_at and not record.dispute_resolved_at:
        return _return_dispute_detail(db, record, dispute_type="return")

    if record and record.admin_review_flagged and not record.dispute_filed_at:
        return _return_dispute_detail(db, record, dispute_type="manual")

    match = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item),
        )
        .filter(PotentialMatch.id == dispute_id)
        .first()
    )
    if match and match.status == PotentialMatchStatus.PAUSED:
        return _verification_dispute_detail(db, match)

    if record:
        return _return_dispute_detail(
            db,
            record,
            dispute_type=dispute_type or ("return" if record.dispute_filed_at else "manual"),
        )

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")


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
            "tip_frozen": record.tip_frozen,
            "admin_review_flagged": record.admin_review_flagged,
        },
        "qr_logs": {
            "qr_generated": record.qr_token_hash is not None,
            "qr_expires_at": record.qr_expires_at,
            "qr_consumed_at": record.qr_consumed_at,
        },
        "lost_item": _item_detail(db, lost_item),
        "found_item": _item_detail(db, found_item),
        "verification_history": _verification_attempts_for_match(db, record.potential_match_id),
        "chat_history": _chat_for_match(db, record.potential_match_id),
        "reports_on_parties": _reports_for_users(
            db, [record.lost_owner_id, record.found_owner_id]
        ),
    }


def _verification_dispute_detail(db: Session, match: PotentialMatch) -> dict:
    paused_matches = (
        db.query(PotentialMatch)
        .filter(
            PotentialMatch.lost_item_id == match.lost_item_id,
            PotentialMatch.status == PotentialMatchStatus.PAUSED,
        )
        .all()
    )
    verified_matches = (
        db.query(PotentialMatch)
        .filter(
            PotentialMatch.lost_item_id == match.lost_item_id,
            PotentialMatch.status == PotentialMatchStatus.VERIFIED,
        )
        .all()
    )
    claimants = []
    for m in paused_matches + verified_matches:
        path, claimant_id, _ = _detect_claim_path(db, m)
        claimants.append(
            {
                "match_id": m.id,
                "path": path,
                "status": m.status.value,
                "match_score": m.match_score,
                "claimant": _user_brief(db, claimant_id),
            }
        )

    return {
        "dispute_type": "verification",
        "match_id": match.id,
        "lost_item": _item_detail(db, match.lost_item),
        "found_item": _item_detail(db, match.found_item),
        "claimants": claimants,
        "verification_history": _verification_attempts_for_match(db, match.id),
        "chat_history": _chat_for_match(db, match.id),
        "reports_on_parties": _reports_for_users(
            db,
            [match.lost_item.posted_by_id] if match.lost_item else [],
        ),
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
    claims_summary = []
    for m in matches:
        path, claimant_id, _ = _detect_claim_path(db, m)
        claims_summary.append(
            {
                "match_id": m.id,
                "path": path,
                "status": m.status.value,
                "match_score": m.match_score,
                "claimant": _user_brief(db, claimant_id),
                "created_at": m.created_at,
            }
        )

    reports = (
        db.query(PostReport)
        .filter(PostReport.item_id == item_id)
        .order_by(PostReport.created_at.desc())
        .all()
    )

    return {
        "item": _item_detail(db, item),
        "status_history": _item_status_history(db, item_id),
        "claims": claims_summary,
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
    }


def get_user_detail(db: Session, user_id: uuid.UUID) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    trust_events = (
        db.query(TrustEvent)
        .filter(TrustEvent.user_id == user_id)
        .order_by(TrustEvent.created_at.desc())
        .limit(100)
        .all()
    )
    fraud_events = (
        db.query(FraudEvent)
        .filter(FraudEvent.user_id == user_id)
        .order_by(FraudEvent.created_at.asc())
        .limit(100)
        .all()
    )
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

    claims_b = (
        db.query(IHaveThisItemClaim)
        .filter(IHaveThisItemClaim.user_id == user_id)
        .order_by(IHaveThisItemClaim.created_at.desc())
        .limit(30)
        .all()
    )
    claims_c = (
        db.query(ThisMightBeMineClaim)
        .filter(ThisMightBeMineClaim.user_id == user_id)
        .order_by(ThisMightBeMineClaim.created_at.desc())
        .limit(30)
        .all()
    )
    verifications = (
        db.query(VerificationAttempt)
        .filter(VerificationAttempt.user_id == user_id)
        .order_by(VerificationAttempt.created_at.desc())
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
            "fraud_verification_override": getattr(user, "fraud_verification_override", False),
        },
        "trust_score": user.trust_score,
        "trust_tier": get_trust_tier(user.trust_score),
        "trust_events": [
            {
                "id": e.id,
                "delta": e.delta,
                "reason": e.reason.value,
                "reference_id": e.reference_id,
                "applied_by_id": e.applied_by_id,
                "created_at": e.created_at,
            }
            for e in trust_events
        ],
        "fraud_risk_score": user.fraud_risk_score,
        "fraud_risk_tier": get_risk_tier(user.fraud_risk_score),
        "fraud_events": [
            {
                "id": e.id,
                "signal_type": e.signal_type.value,
                "delta": e.delta,
                "score_after": e.score_after,
                "detail": e.detail or {},
                "note": e.note,
                "created_at": e.created_at,
            }
            for e in fraud_events
        ],
        "items_posted": [_item_detail(db, i) for i in items],
        "claims": {
            "path_a_attempts": [
                {
                    "id": v.id,
                    "result": v.result.value,
                    "ownership_score": v.ownership_score,
                    "created_at": v.created_at,
                }
                for v in verifications
            ],
            "path_b": [
                {
                    "id": c.id,
                    "result": c.result.value,
                    "ownership_score": c.ownership_score,
                    "lost_item_id": c.lost_item_id,
                    "created_at": c.created_at,
                }
                for c in claims_b
            ],
            "path_c": [
                {
                    "id": c.id,
                    "result": c.result.value,
                    "ownership_score": c.ownership_score,
                    "found_item_id": c.found_item_id,
                    "created_at": c.created_at,
                }
                for c in claims_c
            ],
        },
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
    }


def get_fraud_detail(db: Session, user_id: uuid.UUID) -> dict:
    detail = get_user_detail(db, user_id)
    return {
        "user": detail["profile"],
        "fraud_risk_score": detail["fraud_risk_score"],
        "fraud_risk_tier": detail["fraud_risk_tier"],
        "fraud_events": detail["fraud_events"],
        "trust_score": detail["trust_score"],
        "trust_tier": detail["trust_tier"],
    }

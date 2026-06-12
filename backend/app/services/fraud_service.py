"""
FraudService — canonical entry point for fraud risk scoring (Section 18).

Rules:
- Every fraud risk change MUST go through apply_fraud_delta.
- All signals are logged to fraud_events for admin review.
- Fraud risk is internal only — never exposed in public user APIs.
- At 100+ risk, further verification/claims are blocked until admin review.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.fraud_event import FraudEvent, FraudSignalType
from app.models.user import User, UserRole, AccountStatus
from app.models.verification_attempt import (
    VerificationAttempt,
    VerificationPath,
    VerificationResult,
)
from app.services import notification_service

FALSE_CLAIM_THRESHOLD = 0.30
LOW_SCORE_LOOKBACK_DAYS = 7
CLAIM_VOLUME_WINDOW_HOURS = 24
CLAIM_VOLUME_THRESHOLD = 5
BLOCK_THRESHOLD = 100
ELEVATED_THRESHOLD = 31
HIGH_THRESHOLD = 61


def get_risk_tier(score: int) -> str:
    """Section 18.2 — admin-facing tier label."""
    if score >= BLOCK_THRESHOLD:
        return "blocked"
    if score >= HIGH_THRESHOLD:
        return "high"
    if score >= ELEVATED_THRESHOLD:
        return "elevated"
    return "normal"


def assert_can_attempt_verification(db: Session, user: User) -> None:
    """Section 18.2 — block new verifications/claims at 100+ risk."""
    db.refresh(user)
    if getattr(user, "fraud_verification_override", False):
        return
    if user.fraud_risk_score >= BLOCK_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Your account requires admin review before you can submit "
                "further verification attempts."
            ),
        )


def apply_fraud_delta(
    db: Session,
    *,
    user_id: uuid.UUID,
    university_id: uuid.UUID,
    delta: int,
    signal_type: FraudSignalType,
    reference_id: Optional[uuid.UUID] = None,
    detail: Optional[dict] = None,
    note: Optional[str] = None,
    applied_by_id: Optional[uuid.UUID] = None,
    notify_admin: bool = False,
) -> FraudEvent:
    """
    Apply a fraud risk delta and log the event. Does not commit.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise LookupError(f"User {user_id} not found")

    score_before = user.fraud_risk_score
    user.fraud_risk_score = min(100, max(0, user.fraud_risk_score + delta))
    score_after = user.fraud_risk_score

    event = FraudEvent(
        university_id=university_id,
        user_id=user_id,
        signal_type=signal_type,
        delta=delta,
        score_after=score_after,
        reference_id=reference_id,
        detail=detail or {},
        note=note,
        applied_by_id=applied_by_id,
    )
    db.add(event)
    db.flush()

    if notify_admin:
        _notify_admins_fraud_alert(
            db,
            user_id=user_id,
            signal_type=signal_type,
            score_after=score_after,
            reference_id=reference_id,
        )

    if score_before < HIGH_THRESHOLD <= score_after:
        apply_fraud_delta(
            db,
            user_id=user_id,
            university_id=university_id,
            delta=0,
            signal_type=FraudSignalType.RISK_TIER_HIGH,
            reference_id=reference_id,
            detail={"score_before": score_before, "score_after": score_after},
            notify_admin=True,
        )

    return event


def _since_hours(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


def _failed_verifications_24h(db: Session, user_id: uuid.UUID) -> int:
    since = _since_hours(24)
    return (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.user_id == user_id,
            VerificationAttempt.result == VerificationResult.REJECTED,
            VerificationAttempt.created_at >= since,
        )
        .count()
    )


def _claims_24h(db: Session, user_id: uuid.UUID) -> int:
    since = _since_hours(CLAIM_VOLUME_WINDOW_HOURS)
    return (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.user_id == user_id,
            VerificationAttempt.created_at >= since,
        )
        .count()
    )


def _item_key_for_attempt(attempt: VerificationAttempt) -> uuid.UUID:
    if attempt.path == VerificationPath.PATH_C:
        return attempt.found_item_id
    return attempt.lost_item_id


def _low_score_distinct_items_7d(db: Session, user_id: uuid.UUID) -> int:
    since = datetime.now(timezone.utc) - timedelta(days=LOW_SCORE_LOOKBACK_DAYS)
    rows = (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.user_id == user_id,
            VerificationAttempt.result == VerificationResult.REJECTED,
            VerificationAttempt.ownership_score < FALSE_CLAIM_THRESHOLD,
            VerificationAttempt.created_at >= since,
        )
        .all()
    )
    keys = {_item_key_for_attempt(r) for r in rows}
    return len(keys)


def _has_recent_signal(
    db: Session, user_id: uuid.UUID, signal_type: FraudSignalType, hours: int
) -> bool:
    since = _since_hours(hours)
    return (
        db.query(FraudEvent)
        .filter(
            FraudEvent.user_id == user_id,
            FraudEvent.signal_type == signal_type,
            FraudEvent.created_at >= since,
        )
        .first()
        is not None
    )


def on_verification_rejected(
    db: Session,
    *,
    attempt: VerificationAttempt,
) -> None:
    """
    Process fraud signals after a rejected verification attempt is persisted.
    """
    user = db.query(User).filter(User.id == attempt.user_id).first()
    if not user:
        return

    failed_count = _failed_verifications_24h(db, user.id)
    if failed_count == 2:
        apply_fraud_delta(
            db,
            user_id=user.id,
            university_id=user.university_id,
            delta=10,
            signal_type=FraudSignalType.FAILED_VERIFICATIONS_2_IN_24H,
            reference_id=attempt.id,
            detail={"failed_count_24h": failed_count},
        )
    elif failed_count == 3:
        apply_fraud_delta(
            db,
            user_id=user.id,
            university_id=user.university_id,
            delta=20,
            signal_type=FraudSignalType.FAILED_VERIFICATIONS_3_IN_24H,
            reference_id=attempt.id,
            detail={"failed_count_24h": failed_count},
            notify_admin=True,
        )

    if attempt.path in (VerificationPath.PATH_B, VerificationPath.PATH_C):
        apply_fraud_delta(
            db,
            user_id=user.id,
            university_id=user.university_id,
            delta=10,
            signal_type=FraudSignalType.PATH_B_C_CLAIM_FAILED,
            reference_id=attempt.id,
            detail={"path": attempt.path.value, "score": attempt.ownership_score},
        )

    if attempt.ownership_score < FALSE_CLAIM_THRESHOLD:
        distinct = _low_score_distinct_items_7d(db, user.id)
        if distinct >= 2 and not _has_recent_signal(
            db,
            user.id,
            FraudSignalType.REPEATED_LOW_SCORE_MULTI_ITEM,
            hours=LOW_SCORE_LOOKBACK_DAYS * 24,
        ):
            apply_fraud_delta(
                db,
                user_id=user.id,
                university_id=user.university_id,
                delta=15,
                signal_type=FraudSignalType.REPEATED_LOW_SCORE_MULTI_ITEM,
                reference_id=attempt.id,
                detail={"distinct_low_score_items_7d": distinct},
            )

    claim_count = _claims_24h(db, user.id)
    if claim_count >= CLAIM_VOLUME_THRESHOLD and not _has_recent_signal(
        db, user.id, FraudSignalType.UNUSUAL_CLAIM_VOLUME, hours=24
    ):
        apply_fraud_delta(
            db,
            user_id=user.id,
            university_id=user.university_id,
            delta=25,
            signal_type=FraudSignalType.UNUSUAL_CLAIM_VOLUME,
            reference_id=attempt.id,
            detail={"claims_24h": claim_count},
            notify_admin=True,
        )


def record_gradual_improvement(
    db: Session,
    *,
    user_id: uuid.UUID,
    university_id: uuid.UUID,
    reference_id: uuid.UUID,
    attempt_scores: list[float],
) -> FraudEvent:
    """Section 12.9 (V4.3) — monotonically improving attempt scores."""
    return apply_fraud_delta(
        db,
        user_id=user_id,
        university_id=university_id,
        delta=10,
        signal_type=FraudSignalType.GRADUAL_IMPROVEMENT,
        reference_id=reference_id,
        detail={"attempt_scores": attempt_scores},
        notify_admin=True,
    )


def record_dispute_user_flagged(
    db: Session,
    *,
    user_id: uuid.UUID,
    university_id: uuid.UUID,
    return_id: uuid.UUID,
    admin_id: uuid.UUID,
    note: str,
) -> FraudEvent:
    """Section 19.4 — admin flags a user during dispute resolution."""
    return apply_fraud_delta(
        db,
        user_id=user_id,
        university_id=university_id,
        delta=15,
        signal_type=FraudSignalType.DISPUTE_USER_FLAGGED,
        reference_id=return_id,
        detail={"dispute_outcome": "flagged", "admin_note": note[:200]},
        applied_by_id=admin_id,
        notify_admin=True,
    )


def record_user_report(
    db: Session,
    *,
    reported_user_id: uuid.UUID,
    report_id: uuid.UUID,
    report_count: int,
) -> Optional[FraudEvent]:
    """
    Section 18.1 — +15 fraud risk per user report after the first.
    Call from Feature P when reports are implemented.
    """
    if report_count <= 1:
        return None
    user = db.query(User).filter(User.id == reported_user_id).first()
    if not user:
        return None
    return apply_fraud_delta(
        db,
        user_id=user.id,
        university_id=user.university_id,
        delta=15,
        signal_type=FraudSignalType.USER_REPORT_RECEIVED,
        reference_id=report_id,
        detail={"report_count": report_count},
        notify_admin=report_count >= 2,
    )


def admin_confirm_fraud(
    db: Session,
    *,
    target_user_id: uuid.UUID,
    admin: User,
) -> FraudEvent:
    """Section 18.1 — admin confirms fraud: +50 risk, trust penalty via TrustService."""
    from app.services import trust_service

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    trust_service.penalise_fraud_confirmed(
        db, target_user_id, applied_by_id=admin.id
    )
    return apply_fraud_delta(
        db,
        user_id=target.id,
        university_id=target.university_id,
        delta=50,
        signal_type=FraudSignalType.ADMIN_CONFIRMED_FRAUD,
        reference_id=target.id,
        applied_by_id=admin.id,
        notify_admin=True,
    )


def admin_clear_fraud_flag(
    db: Session,
    *,
    target_user_id: uuid.UUID,
    admin: User,
) -> FraudEvent:
    """Reset fraud risk to 0, clear verification override, and log admin clear."""
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    target.fraud_verification_override = False
    delta = -target.fraud_risk_score
    return apply_fraud_delta(
        db,
        user_id=target.id,
        university_id=target.university_id,
        delta=delta,
        signal_type=FraudSignalType.ADMIN_CLEARED_FLAG,
        reference_id=target.id,
        applied_by_id=admin.id,
        note="Admin cleared fraud flag",
    )


def admin_allow_verification(
    db: Session,
    *,
    target_user_id: uuid.UUID,
    admin: User,
) -> User:
    """Allow blocked user to attempt verification again."""
    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    target.fraud_verification_override = True
    apply_fraud_delta(
        db,
        user_id=target.id,
        university_id=target.university_id,
        delta=0,
        signal_type=FraudSignalType.ADMIN_VERIFICATION_OVERRIDE,
        reference_id=target.id,
        applied_by_id=admin.id,
        note="Admin allowed verification attempts",
    )
    db.flush()
    return target


def _notify_admins_fraud_alert(
    db: Session,
    *,
    user_id: uuid.UUID,
    signal_type: FraudSignalType,
    score_after: int,
    reference_id: Optional[uuid.UUID],
) -> None:
    admins = (
        db.query(User)
        .filter(
            User.role.in_((UserRole.ROOT_ADMIN, UserRole.ASSISTANT_ROOT_ADMIN)),
            User.status == AccountStatus.ACTIVE,
        )
        .all()
    )
    tier = get_risk_tier(score_after)
    body = (
        f"Fraud signal: {signal_type.value.replace('_', ' ')}. "
        f"User risk score is now {score_after} ({tier})."
    )
    link = f"admin:fraud:{user_id}"
    for admin in admins:
        notification_service.notify_fraud_alert(
            db,
            admin_id=admin.id,
            user_id=user_id,
            title="Fraud monitoring alert",
            body=body,
            link=link,
            reference_id=reference_id or user_id,
        )
    db.flush()


def list_fraud_alerts(db: Session, *, limit: int = 50) -> list[dict]:
    """Users with fraud risk score above 30 (elevated tier and above)."""
    users = (
        db.query(User)
        .filter(User.fraud_risk_score > 30)
        .order_by(User.fraud_risk_score.desc())
        .limit(limit)
        .all()
    )
    out = []
    for u in users:
        last_event = (
            db.query(FraudEvent)
            .filter(FraudEvent.user_id == u.id)
            .order_by(FraudEvent.created_at.desc())
            .first()
        )
        override = getattr(u, "fraud_verification_override", False)
        out.append(
            {
                "user_id": u.id,
                "email": u.email,
                "username": u.username,
                "full_name": u.full_name,
                "trust_score": u.trust_score,
                "fraud_risk_score": u.fraud_risk_score,
                "risk_tier": get_risk_tier(u.fraud_risk_score),
                "verification_blocked": u.fraud_risk_score >= BLOCK_THRESHOLD and not override,
                "fraud_verification_override": override,
                "last_signal": last_event.signal_type.value if last_event else None,
                "last_event_at": last_event.created_at if last_event else None,
            }
        )
    return out


def list_user_fraud_events(
    db: Session, user_id: uuid.UUID, *, limit: int = 100
) -> list[FraudEvent]:
    return (
        db.query(FraudEvent)
        .filter(FraudEvent.user_id == user_id)
        .order_by(FraudEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def get_user_fraud_summary(db: Session, user_id: uuid.UUID) -> dict:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    event_count = (
        db.query(func.count(FraudEvent.id))
        .filter(FraudEvent.user_id == user_id)
        .scalar()
    ) or 0
    override = getattr(user, "fraud_verification_override", False)
    return {
        "user_id": user.id,
        "email": user.email,
        "fraud_risk_score": user.fraud_risk_score,
        "risk_tier": get_risk_tier(user.fraud_risk_score),
        "verification_blocked": user.fraud_risk_score >= BLOCK_THRESHOLD and not override,
        "fraud_verification_override": override,
        "event_count": event_count,
    }

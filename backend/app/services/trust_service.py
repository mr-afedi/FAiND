"""
TrustService — canonical entry point for ALL trust score changes (Section 17).

Rules:
- Every trust change MUST go through apply_trust_delta — never update trust_score directly.
- Trust score is frozen (no changes applied) while a user is suspended (Section 17.1).
- All changes are logged to the trust_events table for full audit history.
- Trust score and fraud_risk_score are stored on the User row for fast reads.
- TrustService does NOT enforce ownership or permissions — callers are responsible.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models.user import User, AccountStatus
from app.models.trust_event import TrustEvent, TrustEventReason


# ── Trust tier helper (Section 17.2) ─────────────────────────────────────────

def get_trust_tier(score: int) -> str:
    """Return the public tier label for a given raw trust score."""
    if score >= 100:
        return "Community Champion"
    if score >= 51:
        return "Reliable Member"
    if score >= 21:
        return "Trusted Member"
    return "New Member"


# ── Core mutation ─────────────────────────────────────────────────────────────

def apply_trust_delta(
    db: Session,
    user_id: uuid.UUID,
    delta: int,
    reason: TrustEventReason,
    reference_id: Optional[uuid.UUID] = None,
    applied_by_id: Optional[uuid.UUID] = None,
) -> Optional[TrustEvent]:
    """
    Apply a trust score change for a user.

    Returns the TrustEvent record on success, or None if the change was
    skipped (e.g. user is suspended — score frozen per Section 17.1).

    Does NOT commit — caller is responsible for the transaction, so this
    can be chained with other DB writes in the same commit (e.g. create
    an item + award trust in one atomic transaction).
    """
    user: Optional[User] = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise LookupError(f"User {user_id} not found")

    # Score frozen during suspension (Section 17.1)
    if user.status == AccountStatus.SUSPENDED:
        return None

    user.trust_score = max(0, user.trust_score + delta)

    event = TrustEvent(
        user_id=user_id,
        delta=delta,
        reason=reason,
        reference_id=reference_id,
        applied_by_id=applied_by_id,
    )
    db.add(event)
    return event


# ── Convenience wrappers for each trust event type ────────────────────────────

def award_found_item_posted(
    db: Session, user_id: uuid.UUID, item_id: uuid.UUID
) -> Optional[TrustEvent]:
    """+2 when a found item is successfully posted (Section 7.2)."""
    return apply_trust_delta(
        db, user_id, delta=+2,
        reason=TrustEventReason.FOUND_ITEM_POSTED,
        reference_id=item_id,
    )


def award_successful_return(
    db: Session, user_id: uuid.UUID, item_id: uuid.UUID
) -> Optional[TrustEvent]:
    """+5 for the finder when an item is successfully returned (Section 15.3)."""
    return apply_trust_delta(
        db, user_id, delta=+5,
        reason=TrustEventReason.SUCCESSFUL_RETURN,
        reference_id=item_id,
    )


def penalise_failed_verification(
    db: Session, user_id: uuid.UUID, attempt_number: int, item_id: uuid.UUID
) -> Optional[TrustEvent]:
    """
    -3 on the 2nd and 3rd failed verification attempts (Section 12.6).
    No penalty on the first failure.
    """
    if attempt_number == 2:
        return apply_trust_delta(
            db, user_id, delta=-3,
            reason=TrustEventReason.FAILED_VERIFICATION_2ND,
            reference_id=item_id,
        )
    if attempt_number >= 3:
        return apply_trust_delta(
            db, user_id, delta=-3,
            reason=TrustEventReason.FAILED_VERIFICATION_3RD,
            reference_id=item_id,
        )
    return None


def penalise_false_claim(
    db: Session, user_id: uuid.UUID, item_id: uuid.UUID,
    applied_by_id: Optional[uuid.UUID] = None
) -> Optional[TrustEvent]:
    """-10 for confirmed false claims (score < 0.30 or admin-confirmed, Section 12.8)."""
    return apply_trust_delta(
        db, user_id, delta=-10,
        reason=TrustEventReason.FALSE_CLAIM_CONFIRMED,
        reference_id=item_id,
        applied_by_id=applied_by_id,
    )


def penalise_fraud_confirmed(
    db: Session, user_id: uuid.UUID,
    applied_by_id: Optional[uuid.UUID] = None
) -> Optional[TrustEvent]:
    """-20 for admin-confirmed fraud (Section 17.1)."""
    return apply_trust_delta(
        db, user_id, delta=-20,
        reason=TrustEventReason.FRAUD_CONFIRMED,
        applied_by_id=applied_by_id,
    )


def penalise_user_report_received(
    db: Session, user_id: uuid.UUID, report_count: int,
    reporter_id: Optional[uuid.UUID] = None
) -> Optional[TrustEvent]:
    """
    -5 per user report received AFTER the first (Section 17.1).
    The first report does not deduct trust.
    """
    if report_count <= 1:
        return None
    return apply_trust_delta(
        db, user_id, delta=-5,
        reason=TrustEventReason.USER_REPORT_RECEIVED,
        reference_id=reporter_id,
    )


def admin_adjust_trust(
    db: Session, user_id: uuid.UUID, delta: int, admin_id: uuid.UUID
) -> Optional[TrustEvent]:
    """Discretionary admin adjustment — signed delta, any value."""
    return apply_trust_delta(
        db, user_id, delta=delta,
        reason=TrustEventReason.ADMIN_ADJUSTMENT,
        applied_by_id=admin_id,
    )


# ── Read helpers ──────────────────────────────────────────────────────────────

def get_user_trust_events(
    db: Session,
    user_id: uuid.UUID,
    skip: int = 0,
    limit: int = 20,
) -> list[TrustEvent]:
    """Return paginated trust event history for a user, newest first."""
    return (
        db.query(TrustEvent)
        .filter(TrustEvent.user_id == user_id)
        .order_by(TrustEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

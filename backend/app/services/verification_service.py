"""
Ownership Verification Service — Path A (Section 12, V4.2).

Path A flow:
  Lost item owner answers the FINDER's hidden questions on the matched found item.
  Score > 0.70 → auto-approve + unlock chat (Path A/C hidden-answer verification).
  Score 0.50–0.70 → admin review queue.
  Score < 0.50 → rejected.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.models.item import Item, ItemStatus
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.verification_attempt import (
    VerificationAttempt,
    VerificationPath,
    VerificationResult,
)
from app.models.conversation import Conversation, ConversationStatus
from app.models.user import User
from app.schemas.verification import (
    PathAFormResponse,
    PathASubmitRequest,
    PathASubmitResponse,
    VerificationQuestionForm,
    VerificationStatusResponse,
    AnswerSubmission,
)
from app.utils.encryption import decrypt
from app.services import matching_service, trust_service, notification_service, fraud_service
from app.services import matching_service as ms

MAX_ATTEMPTS_24H = 3
MATCH_TIMEOUT_DAYS = 14

APPROVE_THRESHOLD = 0.70   # Path A/C: score must be > this (relaxed from 0.75 for semantic answers)
REVIEW_THRESHOLD = 0.50    # 0.50–0.70 → admin review
FALSE_CLAIM_THRESHOLD = 0.30  # Section 12.8

# Path A + C weights (Section 12.3, V4.2)
_W_HIDDEN = 0.70
_W_DESC = 0.30


def _attempts_in_window(db: Session, user_id: uuid.UUID, lost_item_id: uuid.UUID) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.user_id == user_id,
            VerificationAttempt.lost_item_id == lost_item_id,
            VerificationAttempt.path == VerificationPath.PATH_A,
            VerificationAttempt.created_at >= since,
        )
        .count()
    )


def _failed_attempts_in_window(db: Session, user_id: uuid.UUID, lost_item_id: uuid.UUID) -> int:
    since = datetime.now(timezone.utc) - timedelta(hours=24)
    return (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.user_id == user_id,
            VerificationAttempt.lost_item_id == lost_item_id,
            VerificationAttempt.path == VerificationPath.PATH_A,
            VerificationAttempt.result == VerificationResult.REJECTED,
            VerificationAttempt.created_at >= since,
        )
        .count()
    )


def _get_match_for_owner(
    db: Session, match_id: uuid.UUID, user: User
) -> PotentialMatch:
    match = (
        db.query(PotentialMatch)
        .options(
            joinedload(PotentialMatch.lost_item),
            joinedload(PotentialMatch.found_item).joinedload(Item.hidden_questions),
        )
        .filter(PotentialMatch.id == match_id)
        .first()
    )
    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    if match.lost_item.posted_by_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if match.university_id != user.university_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return match


def compute_path_a_score(
    found_item: Item,
    submitted_answers: dict[uuid.UUID, str],
) -> tuple[float, dict]:
    """
    Path A/C ownership score (Section 12.3, V4.2).
    Hidden 0.70: mean similarity(owner answer, finder stored answer) per question.
    Description 0.30: combined owner answers vs found item public description.
    """
    questions = sorted(found_item.hidden_questions, key=lambda q: q.position)
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This found item has no verification questions.",
        )

    hidden_scores: list[float] = []
    for q in questions:
        if q.id not in submitted_answers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="All verification questions must be answered.",
            )
        stored = decrypt(q.answer)
        submitted = submitted_answers[q.id].strip()
        pair_score = ms.description_similarity(submitted, stored)
        hidden_scores.append(pair_score)
        print(
            f"[Verification] Q{q.position} hidden-answer similarity={pair_score:.4f}",
            flush=True,
        )
        print(f"  finder answer: {stored!r}", flush=True)
        print(f"  owner answer:  {submitted!r}", flush=True)

    hidden_avg = sum(hidden_scores) / len(hidden_scores)

    combined_text = " ".join(submitted_answers[q.id].strip() for q in questions)
    desc_score = ms.description_similarity(combined_text, found_item.public_description)

    total = _W_HIDDEN * hidden_avg + _W_DESC * desc_score
    total = max(0.0, min(1.0, float(total)))

    print(
        f"[Verification] hidden_avg={hidden_avg:.4f} × {_W_HIDDEN}"
        f" + desc={desc_score:.4f} × {_W_DESC} (answers vs found public)"
        f" = total={total:.4f} (approve if > {APPROVE_THRESHOLD})",
        flush=True,
    )

    breakdown = {
        "hidden_answer": round(float(hidden_avg), 4),
        "description": round(float(desc_score), 4),
        "image": 0.0,
        "total": round(total, 4),
        "weights": {
            "hidden_answer": _W_HIDDEN,
            "description": _W_DESC,
            "image": 0.0,
        },
        "per_question_hidden": [round(s, 4) for s in hidden_scores],
    }
    return total, breakdown


def _classify_score(score: float, hidden_avg: float) -> VerificationResult:
    """
    Path A/C: auto-approve if weighted total > 0.70 OR hidden-answer average > 0.70,
    so strong per-question matches are not downgraded by a weak description factor.
    """
    if score > APPROVE_THRESHOLD or hidden_avg > APPROVE_THRESHOLD:
        return VerificationResult.APPROVED
    if score >= REVIEW_THRESHOLD:
        return VerificationResult.REVIEW
    return VerificationResult.REJECTED


def _conversation_for_match(db: Session, match_id: uuid.UUID) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(Conversation.potential_match_id == match_id)
        .first()
    )


def _unlocked_conversation(db: Session, match_id: uuid.UUID) -> Conversation | None:
    return (
        db.query(Conversation)
        .filter(
            Conversation.potential_match_id == match_id,
            Conversation.status == ConversationStatus.UNLOCKED,
        )
        .first()
    )


def _assert_match_open_for_verification(db: Session, match: PotentialMatch, user: User) -> None:
    """Block re-verification after approval or when another match is already verified."""
    if match.status == PotentialMatchStatus.VERIFIED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification already approved. Open chat to continue.",
        )

    if match.status == PotentialMatchStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your verification is under admin review.",
        )

    if match.status not in (PotentialMatchStatus.ACTIVE,):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This match is no longer open for verification.",
        )

    verified_sibling = (
        db.query(PotentialMatch)
        .filter(
            PotentialMatch.lost_item_id == match.lost_item_id,
            PotentialMatch.id != match.id,
            PotentialMatch.status == PotentialMatchStatus.VERIFIED,
        )
        .first()
    )
    if verified_sibling:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already verified ownership on another matched item.",
        )

    approved_attempt = (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.potential_match_id == match.id,
            VerificationAttempt.user_id == user.id,
            VerificationAttempt.result == VerificationResult.APPROVED,
        )
        .first()
    )
    if approved_attempt and _unlocked_conversation(db, match.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Verification already approved. Open chat to continue.",
        )


def get_path_a_form(db: Session, match_id: uuid.UUID, user: User) -> PathAFormResponse:
    match = _get_match_for_owner(db, match_id, user)
    _assert_match_open_for_verification(db, match, user)

    used = _attempts_in_window(db, user.id, match.lost_item_id)
    remaining = max(0, MAX_ATTEMPTS_24H - used)

    questions = [
        VerificationQuestionForm(
            id=q.id,
            position=q.position,
            question=decrypt(q.question),
        )
        for q in sorted(match.found_item.hidden_questions, key=lambda x: x.position)
    ]
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The finder has not set verification questions for this item.",
        )

    return PathAFormResponse(
        match_id=match.id,
        lost_item_id=match.lost_item_id,
        found_item_id=match.found_item_id,
        found_item_description=match.found_item.public_description,
        found_item_location=match.found_item.location_label,
        questions=questions,
        attempts_used_24h=used,
        attempts_remaining_24h=remaining,
    )


def get_verification_status(
    db: Session, match_id: uuid.UUID, user: User
) -> VerificationStatusResponse:
    match = _get_match_for_owner(db, match_id, user)
    used = _attempts_in_window(db, user.id, match.lost_item_id)
    remaining = max(0, MAX_ATTEMPTS_24H - used)

    latest = (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.potential_match_id == match_id,
            VerificationAttempt.user_id == user.id,
        )
        .order_by(VerificationAttempt.created_at.desc())
        .first()
    )
    conv = _conversation_for_match(db, match_id)

    verified_sibling = (
        db.query(PotentialMatch)
        .filter(
            PotentialMatch.lost_item_id == match.lost_item_id,
            PotentialMatch.id != match.id,
            PotentialMatch.status == PotentialMatchStatus.VERIFIED,
        )
        .first()
    )
    unlocked = conv if conv and conv.status == ConversationStatus.UNLOCKED else None
    can_verify = (
        match.status == PotentialMatchStatus.ACTIVE
        and remaining > 0
        and not unlocked
        and not verified_sibling
        and not (latest and latest.result == VerificationResult.APPROVED)
    )

    return VerificationStatusResponse(
        match_id=match.id,
        match_status=match.status.value,
        latest_result=latest.result if latest else None,
        latest_score=latest.ownership_score if latest else None,
        conversation_id=unlocked.id if unlocked else None,
        attempts_used_24h=used,
        attempts_remaining_24h=remaining,
        can_verify=can_verify,
    )


def submit_path_a(
    db: Session,
    match_id: uuid.UUID,
    user: User,
    payload: PathASubmitRequest,
) -> PathASubmitResponse:
    fraud_service.assert_can_attempt_verification(db, user)
    match = _get_match_for_owner(db, match_id, user)

    if match.status != PotentialMatchStatus.VERIFIED:
        _assert_match_open_for_verification(db, match, user)

    if match.status == PotentialMatchStatus.VERIFIED:
        conv = _conversation_for_match(db, match_id)
        return PathASubmitResponse(
            result=VerificationResult.APPROVED,
            ownership_score=1.0,
            score_breakdown={},
            attempts_remaining_24h=0,
            conversation_id=conv.id if conv else None,
            message="Verification already approved. Chat is unlocked.",
        )

    if match.status != PotentialMatchStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This match is no longer open for verification.",
        )

    used = _attempts_in_window(db, user.id, match.lost_item_id)
    if used >= MAX_ATTEMPTS_24H:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maximum 3 verification attempts per item per 24 hours reached.",
        )

    # Validate question IDs belong to the matched found item (finder's questions)
    question_ids = {q.id for q in match.found_item.hidden_questions}
    submitted_map: dict[uuid.UUID, str] = {}
    for ans in payload.answers:
        if ans.question_id not in question_ids:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid question ID in submission.",
            )
        submitted_map[ans.question_id] = ans.answer

    if len(submitted_map) != len(question_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="All verification questions must be answered.",
        )

    # Mark verification in progress (Section 22 status reference)
    if match.lost_item.status == ItemStatus.POTENTIAL_MATCH:
        match.lost_item.status = ItemStatus.UNDER_VERIFICATION

    score, breakdown = compute_path_a_score(match.found_item, submitted_map)
    hidden_avg = breakdown["hidden_answer"]
    result = _classify_score(score, hidden_avg)

    attempt = VerificationAttempt(
        university_id=user.university_id,
        user_id=user.id,
        potential_match_id=match.id,
        lost_item_id=match.lost_item_id,
        found_item_id=match.found_item_id,
        path=VerificationPath.PATH_A,
        ownership_score=round(score, 4),
        score_breakdown=breakdown,
        result=result,
    )
    db.add(attempt)
    db.flush()

    conversation_id: uuid.UUID | None = None
    message: str

    if result == VerificationResult.APPROVED:
        # Section 12.7 — dispute if another match on same lost item already verified
        other_verified = (
            db.query(PotentialMatch)
            .filter(
                PotentialMatch.lost_item_id == match.lost_item_id,
                PotentialMatch.id != match.id,
                PotentialMatch.status == PotentialMatchStatus.VERIFIED,
            )
            .first()
        )
        if other_verified:
            match.lost_item.status = ItemStatus.UNDER_DISPUTE
            match.status = PotentialMatchStatus.PAUSED
            matching_service.pause_matches_for_item(db, match.lost_item_id)
            message = (
                "Multiple matches were approved for this item. "
                "An admin will review — chat is not unlocked yet."
            )
            from app.services import admin_notification_service

            admin_notification_service.notify_admins_verification_dispute(
                db, match_id=match.id, lost_item_id=match.lost_item_id
            )
            notification_service.notify_verification_review(
                db,
                user_id=user.id,
                match_id=match.id,
                lost_item_id=match.lost_item_id,
            )
        else:
            match.status = PotentialMatchStatus.VERIFIED
            match.lost_item.status = ItemStatus.POTENTIAL_MATCH

            conv = Conversation(
                university_id=user.university_id,
                potential_match_id=match.id,
                lost_item_id=match.lost_item_id,
                found_item_id=match.found_item_id,
                lost_owner_id=match.lost_item.posted_by_id,
                found_owner_id=match.found_item.posted_by_id,
                status=ConversationStatus.UNLOCKED,
                unlocked_at=datetime.now(timezone.utc),
            )
            db.add(conv)
            db.flush()
            conversation_id = conv.id

            notification_service.notify_verification_passed(
                db,
                lost_owner_id=match.lost_item.posted_by_id,
                found_owner_id=match.found_item.posted_by_id,
                match_id=match.id,
                conversation_id=conv.id,
                lost_item_id=match.lost_item_id,
                found_item_id=match.found_item_id,
            )
            matching_service.expire_superseded_matches(
                db, match.lost_item_id, match.id
            )
            message = "Verification passed! Chat is now unlocked."

    elif result == VerificationResult.REVIEW:
        match.status = PotentialMatchStatus.PENDING_REVIEW
        match.lost_item.status = ItemStatus.UNDER_VERIFICATION
        from app.services import admin_notification_service

        admin_notification_service.notify_admins_claim_in_review(
            db, match_id=match.id, path="path_a"
        )
        notification_service.notify_verification_review(
            db,
            user_id=user.id,
            match_id=match.id,
            lost_item_id=match.lost_item_id,
        )
        message = (
            "Your answers need admin review (score in the 50–75% range). "
            "We'll notify you when a decision is made."
        )

    else:
        # Rejected
        match.lost_item.status = ItemStatus.POTENTIAL_MATCH
        failed_before = _failed_attempts_in_window(db, user.id, match.lost_item_id)
        attempt_num = failed_before + 1  # this rejection counts

        if attempt_num == 2:
            trust_service.penalise_failed_verification(
                db, user.id, attempt_number=2, item_id=match.lost_item_id
            )
        elif attempt_num >= 3:
            trust_service.penalise_failed_verification(
                db, user.id, attempt_number=3, item_id=match.lost_item_id
            )

        fraud_service.on_verification_rejected(db, attempt=attempt)

        if score < FALSE_CLAIM_THRESHOLD:
            trust_service.penalise_false_claim(db, user.id, match.lost_item_id)

        remaining = max(0, MAX_ATTEMPTS_24H - (used + 1))
        notification_service.notify_verification_failed(
            db,
            user_id=user.id,
            match_id=match.id,
            lost_item_id=match.lost_item_id,
            attempts_remaining=remaining,
        )
        message = (
            f"Verification failed (score {int(score * 100)}%). "
            f"You have {remaining} attempt(s) remaining in the next 24 hours."
        )

    db.commit()

    remaining_after = max(0, MAX_ATTEMPTS_24H - (used + 1))
    return PathASubmitResponse(
        result=result,
        ownership_score=round(score, 4),
        score_breakdown=breakdown,
        attempts_remaining_24h=remaining_after,
        conversation_id=conversation_id,
        message=message,
    )


def expire_stale_potential_matches(db: Session) -> int:
    """
    Section 21.3 — revert POTENTIAL_MATCH to OPEN after 14 days with no verification attempt.
    Called hourly by APScheduler.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=MATCH_TIMEOUT_DAYS)

    stale_matches = (
        db.query(PotentialMatch)
        .options(joinedload(PotentialMatch.lost_item))
        .filter(
            PotentialMatch.status == PotentialMatchStatus.ACTIVE,
            PotentialMatch.created_at < cutoff,
        )
        .all()
    )

    expired_count = 0
    for match in stale_matches:
        has_attempt = (
            db.query(VerificationAttempt)
            .filter(VerificationAttempt.potential_match_id == match.id)
            .first()
        )
        if has_attempt:
            continue

        match.status = PotentialMatchStatus.EXPIRED
        if match.lost_item.status == ItemStatus.POTENTIAL_MATCH:
            match.lost_item.status = ItemStatus.OPEN

        notification_service.notify_potential_match_expired(
            db,
            owner_id=match.lost_item.posted_by_id,
            lost_item_id=match.lost_item_id,
            match_id=match.id,
        )
        expired_count += 1
        print(
            f"[Lifecycle] POTENTIAL_MATCH expired — match={match.id} lost_item={match.lost_item_id}",
            flush=True,
        )

    if expired_count:
        db.commit()
    return expired_count

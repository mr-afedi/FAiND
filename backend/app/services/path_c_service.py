"""
Path C — This Might Be Mine (V4.3 flow, V4.4 scoring).

Owner answers the finder's hidden questions only (hidden-answer score, weight 1.0).
Creates a bridge lost item + match for chat records.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemType, ItemStatus
from app.models.user import User, AccountStatus
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.verification_attempt import (
    VerificationAttempt,
    VerificationPath,
    VerificationResult,
)
from app.models.conversation import Conversation, ConversationStatus
from app.models.this_might_be_mine_claim import ThisMightBeMineClaim
from app.schemas.path_c import PathCFormResponse, PathCSubmitRequest, PathCSubmitResponse
from app.schemas.verification import VerificationQuestionForm
from app.utils.encryption import decrypt
from app.services import matching_service as ms
from app.services import trust_service, notification_service

MAX_ATTEMPTS = 3
FALSE_CLAIM_THRESHOLD = 0.30
_LOST_BRIDGE_ACTIVE_DAYS = 45

# Path C scoring (V4.4) — hidden answers only
_PATH_C_APPROVE_THRESHOLD = 0.70
_PATH_C_REVIEW_LOW = 0.50
_PATH_C_AUTO_APPROVE_HIDDEN = 0.80
_PATH_C_AUTO_REJECT_HIDDEN = 0.40

_CLAIMABLE_FOUND_STATUSES = [
    ItemStatus.FOUND,
    ItemStatus.POTENTIAL_MATCH,
    ItemStatus.UNDER_VERIFICATION,
    ItemStatus.UNDER_DISPUTE,
]


def _path_c_attempts(
    db: Session, user_id: uuid.UUID, found_item_id: uuid.UUID
) -> list[VerificationAttempt]:
    return (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.user_id == user_id,
            VerificationAttempt.found_item_id == found_item_id,
            VerificationAttempt.path == VerificationPath.PATH_C,
        )
        .order_by(VerificationAttempt.created_at.asc())
        .all()
    )


def _attempt_counter_paused(
    db: Session, user_id: uuid.UUID, found_item_id: uuid.UUID
) -> bool:
    attempts = _path_c_attempts(db, user_id, found_item_id)
    if len(attempts) < 3:
        return False
    third = attempts[2]
    if third.result != VerificationResult.REVIEW:
        return False
    match = (
        db.query(PotentialMatch)
        .filter(PotentialMatch.id == third.potential_match_id)
        .first()
    )
    return bool(match and match.status == PotentialMatchStatus.PENDING_REVIEW)


def _failed_attempts_count(db: Session, user_id: uuid.UUID, found_item_id: uuid.UUID) -> int:
    return sum(
        1
        for a in _path_c_attempts(db, user_id, found_item_id)
        if a.result == VerificationResult.REJECTED
    )


def _prior_attempt_scores(
    db: Session, user_id: uuid.UUID, found_item_id: uuid.UUID
) -> list[float]:
    return [float(a.ownership_score) for a in _path_c_attempts(db, user_id, found_item_id)]


def _check_gradual_improvement(scores: list[float]) -> bool:
    if len(scores) < 2:
        return False
    return all(scores[i] < scores[i + 1] for i in range(len(scores) - 1))


def _verification_result_value(result: VerificationResult | str) -> str:
    if isinstance(result, VerificationResult):
        return result.value
    return str(result).lower()


def _match_status_value(status: PotentialMatchStatus | str | None) -> str | None:
    if status is None:
        return None
    if isinstance(status, PotentialMatchStatus):
        return status.value
    return str(status).lower()


def _status_from_latest_claim(
    claim: ThisMightBeMineClaim,
    match: PotentialMatch | None,
    conversation: Conversation | None,
) -> tuple[str | None, uuid.UUID | None]:
    claim_result = _verification_result_value(claim.result)
    match_status = _match_status_value(match.status) if match else None

    if claim_result == "review":
        return "under_review", None

    if claim_result == "approved":
        if match_status == "verified":
            return "approved", (conversation.id if conversation else None)
        if match_status in ("pending_review", "paused"):
            return "under_review", None

    if claim_result == "rejected":
        return "rejected", None

    return None, None


def resolve_viewer_path_c_status(
    db: Session,
    viewer_id: uuid.UUID | None,
    found_item_id: uuid.UUID,
) -> tuple[str | None, uuid.UUID | None]:
    """Path C UI state for a user viewing a found item (not the finder)."""
    if not viewer_id:
        return None, None

    latest = (
        db.query(ThisMightBeMineClaim)
        .filter(
            ThisMightBeMineClaim.user_id == viewer_id,
            ThisMightBeMineClaim.found_item_id == found_item_id,
        )
        .order_by(ThisMightBeMineClaim.created_at.desc())
        .first()
    )

    if latest:
        match = (
            db.query(PotentialMatch)
            .filter(PotentialMatch.id == latest.potential_match_id)
            .first()
        )
        conv = None
        if match:
            conv = (
                db.query(Conversation)
                .filter(
                    Conversation.potential_match_id == match.id,
                    Conversation.status == ConversationStatus.UNLOCKED,
                )
                .first()
            )
        status, conv_id = _status_from_latest_claim(latest, match, conv)
        if status == "rejected":
            if len(_path_c_attempts(db, viewer_id, found_item_id)) >= MAX_ATTEMPTS:
                return "exhausted", None
            return "rejected", None
        if status:
            return status, conv_id

    if _attempt_counter_paused(db, viewer_id, found_item_id):
        return "under_review", None

    if len(_path_c_attempts(db, viewer_id, found_item_id)) >= MAX_ATTEMPTS:
        return "exhausted", None

    return None, None


def resolve_viewer_path_c_statuses_batch(
    db: Session,
    viewer_id: uuid.UUID | None,
    found_item_ids: list[uuid.UUID],
) -> dict[uuid.UUID, tuple[str | None, uuid.UUID | None]]:
    if not viewer_id or not found_item_ids:
        return {}

    out: dict[uuid.UUID, tuple[str | None, uuid.UUID | None]] = {
        fid: (None, None) for fid in found_item_ids
    }

    claims = (
        db.query(ThisMightBeMineClaim)
        .filter(
            ThisMightBeMineClaim.user_id == viewer_id,
            ThisMightBeMineClaim.found_item_id.in_(found_item_ids),
        )
        .order_by(ThisMightBeMineClaim.created_at.desc())
        .all()
    )
    latest_by_item: dict[uuid.UUID, ThisMightBeMineClaim] = {}
    for claim in claims:
        if claim.found_item_id not in latest_by_item:
            latest_by_item[claim.found_item_id] = claim

    if latest_by_item:
        match_ids = [c.potential_match_id for c in latest_by_item.values()]
        matches = {
            m.id: m
            for m in db.query(PotentialMatch).filter(PotentialMatch.id.in_(match_ids)).all()
        }
        convs: dict[uuid.UUID, Conversation] = {}
        for conv in (
            db.query(Conversation)
            .filter(
                Conversation.potential_match_id.in_(match_ids),
                Conversation.status == ConversationStatus.UNLOCKED,
            )
            .all()
        ):
            convs[conv.potential_match_id] = conv

        for fid, claim in latest_by_item.items():
            match = matches.get(claim.potential_match_id)
            conv = convs.get(claim.potential_match_id)
            status, conv_id = _status_from_latest_claim(claim, match, conv)
            if status == "rejected":
                if len(_path_c_attempts(db, viewer_id, fid)) >= MAX_ATTEMPTS:
                    out[fid] = ("exhausted", None)
                else:
                    out[fid] = ("rejected", None)
            elif status:
                out[fid] = (status, conv_id)

    for fid in found_item_ids:
        if out[fid][0] is not None:
            continue
        if _attempt_counter_paused(db, viewer_id, fid):
            out[fid] = ("under_review", None)
            continue
        if len(_path_c_attempts(db, viewer_id, fid)) >= MAX_ATTEMPTS:
            out[fid] = ("exhausted", None)

    return out


def _get_found_item_for_claim(db: Session, found_item_id: uuid.UUID, user: User) -> Item:
    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
        .filter(Item.id == found_item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    if item.item_type != ItemType.FOUND:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This Might Be Mine is only available on found item posts.",
        )
    if item.university_id != user.university_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if item.posted_by_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot claim your own found item post.",
        )
    if item.status not in _CLAIMABLE_FOUND_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This found item is not accepting claims.",
        )
    questions = sorted(item.hidden_questions, key=lambda q: q.position)
    if len(questions) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This found item cannot be verified (missing hidden questions).",
        )
    return item


def _owner_has_verified_claim(db: Session, user_id: uuid.UUID, found_item_id: uuid.UUID) -> bool:
    return (
        db.query(ThisMightBeMineClaim)
        .join(PotentialMatch, ThisMightBeMineClaim.potential_match_id == PotentialMatch.id)
        .filter(
            ThisMightBeMineClaim.user_id == user_id,
            ThisMightBeMineClaim.found_item_id == found_item_id,
            ThisMightBeMineClaim.result == VerificationResult.APPROVED,
            PotentialMatch.status == PotentialMatchStatus.VERIFIED,
        )
        .first()
        is not None
    )


def _answers_map(payload: PathCSubmitRequest) -> dict[uuid.UUID, str]:
    return {a.question_id: a.answer.strip() for a in payload.answers}


def compute_path_c_score(
    found_item: Item,
    submitted_answers: dict[uuid.UUID, str],
) -> tuple[float, dict]:
    """Hidden-answer similarity only (weight 1.0)."""
    questions = sorted(found_item.hidden_questions, key=lambda q: q.position)
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This found item has no verification questions.",
        )

    hidden_scores: list[float] = []
    per_question: list[dict] = []
    for q in questions:
        if q.id not in submitted_answers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="All verification questions must be answered.",
            )
        stored = decrypt(q.answer) or ""
        submitted = submitted_answers[q.id].strip()
        pair_score = float(ms.description_similarity(submitted, stored))
        hidden_scores.append(pair_score)
        per_question.append(
            {
                "question_id": str(q.id),
                "position": q.position,
                "similarity": round(pair_score, 4),
            }
        )

    hidden_avg = sum(hidden_scores) / len(hidden_scores)
    total = max(0.0, min(1.0, float(hidden_avg)))

    breakdown = {
        "hidden_answer": round(float(hidden_avg), 4),
        "total": round(total, 4),
        "weights": {"hidden_answer": 1.0},
        "per_question_similarity": per_question,
        "per_question_hidden": [round(s, 4) for s in hidden_scores],
    }
    return total, breakdown


def _classify_path_c_score(hidden_score: float) -> VerificationResult:
    """V4.4 thresholds and overrides on hidden-answer score."""
    if hidden_score > _PATH_C_AUTO_APPROVE_HIDDEN:
        return VerificationResult.APPROVED
    if hidden_score < _PATH_C_AUTO_REJECT_HIDDEN:
        return VerificationResult.REJECTED
    if hidden_score > _PATH_C_APPROVE_THRESHOLD:
        return VerificationResult.APPROVED
    if hidden_score >= _PATH_C_REVIEW_LOW:
        return VerificationResult.REVIEW
    return VerificationResult.REJECTED


def _build_verification_detail(
    found_item: Item,
    submitted: dict[uuid.UUID, str],
    breakdown: dict,
    prior_scores: list[float],
    overall_score: float,
) -> dict:
    sorted_questions = sorted(found_item.hidden_questions, key=lambda x: x.position)
    sim_by_qid = {
        p["question_id"]: p["similarity"]
        for p in breakdown.get("per_question_similarity", [])
    }
    finder_questions = []
    owner_answers = []
    per_question_similarity = []
    for q in sorted_questions:
        qid = str(q.id)
        finder_questions.append(
            {
                "question_id": qid,
                "position": q.position,
                "question": decrypt(q.question) or "",
                "finder_answer": decrypt(q.answer) or "",
            }
        )
        owner_answers.append(
            {
                "question_id": qid,
                "position": q.position,
                "answer": submitted[q.id],
            }
        )
        per_question_similarity.append(
            {
                "question_id": qid,
                "position": q.position,
                "similarity": sim_by_qid.get(qid, 0.0),
            }
        )
    return {
        "finder_questions": finder_questions,
        "owner_answers": owner_answers,
        "per_question_similarity": per_question_similarity,
        "overall_score": round(overall_score, 4),
        "previous_attempt_scores": [round(s, 4) for s in prior_scores],
    }


def get_path_c_form(db: Session, found_item_id: uuid.UUID, user: User) -> PathCFormResponse:
    found_item = _get_found_item_for_claim(db, found_item_id, user)
    used = len(_path_c_attempts(db, user.id, found_item_id))
    paused = _attempt_counter_paused(db, user.id, found_item_id)
    remaining = max(0, MAX_ATTEMPTS - used)

    if _owner_has_verified_claim(db, user.id, found_item_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an approved claim with chat unlocked for this item.",
        )

    questions = [
        VerificationQuestionForm(
            id=q.id,
            position=q.position,
            question=decrypt(q.question) or "",
        )
        for q in sorted(found_item.hidden_questions, key=lambda x: x.position)
    ]

    return PathCFormResponse(
        found_item_id=found_item.id,
        found_item_public_description=found_item.public_description,
        found_item_location=found_item.location_label,
        questions=questions,
        attempts_used=used,
        attempts_remaining=remaining,
        attempt_counter_paused=paused,
    )


def submit_path_c(
    db: Session,
    found_item_id: uuid.UUID,
    user: User,
    payload: PathCSubmitRequest,
) -> PathCSubmitResponse:
    found_item = _get_found_item_for_claim(db, found_item_id, user)

    if user.status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active.")

    if _owner_has_verified_claim(db, user.id, found_item_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an approved claim for this item.",
        )

    if _attempt_counter_paused(db, user.id, found_item_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your last claim is under admin review. Please wait for a decision.",
        )

    used = len(_path_c_attempts(db, user.id, found_item_id))
    if used >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You have reached the maximum number of attempts for this item.",
        )

    submitted = _answers_map(payload)
    question_ids = {q.id for q in found_item.hidden_questions}
    if set(submitted.keys()) != question_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Answer every verification question exactly once.",
        )

    score, breakdown = compute_path_c_score(found_item, submitted)
    result = _classify_path_c_score(score)

    prior_scores = _prior_attempt_scores(db, user.id, found_item_id)
    attempt_scores = prior_scores + [round(score, 4)]
    verification_detail = _build_verification_detail(
        found_item, submitted, breakdown, prior_scores, score
    )
    if _check_gradual_improvement(attempt_scores):
        user.fraud_risk_score = min(100, user.fraud_risk_score + 10)
        breakdown["gradual_improvement_flag"] = True

    sorted_questions = sorted(found_item.hidden_questions, key=lambda x: x.position)
    owner_answers = [
        {"question_id": str(q.id), "answer": submitted[q.id]}
        for q in sorted_questions
    ]
    bridge_desc = ". ".join(submitted[q.id] for q in sorted_questions)[:1000]

    expiry = datetime.now(timezone.utc) + timedelta(days=_LOST_BRIDGE_ACTIVE_DAYS)
    bridge_lost = Item(
        university_id=user.university_id,
        posted_by_id=user.id,
        item_type=ItemType.LOST,
        status=ItemStatus.OPEN,
        category=found_item.category,
        public_description=bridge_desc or "Path C ownership claim",
        location_id=found_item.location_id,
        location_label=found_item.location_label,
        location_lat=found_item.location_lat,
        location_lng=found_item.location_lng,
        date_occurred=found_item.date_occurred,
        image_urls=[],
        expiry_date=expiry,
        path_c_bridge=True,
    )
    db.add(bridge_lost)
    db.flush()

    match = PotentialMatch(
        university_id=user.university_id,
        lost_item_id=bridge_lost.id,
        found_item_id=found_item.id,
        match_score=round(score, 4),
        score_breakdown={**breakdown, "path": "path_c"},
        status=PotentialMatchStatus.ACTIVE,
    )
    db.add(match)
    db.flush()

    db.add(
        VerificationAttempt(
            university_id=user.university_id,
            user_id=user.id,
            potential_match_id=match.id,
            lost_item_id=bridge_lost.id,
            found_item_id=found_item.id,
            path=VerificationPath.PATH_C,
            ownership_score=round(score, 4),
            score_breakdown=breakdown,
            result=result,
        )
    )

    claim = ThisMightBeMineClaim(
        university_id=user.university_id,
        user_id=user.id,
        found_item_id=found_item.id,
        bridge_lost_item_id=bridge_lost.id,
        potential_match_id=match.id,
        owner_answers=owner_answers,
        attempt_scores=attempt_scores,
        verification_detail=verification_detail,
        ownership_score=round(score, 4),
        score_breakdown=breakdown,
        result=result,
    )
    db.add(claim)
    db.flush()

    notification_service.notify_path_c_claim_received(
        db,
        finder_id=found_item.posted_by_id,
        found_item_id=found_item.id,
        claim_id=claim.id,
    )

    conversation_id: uuid.UUID | None = None
    message: str
    prompt_post_lost = False
    attempt_num = used + 1

    if result == VerificationResult.APPROVED:
        other_verified = (
            db.query(PotentialMatch)
            .filter(
                PotentialMatch.found_item_id == found_item.id,
                PotentialMatch.id != match.id,
                PotentialMatch.status == PotentialMatchStatus.VERIFIED,
            )
            .first()
        )
        if other_verified:
            found_item.status = ItemStatus.UNDER_DISPUTE
            match.status = PotentialMatchStatus.PAUSED
            ms.pause_matches_for_item(db, found_item.id)
            message = (
                "Your claim scored highly, but another claimant was already approved. "
                "An admin will review — chat is not unlocked yet."
            )
            notification_service.notify_path_c_under_review(
                db,
                claimant_id=user.id,
                finder_id=found_item.posted_by_id,
                found_item_id=found_item.id,
                match_id=match.id,
            )
        else:
            match.status = PotentialMatchStatus.VERIFIED
            bridge_lost.status = ItemStatus.POTENTIAL_MATCH
            if found_item.status == ItemStatus.FOUND:
                found_item.status = ItemStatus.POTENTIAL_MATCH

            conv = Conversation(
                university_id=user.university_id,
                potential_match_id=match.id,
                lost_item_id=bridge_lost.id,
                found_item_id=found_item.id,
                lost_owner_id=user.id,
                found_owner_id=found_item.posted_by_id,
                status=ConversationStatus.UNLOCKED,
                unlocked_at=datetime.now(timezone.utc),
            )
            db.add(conv)
            db.flush()
            conversation_id = conv.id

            notification_service.notify_verification_passed(
                db,
                lost_owner_id=user.id,
                found_owner_id=found_item.posted_by_id,
                match_id=match.id,
                conversation_id=conv.id,
                lost_item_id=bridge_lost.id,
                found_item_id=found_item.id,
            )
            message = "Ownership verified! Chat is now unlocked with the finder."
            prompt_post_lost = True

    elif result == VerificationResult.REVIEW:
        match.status = PotentialMatchStatus.PENDING_REVIEW
        bridge_lost.status = ItemStatus.UNDER_VERIFICATION
        if found_item.status == ItemStatus.FOUND:
            found_item.status = ItemStatus.UNDER_VERIFICATION
        notification_service.notify_path_c_under_review(
            db,
            claimant_id=user.id,
            finder_id=found_item.posted_by_id,
            found_item_id=found_item.id,
            match_id=match.id,
        )
        if attempt_num == MAX_ATTEMPTS:
            message = (
                "Your claim is under admin review. Your attempt counter is paused "
                "until an admin decides — you will not be locked out while waiting."
            )
        else:
            message = (
                "Your claim is under admin review (score in the 50–70% range). "
                "We'll notify you when a decision is made."
            )

    else:
        failed_before = _failed_attempts_count(db, user.id, found_item.id)
        fail_num = failed_before + 1
        if fail_num == 2:
            trust_service.penalise_failed_verification(
                db, user.id, attempt_number=2, item_id=found_item.id
            )
        elif fail_num >= 3:
            trust_service.penalise_failed_verification(
                db, user.id, attempt_number=3, item_id=found_item.id
            )
            user.fraud_risk_score = min(100, user.fraud_risk_score + 20)

        if score < FALSE_CLAIM_THRESHOLD:
            trust_service.penalise_false_claim(db, user.id, found_item.id)

        remaining = max(0, MAX_ATTEMPTS - attempt_num)
        notification_service.notify_path_c_rejected(
            db,
            claimant_id=user.id,
            finder_id=found_item.posted_by_id,
            found_item_id=found_item.id,
            match_id=match.id,
            attempts_remaining=remaining,
        )
        message = (
            f"Claim not approved (score {int(score * 100)}%). "
            f"You have {remaining} attempt(s) remaining for this item."
        )

    db.commit()

    remaining_after = max(0, MAX_ATTEMPTS - attempt_num)
    paused_after = attempt_num == MAX_ATTEMPTS and result == VerificationResult.REVIEW

    return PathCSubmitResponse(
        result=result,
        ownership_score=round(score, 4),
        score_breakdown=breakdown,
        attempts_remaining=remaining_after,
        attempt_counter_paused=paused_after,
        conversation_id=conversation_id,
        match_id=match.id,
        claim_id=claim.id,
        message=message,
        prompt_post_lost_item=prompt_post_lost,
    )

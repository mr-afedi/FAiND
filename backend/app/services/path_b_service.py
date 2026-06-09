"""
Path B — I Have This Item (Section 8, V4.3).

Finder answers the lost owner's hidden questions (physical inspection),
plus location and optional photo. Scored with Path B formula (§12.4).
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
from app.models.ihave_this_item_claim import IHaveThisItemClaim
from app.schemas.path_b import PathBFormResponse, PathBSubmitRequest, PathBSubmitResponse
from app.schemas.verification import VerificationQuestionForm
from app.utils.encryption import decrypt
from app.services import matching_service as ms
from app.services import trust_service, notification_service, fraud_service
from app.utils.location_utils import _resolve_location

MAX_ATTEMPTS = 3
APPROVE_THRESHOLD = 0.75
REVIEW_THRESHOLD = 0.50
FALSE_CLAIM_THRESHOLD = 0.30
HIDDEN_AUTO_APPROVE = 0.80
HIDDEN_AUTO_REJECT = 0.40

_W_HIDDEN = 0.70
_W_IMG = 0.15
_W_LOC = 0.15

_CLAIMABLE_LOST_STATUSES = [
    ItemStatus.OPEN,
    ItemStatus.POTENTIAL_MATCH,
    ItemStatus.UNDER_VERIFICATION,
    ItemStatus.UNDER_DISPUTE,
]

_FOUND_BRIDGE_ACTIVE_DAYS = 21


def _path_b_attempts(
    db: Session, user_id: uuid.UUID, lost_item_id: uuid.UUID
) -> list[VerificationAttempt]:
    return (
        db.query(VerificationAttempt)
        .filter(
            VerificationAttempt.user_id == user_id,
            VerificationAttempt.lost_item_id == lost_item_id,
            VerificationAttempt.path == VerificationPath.PATH_B,
        )
        .order_by(VerificationAttempt.created_at.asc())
        .all()
    )


def _attempt_counter_paused(
    db: Session, user_id: uuid.UUID, lost_item_id: uuid.UUID
) -> bool:
    """3rd attempt in admin review — counter paused until decision (V4.3 §12.6)."""
    attempts = _path_b_attempts(db, user_id, lost_item_id)
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


def _failed_attempts_count(db: Session, user_id: uuid.UUID, lost_item_id: uuid.UUID) -> int:
    return sum(
        1
        for a in _path_b_attempts(db, user_id, lost_item_id)
        if a.result == VerificationResult.REJECTED
    )


def _prior_attempt_scores(
    db: Session, user_id: uuid.UUID, lost_item_id: uuid.UUID
) -> list[float]:
    return [float(a.ownership_score) for a in _path_b_attempts(db, user_id, lost_item_id)]


def _check_gradual_improvement(scores: list[float]) -> bool:
    if len(scores) < 2:
        return False
    return all(scores[i] < scores[i + 1] for i in range(len(scores) - 1))


def _get_lost_item_for_claim(db: Session, lost_item_id: uuid.UUID, user: User) -> Item:
    item = (
        db.query(Item)
        .options(joinedload(Item.posted_by), joinedload(Item.hidden_questions))
        .filter(Item.id == lost_item_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    if item.item_type != ItemType.LOST:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="I Have This Item is only available on lost item posts.",
        )
    if item.university_id != user.university_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    if item.posted_by_id == user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot claim your own lost item post.",
        )
    if item.status not in _CLAIMABLE_LOST_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This lost item is not accepting claims.",
        )
    questions = sorted(item.hidden_questions, key=lambda q: q.position)
    if len(questions) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This lost item cannot be verified (missing hidden questions).",
        )
    return item


def _answers_map(payload: PathBSubmitRequest) -> dict[uuid.UUID, str]:
    return {a.question_id: a.answer.strip() for a in payload.answers}


def compute_path_b_score(
    lost_item: Item,
    submitted_answers: dict[uuid.UUID, str],
    claim_image_url: str | None,
    finder_lat: float | None,
    finder_lng: float | None,
) -> tuple[float, dict]:
    """Path B score (V4.3 §12.4): hidden answers, image, location."""
    questions = sorted(lost_item.hidden_questions, key=lambda q: q.position)
    hidden_scores: list[float] = []

    for q in questions:
        if q.id not in submitted_answers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="All verification questions must be answered.",
            )
        stored = decrypt(q.answer) or ""
        submitted = submitted_answers[q.id]
        hidden_scores.append(ms.description_similarity(submitted, stored))

    hidden_avg = sum(hidden_scores) / len(hidden_scores)

    owner_has_photo = bool(lost_item.image_urls)
    finder_has_photo = bool(claim_image_url)

    if owner_has_photo and finder_has_photo:
        img_score = ms.image_similarity(claim_image_url, lost_item.image_urls[0])
        w_hidden, w_img, w_loc = _W_HIDDEN, _W_IMG, _W_LOC
    elif not owner_has_photo:
        img_score = 0.0
        w_hidden, w_img, w_loc = 0.85, 0.0, _W_LOC
    else:
        img_score = 0.0
        base_h, base_l = _W_HIDDEN, _W_LOC
        share = _W_IMG
        denom = base_h + base_l
        w_hidden = base_h + share * (base_h / denom)
        w_loc = base_l + share * (base_l / denom)
        w_img = 0.0

    loc_score = ms.location_proximity_score(
        finder_lat,
        finder_lng,
        lost_item.location_lat,
        lost_item.location_lng,
    )

    total = w_hidden * hidden_avg + w_img * img_score + w_loc * loc_score
    total = max(0.0, min(1.0, float(total)))

    breakdown = {
        "hidden_answer": round(float(hidden_avg), 4),
        "image": round(float(img_score), 4),
        "location": round(float(loc_score), 4),
        "total": round(total, 4),
        "weights": {
            "hidden_answer": round(float(w_hidden), 4),
            "image": round(float(w_img), 4),
            "location": round(float(w_loc), 4),
        },
        "per_question_hidden": [round(s, 4) for s in hidden_scores],
    }
    return total, breakdown


def _classify_path_b_score(total: float, hidden_avg: float) -> VerificationResult:
    if hidden_avg > HIDDEN_AUTO_APPROVE:
        return VerificationResult.APPROVED
    if hidden_avg < HIDDEN_AUTO_REJECT:
        return VerificationResult.REJECTED
    if total > APPROVE_THRESHOLD:
        return VerificationResult.APPROVED
    if total >= REVIEW_THRESHOLD:
        return VerificationResult.REVIEW
    return VerificationResult.REJECTED


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
    claim: IHaveThisItemClaim,
    match: PotentialMatch | None,
    conversation: Conversation | None,
) -> tuple[str | None, uuid.UUID | None]:
    """Map latest Path B claim + match to viewer-facing status."""
    claim_result = _verification_result_value(claim.result)
    match_status = _match_status_value(match.status) if match else None

    if claim_result == "review":
        return "under_review", None

    if claim_result == "approved":
        if match_status == "verified":
            conv_id = conversation.id if conversation else None
            return "approved", conv_id
        if match_status in ("pending_review", "paused"):
            return "under_review", None

    if claim_result == "rejected":
        return "rejected", None

    return None, None


def resolve_viewer_path_b_status(
    db: Session,
    viewer_id: uuid.UUID | None,
    lost_item_id: uuid.UUID,
) -> tuple[str | None, uuid.UUID | None]:
    """Path B UI state for a user viewing a lost item (not the owner)."""
    if not viewer_id:
        return None, None

    if _attempt_counter_paused(db, viewer_id, lost_item_id):
        return "under_review", None

    latest = (
        db.query(IHaveThisItemClaim)
        .filter(
            IHaveThisItemClaim.user_id == viewer_id,
            IHaveThisItemClaim.lost_item_id == lost_item_id,
        )
        .order_by(IHaveThisItemClaim.created_at.desc())
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
            used = len(_path_b_attempts(db, viewer_id, lost_item_id))
            if used >= MAX_ATTEMPTS:
                return "exhausted", None
            return "rejected", None
        if status:
            return status, conv_id

    if _attempt_counter_paused(db, viewer_id, lost_item_id):
        return "under_review", None

    used = len(_path_b_attempts(db, viewer_id, lost_item_id))
    if used >= MAX_ATTEMPTS:
        return "exhausted", None
    return None, None


def resolve_viewer_path_b_statuses_batch(
    db: Session,
    viewer_id: uuid.UUID | None,
    lost_item_ids: list[uuid.UUID],
) -> dict[uuid.UUID, tuple[str | None, uuid.UUID | None]]:
    """Batch Path B viewer status for browse/homepage cards."""
    if not viewer_id or not lost_item_ids:
        return {}

    out: dict[uuid.UUID, tuple[str | None, uuid.UUID | None]] = {
        lid: (None, None) for lid in lost_item_ids
    }

    claims = (
        db.query(IHaveThisItemClaim)
        .filter(
            IHaveThisItemClaim.user_id == viewer_id,
            IHaveThisItemClaim.lost_item_id.in_(lost_item_ids),
        )
        .order_by(IHaveThisItemClaim.created_at.desc())
        .all()
    )
    latest_by_item: dict[uuid.UUID, IHaveThisItemClaim] = {}
    for claim in claims:
        if claim.lost_item_id not in latest_by_item:
            latest_by_item[claim.lost_item_id] = claim

    if not latest_by_item:
        for lid in lost_item_ids:
            if out[lid][0] == "under_review":
                continue
            if len(_path_b_attempts(db, viewer_id, lid)) >= MAX_ATTEMPTS:
                out[lid] = ("exhausted", None)
        return out

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

    for lid, claim in latest_by_item.items():
        match = matches.get(claim.potential_match_id)
        conv = convs.get(claim.potential_match_id)
        status, conv_id = _status_from_latest_claim(claim, match, conv)
        if status == "rejected":
            if len(_path_b_attempts(db, viewer_id, lid)) >= MAX_ATTEMPTS:
                out[lid] = ("exhausted", None)
            else:
                out[lid] = ("rejected", None)
        elif status:
            out[lid] = (status, conv_id)

    for lid in lost_item_ids:
        if out[lid][0] is not None:
            continue
        if _attempt_counter_paused(db, viewer_id, lid):
            out[lid] = ("under_review", None)
            continue
        if len(_path_b_attempts(db, viewer_id, lid)) >= MAX_ATTEMPTS:
            out[lid] = ("exhausted", None)

    return out


def _finder_has_verified_claim(db: Session, user_id: uuid.UUID, lost_item_id: uuid.UUID) -> bool:
    return (
        db.query(IHaveThisItemClaim)
        .join(PotentialMatch, IHaveThisItemClaim.potential_match_id == PotentialMatch.id)
        .filter(
            IHaveThisItemClaim.user_id == user_id,
            IHaveThisItemClaim.lost_item_id == lost_item_id,
            IHaveThisItemClaim.result == VerificationResult.APPROVED,
            PotentialMatch.status == PotentialMatchStatus.VERIFIED,
        )
        .first()
        is not None
    )


def get_path_b_form(db: Session, lost_item_id: uuid.UUID, user: User) -> PathBFormResponse:
    lost_item = _get_lost_item_for_claim(db, lost_item_id, user)
    used = len(_path_b_attempts(db, user.id, lost_item_id))
    paused = _attempt_counter_paused(db, user.id, lost_item_id)
    remaining = max(0, MAX_ATTEMPTS - used)

    if _finder_has_verified_claim(db, user.id, lost_item_id):
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
        for q in sorted(lost_item.hidden_questions, key=lambda x: x.position)
    ]

    return PathBFormResponse(
        lost_item_id=lost_item.id,
        lost_item_public_description=lost_item.public_description,
        lost_item_location=lost_item.location_label,
        questions=questions,
        attempts_used=used,
        attempts_remaining=remaining,
        attempt_counter_paused=paused,
    )


def submit_path_b(
    db: Session,
    lost_item_id: uuid.UUID,
    user: User,
    payload: PathBSubmitRequest,
) -> PathBSubmitResponse:
    lost_item = _get_lost_item_for_claim(db, lost_item_id, user)
    fraud_service.assert_can_attempt_verification(db, user)

    if user.status != AccountStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active.")

    if _finder_has_verified_claim(db, user.id, lost_item_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an approved claim for this item.",
        )

    if _attempt_counter_paused(db, user.id, lost_item_id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Your last claim is under admin review. Please wait for a decision.",
        )

    used = len(_path_b_attempts(db, user.id, lost_item_id))
    if used >= MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="You have reached the maximum number of attempts for this item.",
        )

    submitted = _answers_map(payload)
    question_ids = {q.id for q in lost_item.hidden_questions}
    if set(submitted.keys()) != question_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Answer every verification question exactly once.",
        )

    label, lat, lng, zone_id = _resolve_location(
        db, payload.location_id, user.university_id
    )
    score, breakdown = compute_path_b_score(
        lost_item,
        submitted,
        payload.image_url,
        lat,
        lng,
    )
    hidden_avg = breakdown["hidden_answer"]
    result = _classify_path_b_score(score, hidden_avg)

    prior_scores = _prior_attempt_scores(db, user.id, lost_item_id)
    attempt_scores = prior_scores + [round(score, 4)]
    if _check_gradual_improvement(attempt_scores):
        breakdown["gradual_improvement_flag"] = True

    sorted_questions = sorted(lost_item.hidden_questions, key=lambda x: x.position)
    finder_answers = [
        {"question_id": str(q.id), "answer": submitted[q.id]}
        for q in sorted_questions
    ]
    bridge_desc = ". ".join(submitted[q.id] for q in sorted_questions)[:1000]

    expiry = datetime.now(timezone.utc) + timedelta(days=_FOUND_BRIDGE_ACTIVE_DAYS)
    bridge_found = Item(
        university_id=user.university_id,
        posted_by_id=user.id,
        item_type=ItemType.FOUND,
        status=ItemStatus.FOUND,
        category=lost_item.category,
        public_description=bridge_desc or "Path B claim",
        location_id=zone_id,
        location_label=label,
        location_lat=lat,
        location_lng=lng,
        date_occurred=datetime.now(timezone.utc),
        image_urls=[payload.image_url] if payload.image_url else [],
        expiry_date=expiry,
        path_b_bridge=True,
    )
    db.add(bridge_found)
    db.flush()

    match = PotentialMatch(
        university_id=user.university_id,
        lost_item_id=lost_item.id,
        found_item_id=bridge_found.id,
        match_score=round(score, 4),
        score_breakdown={**breakdown, "path": "path_b"},
        status=PotentialMatchStatus.ACTIVE,
    )
    db.add(match)
    db.flush()

    attempt = VerificationAttempt(
        university_id=user.university_id,
        user_id=user.id,
        potential_match_id=match.id,
        lost_item_id=lost_item.id,
        found_item_id=bridge_found.id,
        path=VerificationPath.PATH_B,
        ownership_score=round(score, 4),
        score_breakdown=breakdown,
        result=result,
    )
    db.add(attempt)
    db.flush()

    claim = IHaveThisItemClaim(
        university_id=user.university_id,
        user_id=user.id,
        lost_item_id=lost_item.id,
        bridge_found_item_id=bridge_found.id,
        potential_match_id=match.id,
        finder_answers=finder_answers,
        attempt_scores=attempt_scores,
        location_id=zone_id,
        location_label=label,
        location_lat=lat,
        location_lng=lng,
        image_url=payload.image_url,
        ownership_score=round(score, 4),
        score_breakdown=breakdown,
        result=result,
    )
    db.add(claim)
    db.flush()

    if breakdown.get("gradual_improvement_flag"):
        fraud_service.record_gradual_improvement(
            db,
            user_id=user.id,
            university_id=user.university_id,
            reference_id=claim.id,
            attempt_scores=attempt_scores,
        )

    notification_service.notify_claim_received(
        db,
        lost_owner_id=lost_item.posted_by_id,
        lost_item_id=lost_item.id,
        claim_id=claim.id,
    )

    conversation_id: uuid.UUID | None = None
    message: str
    prompt_post_found = False
    attempt_num = used + 1

    if result == VerificationResult.APPROVED:
        other_verified = (
            db.query(PotentialMatch)
            .filter(
                PotentialMatch.lost_item_id == lost_item.id,
                PotentialMatch.id != match.id,
                PotentialMatch.status == PotentialMatchStatus.VERIFIED,
            )
            .first()
        )
        if other_verified:
            lost_item.status = ItemStatus.UNDER_DISPUTE
            match.status = PotentialMatchStatus.PAUSED
            ms.pause_matches_for_item(db, lost_item.id)
            message = (
                "Your claim scored highly, but another claimant was already approved. "
                "An admin will review — chat is not unlocked yet."
            )
            from app.services import admin_notification_service

            admin_notification_service.notify_admins_verification_dispute(
                db, match_id=match.id, lost_item_id=lost_item.id
            )
            notification_service.notify_verification_review(
                db,
                user_id=user.id,
                match_id=match.id,
                lost_item_id=lost_item.id,
            )
        else:
            match.status = PotentialMatchStatus.VERIFIED
            if lost_item.status == ItemStatus.OPEN:
                lost_item.status = ItemStatus.POTENTIAL_MATCH

            conv = Conversation(
                university_id=user.university_id,
                potential_match_id=match.id,
                lost_item_id=lost_item.id,
                found_item_id=bridge_found.id,
                lost_owner_id=lost_item.posted_by_id,
                found_owner_id=user.id,
                status=ConversationStatus.UNLOCKED,
                unlocked_at=datetime.now(timezone.utc),
            )
            db.add(conv)
            db.flush()
            conversation_id = conv.id

            notification_service.notify_verification_passed(
                db,
                lost_owner_id=lost_item.posted_by_id,
                found_owner_id=user.id,
                match_id=match.id,
                conversation_id=conv.id,
                lost_item_id=lost_item.id,
                found_item_id=bridge_found.id,
            )
            message = "Your claim was approved! Chat is now unlocked with the lost item owner."
            prompt_post_found = True

    elif result == VerificationResult.REVIEW:
        match.status = PotentialMatchStatus.PENDING_REVIEW
        if lost_item.status == ItemStatus.OPEN:
            lost_item.status = ItemStatus.UNDER_VERIFICATION
        from app.services import admin_notification_service

        admin_notification_service.notify_admins_claim_in_review(
            db, match_id=match.id, path="path_b"
        )
        notification_service.notify_verification_review(
            db,
            user_id=user.id,
            match_id=match.id,
            lost_item_id=lost_item.id,
        )
        notification_service.notify_claim_under_review(
            db,
            lost_owner_id=lost_item.posted_by_id,
            lost_item_id=lost_item.id,
            claim_id=claim.id,
        )
        if attempt_num == MAX_ATTEMPTS:
            message = (
                "Your claim is under admin review. Your attempt counter is paused "
                "until an admin decides — you will not be locked out while waiting."
            )
        else:
            message = (
                "Your claim is under admin review (score in the 50–75% range). "
                "We'll notify you when a decision is made."
            )

    else:
        failed_before = _failed_attempts_count(db, user.id, lost_item.id)
        fail_num = failed_before + 1
        if fail_num == 2:
            trust_service.penalise_failed_verification(
                db, user.id, attempt_number=2, item_id=lost_item.id
            )
        elif fail_num >= 3:
            trust_service.penalise_failed_verification(
                db, user.id, attempt_number=3, item_id=lost_item.id
            )

        fraud_service.on_verification_rejected(db, attempt=attempt)

        if score < FALSE_CLAIM_THRESHOLD:
            trust_service.penalise_false_claim(db, user.id, lost_item.id)

        remaining = max(0, MAX_ATTEMPTS - attempt_num)
        notification_service.notify_path_b_failed(
            db,
            user_id=user.id,
            lost_item_id=lost_item.id,
            attempts_remaining=remaining,
        )
        message = (
            f"Claim not approved (score {int(score * 100)}%). "
            f"You have {remaining} attempt(s) remaining for this item."
        )

    db.commit()

    remaining_after = max(0, MAX_ATTEMPTS - attempt_num)
    paused_after = (
        attempt_num == MAX_ATTEMPTS and result == VerificationResult.REVIEW
    )

    return PathBSubmitResponse(
        result=result,
        ownership_score=round(score, 4),
        score_breakdown=breakdown,
        attempts_remaining=remaining_after,
        attempt_counter_paused=paused_after,
        conversation_id=conversation_id,
        match_id=match.id,
        claim_id=claim.id,
        message=message,
        prompt_post_found_item=prompt_post_found,
    )

"""
AI Matching API routes (Feature G).
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import get_settings
from app.models.user import User
from app.models.item import Item
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.conversation import Conversation, ConversationStatus
from app.models.verification_attempt import VerificationAttempt
from app.schemas.match import (
    PotentialMatchResponse,
    PotentialMatchListResponse,
    MatchItemSummary,
    ScorePreviewRequest,
    ScorePreviewResponse,
)
from app.services import matching_service

router = APIRouter(prefix="/matches", tags=["matches"])


def _item_summary(item: Item) -> MatchItemSummary:
    return MatchItemSummary(
        id=item.id,
        category=item.category,
        status=item.status,
        public_description=item.public_description,
        location_label=item.location_label,
        image_urls=item.image_urls or [],
        date_occurred=item.date_occurred,
        posted_by_username=item.posted_by.username,
        posted_by_display_name=item.posted_by.full_name or item.posted_by.username,
    )


def _build_match_response(
    match: PotentialMatch,
    user_id: uuid.UUID,
    db: Session,
    *,
    has_verification_attempt: bool = False,
) -> PotentialMatchResponse:
    lost = match.lost_item
    found = match.found_item
    role = "lost_owner" if lost.posted_by_id == user_id else "found_owner"
    conv = (
        db.query(Conversation)
        .filter(
            Conversation.potential_match_id == match.id,
            Conversation.status == ConversationStatus.UNLOCKED,
        )
        .first()
    )
    return PotentialMatchResponse(
        id=match.id,
        match_score=match.match_score,
        score_breakdown=match.score_breakdown or {},
        status=match.status,
        created_at=match.created_at,
        lost_item=_item_summary(lost),
        found_item=_item_summary(found),
        user_role=role,
        conversation_id=conv.id if conv else None,
        has_verification_attempt=has_verification_attempt,
    )


@router.get("/me", response_model=PotentialMatchListResponse)
def get_my_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return all active potential matches involving the current user."""
    rows = matching_service.list_matches_for_user(db, current_user.id)
    match_ids = [m.id for m in rows]
    attempted_ids: set[uuid.UUID] = set()
    if match_ids:
        attempted_ids = {
            row[0]
            for row in db.query(VerificationAttempt.potential_match_id)
            .filter(VerificationAttempt.potential_match_id.in_(match_ids))
            .distinct()
            .all()
        }
    matches = [
        _build_match_response(
            m,
            current_user.id,
            db,
            has_verification_attempt=m.id in attempted_ids,
        )
        for m in rows
    ]
    return PotentialMatchListResponse(matches=matches, total=len(matches))


@router.post("/preview", response_model=ScorePreviewResponse)
def preview_match_score(
    payload: ScorePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Score two items without creating a PotentialMatch — DEBUG only.
    Useful for verifying the matching formula during development.
    """
    settings = get_settings()
    if not settings.DEBUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    lost = db.query(Item).filter(Item.id == payload.lost_item_id).first()
    found = db.query(Item).filter(Item.id == payload.found_item_id).first()
    if not lost or not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if lost.university_id != current_user.university_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    score, breakdown = matching_service.compute_match_score(lost, found)
    return ScorePreviewResponse(
        match_score=round(score, 4),
        score_breakdown=breakdown,
        would_match=score >= matching_service.MATCH_THRESHOLD,
    )

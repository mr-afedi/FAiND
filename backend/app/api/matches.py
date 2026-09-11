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
from app.models.potential_match import PotentialMatch
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
    poster = item.posted_by
    return MatchItemSummary(
        id=item.id,
        category=item.category,
        status=item.status,
        public_description=item.public_description,
        location_label=item.location_label,
        image_urls=item.image_urls or [],
        date_occurred=item.date_occurred,
        posted_by_username=poster.username if poster else "anonymous",
        posted_by_display_name=(poster.full_name or poster.username) if poster else "Anonymous",
    )


def _build_match_response(
    match: PotentialMatch,
    user_id: uuid.UUID,
) -> PotentialMatchResponse:
    lost = match.lost_item
    found = match.found_item
    # Role is based on the viewer's own item. Anonymous found posts have no
    # posted_by_id and must not be classified as "found_owner".
    if lost.posted_by_id is not None and lost.posted_by_id == user_id:
        role = "lost_owner"
    elif found.posted_by_id is not None and found.posted_by_id == user_id:
        role = "found_owner"
    else:
        role = "lost_owner"
    return PotentialMatchResponse(
        id=match.id,
        match_score=match.match_score,
        score_breakdown=match.score_breakdown or {},
        status=match.status,
        created_at=match.created_at,
        lost_item=_item_summary(lost),
        found_item=_item_summary(found),
        user_role=role,
    )


@router.get("/me", response_model=PotentialMatchListResponse)
def get_my_matches(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = matching_service.list_matches_for_user(db, current_user.id)
    matches = [_build_match_response(m, current_user.id) for m in rows]
    return PotentialMatchListResponse(matches=matches, total=len(matches))


@router.post("/preview", response_model=ScorePreviewResponse)
def preview_match_score(
    payload: ScorePreviewRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.DEBUG:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    lost = db.query(Item).filter(Item.id == payload.lost_item_id).first()
    found = db.query(Item).filter(Item.id == payload.found_item_id).first()
    if not lost or not found:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    if lost.university_id != current_user.university_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    score, breakdown = matching_service.compute_match_score(lost, found, db=db)
    return ScorePreviewResponse(
        match_score=round(score, 4),
        score_breakdown=breakdown,
        would_match=score >= matching_service.MATCH_THRESHOLD,
    )

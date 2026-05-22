"""Pydantic schemas for AI Matching API (Feature G)."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.potential_match import PotentialMatchStatus
from app.models.item import ItemCategory, ItemStatus


class MatchItemSummary(BaseModel):
    id: uuid.UUID
    category: ItemCategory
    status: ItemStatus
    public_description: str
    location_label: str
    image_urls: list[str]
    date_occurred: datetime
    posted_by_username: str
    posted_by_display_name: str

    model_config = {"from_attributes": True}


class PotentialMatchResponse(BaseModel):
    id: uuid.UUID
    match_score: float
    score_breakdown: dict
    status: PotentialMatchStatus
    created_at: datetime
    lost_item: MatchItemSummary
    found_item: MatchItemSummary
    # Which side the current user is on
    user_role: str  # "lost_owner" | "found_owner"

    model_config = {"from_attributes": True}


class PotentialMatchListResponse(BaseModel):
    matches: list[PotentialMatchResponse]
    total: int


class ScorePreviewRequest(BaseModel):
    """Debug: score two items without creating a match record."""
    lost_item_id: uuid.UUID
    found_item_id: uuid.UUID


class ScorePreviewResponse(BaseModel):
    match_score: float
    score_breakdown: dict
    would_match: bool

"""Pydantic schemas — Path B I Have This Item (V4.3)."""
import uuid
from typing import Optional

from pydantic import BaseModel, Field

from app.models.verification_attempt import VerificationResult
from app.schemas.verification import AnswerSubmission, VerificationQuestionForm


class PathBFormResponse(BaseModel):
    lost_item_id: uuid.UUID
    lost_item_public_description: str
    lost_item_location: str
    questions: list[VerificationQuestionForm]
    attempts_used: int
    attempts_remaining: int
    max_attempts: int = 3
    attempt_counter_paused: bool = False


class PathBSubmitRequest(BaseModel):
    answers: list[AnswerSubmission] = Field(..., min_length=2, max_length=3)
    location_id: Optional[uuid.UUID] = None
    image_url: Optional[str] = Field(None, max_length=500)


class PathBSubmitResponse(BaseModel):
    result: VerificationResult
    ownership_score: float
    score_breakdown: dict
    attempts_remaining: int
    attempt_counter_paused: bool = False
    conversation_id: Optional[uuid.UUID] = None
    match_id: uuid.UUID
    claim_id: uuid.UUID
    message: str
    prompt_post_found_item: bool = False

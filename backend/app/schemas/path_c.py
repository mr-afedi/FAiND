"""Pydantic schemas — Path C This Might Be Mine (V4.4)."""
import uuid
from typing import Optional

from pydantic import BaseModel, Field

from app.models.verification_attempt import VerificationResult
from app.schemas.verification import AnswerSubmission, VerificationQuestionForm


class PathCFormResponse(BaseModel):
    found_item_id: uuid.UUID
    found_item_public_description: str
    found_item_location: str
    questions: list[VerificationQuestionForm]
    attempts_used: int
    attempts_remaining: int
    max_attempts: int = 3
    attempt_counter_paused: bool = False


class PathCSubmitRequest(BaseModel):
    answers: list[AnswerSubmission] = Field(..., min_length=2, max_length=3)


class PathCSubmitResponse(BaseModel):
    result: VerificationResult
    ownership_score: float
    score_breakdown: dict
    attempts_remaining: int
    attempt_counter_paused: bool = False
    conversation_id: Optional[uuid.UUID] = None
    match_id: uuid.UUID
    claim_id: uuid.UUID
    message: str
    prompt_post_lost_item: bool = False

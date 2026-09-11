"""Pydantic schemas for Ownership Verification — Path A (Feature I)."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.verification_attempt import VerificationResult


class VerificationQuestionForm(BaseModel):
    id: uuid.UUID
    position: int
    question: str


class PathAFormResponse(BaseModel):
    match_id: uuid.UUID
    lost_item_id: uuid.UUID
    found_item_id: uuid.UUID
    found_item_description: str
    found_item_location: str
    questions: list[VerificationQuestionForm]
    attempts_used_24h: int
    attempts_remaining_24h: int
    max_attempts_24h: int = 3


class AnswerSubmission(BaseModel):
    question_id: uuid.UUID
    answer: str = Field(..., min_length=1, max_length=500)


class PathASubmitRequest(BaseModel):
    answers: list[AnswerSubmission] = Field(..., min_length=2, max_length=3)


class PathASubmitResponse(BaseModel):
    result: VerificationResult
    ownership_score: float
    score_breakdown: dict
    attempts_remaining_24h: int
    conversation_id: Optional[uuid.UUID] = None
    message: str


class VerificationStatusResponse(BaseModel):
    match_id: uuid.UUID
    match_status: str
    latest_result: Optional[VerificationResult] = None
    latest_score: Optional[float] = None
    conversation_id: Optional[uuid.UUID] = None
    attempts_used_24h: int
    attempts_remaining_24h: int
    can_verify: bool

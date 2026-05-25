"""
Verification API — Path A ownership verification (Feature I).
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.verification import (
    PathAFormResponse,
    PathASubmitRequest,
    PathASubmitResponse,
    VerificationStatusResponse,
)
from app.services import verification_service

router = APIRouter(prefix="/verification", tags=["verification"])


@router.get("/path-a/{match_id}/form", response_model=PathAFormResponse)
def get_path_a_form(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return read-only hidden questions for the lost item owner (Section 27.8)."""
    return verification_service.get_path_a_form(db, match_id, current_user)


@router.get("/path-a/{match_id}/status", response_model=VerificationStatusResponse)
def get_path_a_status(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return verification_service.get_verification_status(db, match_id, current_user)


@router.post("/path-a/{match_id}", response_model=PathASubmitResponse)
def submit_path_a(
    match_id: uuid.UUID,
    payload: PathASubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Submit hidden question answers and receive verification result (Section 12.5)."""
    return verification_service.submit_path_a(db, match_id, current_user, payload)

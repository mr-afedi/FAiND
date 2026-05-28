"""
Verification API — Path A (Feature I) and Path B (Feature J).
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
from app.schemas.path_b import PathBFormResponse, PathBSubmitRequest, PathBSubmitResponse
from app.schemas.path_c import PathCFormResponse, PathCSubmitRequest, PathCSubmitResponse
from app.services import verification_service
from app.services import path_b_service
from app.services import path_c_service

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


@router.get("/path-b/lost-items/{lost_item_id}/form", response_model=PathBFormResponse)
def get_path_b_form(
    lost_item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Path B — pre-submit info and attempt counts (Section 27.9)."""
    return path_b_service.get_path_b_form(db, lost_item_id, current_user)


@router.post("/path-b/lost-items/{lost_item_id}", response_model=PathBSubmitResponse)
def submit_path_b(
    lost_item_id: uuid.UUID,
    payload: PathBSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Path B — I Have This Item claim + automatic verification (Section 8)."""
    return path_b_service.submit_path_b(db, lost_item_id, current_user, payload)


@router.get("/path-c/found-items/{found_item_id}/form", response_model=PathCFormResponse)
def get_path_c_form(
    found_item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Path C — finder's hidden questions for the claimant (Section 8, V4.3)."""
    return path_c_service.get_path_c_form(db, found_item_id, current_user)


@router.post("/path-c/found-items/{found_item_id}", response_model=PathCSubmitResponse)
def submit_path_c(
    found_item_id: uuid.UUID,
    payload: PathCSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Path C — This Might Be Mine claim + automatic verification (V4.3)."""
    return path_c_service.submit_path_c(db, found_item_id, current_user, payload)

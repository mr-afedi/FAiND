"""
User profile and settings route handlers.
Business logic in user_service — handlers only do HTTP concerns.
IDOR enforced: users can only modify their own data.
"""
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.user import (
    OwnProfileResponse,
    PublicProfileResponse,
    UpdateProfileRequest,
    ChangePasswordRequest,
    UpdateSettingsRequest,
    DeleteAccountRequest,
)
from app.schemas.auth import MessageResponse
from app.schemas.trust import TrustHistoryResponse, TrustEventResponse
from app.services import user_service
import app.services.trust_service as trust_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=OwnProfileResponse)
def get_own_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.get_own_profile(db, current_user)


@router.patch("/me", response_model=OwnProfileResponse)
def update_profile(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.update_profile(db, current_user, data)


@router.patch("/me/password", response_model=MessageResponse)
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.change_password(db, current_user, data)
    return {"message": "Password changed successfully. Please log in again."}


@router.patch("/me/settings", response_model=OwnProfileResponse)
def update_settings(
    data: UpdateSettingsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.update_settings(db, current_user, data)


@router.delete("/me", response_model=MessageResponse)
def delete_account(
    data: DeleteAccountRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_service.delete_account(db, current_user, data.password)
    response.delete_cookie("faind_refresh_token", path="/api/v1/auth")
    return {"message": "Your account has been deleted."}


@router.get("/me/trust-events", response_model=TrustHistoryResponse)
def get_own_trust_history(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns the authenticated user's trust score, tier label, and
    paginated event history (Section 17.2 — own dashboard: raw number).
    """
    events = trust_service.get_user_trust_events(db, current_user.id, skip=skip, limit=limit)
    return TrustHistoryResponse(
        trust_score=current_user.trust_score,
        tier=trust_service.get_trust_tier(current_user.trust_score),
        events=[TrustEventResponse.model_validate(e) for e in events],
        total=len(events),
    )


@router.get("/{username}", response_model=PublicProfileResponse)
def get_public_profile(
    username: str,
    db: Session = Depends(get_db),
):
    """
    Public profile — only returns Section 23.1-allowed fields.
    No auth required. Returns 404 for suspended/deleted users.
    """
    return user_service.get_public_profile(db, username)

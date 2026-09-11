"""
User profile and settings route handlers.
"""
from fastapi import APIRouter, Depends, Response
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
from app.schemas.token import UserTokensResponse, TokenLedgerEntryResponse
from app.schemas.redemption import RedeemTokensRequest, RedeemTokensResponse
from app.services import user_service, token_service, redemption_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=OwnProfileResponse)
def get_own_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return user_service.get_own_profile(db, current_user)


@router.get("/me/tokens", response_model=UserTokensResponse)
def get_my_tokens(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    balance = token_service.get_user_token_balance(db, current_user.id)
    entries = token_service.list_user_ledger_entries(db, current_user.id)
    return UserTokensResponse(
        balance=balance,
        recent=[
            TokenLedgerEntryResponse(
                id=e.id,
                delta=e.delta,
                reason=e.reason.value,
                reference_item_id=e.reference_item_id,
                created_at=e.created_at,
            )
            for e in entries
        ],
    )


@router.post("/me/tokens/redeem", response_model=RedeemTokensResponse)
def redeem_tokens(
    payload: RedeemTokensRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = redemption_service.create_redemption_code(db, current_user, payload)
    db.commit()
    return result


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


@router.get("/{username}", response_model=PublicProfileResponse)
def get_public_profile(
    username: str,
    db: Session = Depends(get_db),
):
    return user_service.get_public_profile(db, username)

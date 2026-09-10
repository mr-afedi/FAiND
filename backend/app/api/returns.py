"""
Return confirmation API (Feature M, Section 15).
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.return_confirmation import (
    ReturnActionResponse,
    ReturnStatusResponse,
    ReturnedDetailResponse,
    ReturnedListResponse,
    QrGenerateResponse,
    QrRedeemRequest,
    DisputeReturnRequest,
)
from app.services import returned_items_service
from app.services import return_service

router = APIRouter(prefix="/returns", tags=["returns"])


@router.get("/me", response_model=ReturnedListResponse)
def list_my_returns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return return_service.list_my_returns(db, current_user)


@router.get("/match/{match_id}/status", response_model=ReturnStatusResponse)
def get_return_status(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return return_service.get_return_status(db, match_id, current_user)


@router.get("/by-item/{item_id}/status", response_model=ReturnStatusResponse)
def get_return_status_by_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return return_service.get_return_status_by_item(db, item_id, current_user)


@router.post("/match/{match_id}/finder-confirm", response_model=ReturnActionResponse)
def finder_confirm(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return return_service.finder_confirm_handed_over(db, match_id, current_user)


@router.post("/match/{match_id}/owner-confirm", response_model=ReturnActionResponse)
def owner_confirm(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return return_service.owner_confirm_received(db, match_id, current_user)


@router.post("/match/{match_id}/qr/generate", response_model=QrGenerateResponse)
def generate_qr(
    match_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return return_service.generate_qr_token(db, match_id, current_user)


@router.post("/qr/redeem", response_model=ReturnActionResponse)
def redeem_qr(
    payload: QrRedeemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return return_service.redeem_qr_token(db, current_user, payload.token)


@router.post("/{return_id}/dispute", response_model=ReturnedDetailResponse)
def dispute_return(
    return_id: uuid.UUID,
    payload: DisputeReturnRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    returned_items_service.file_dispute(db, return_id, current_user, payload.reason)
    return return_service.get_return_detail(db, return_id, current_user)


@router.get("/{return_id}", response_model=ReturnedDetailResponse)
def get_return_detail(
    return_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return return_service.get_return_detail(db, return_id, current_user)

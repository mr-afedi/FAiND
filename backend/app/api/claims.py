"""
Claims API — Path A and Path C (Section 8), structured messaging (Section 13).
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.claim import (
    ClaimFormSubmit,
    ClaimSubmitResponse,
    MyClaimsListResponse,
    AwaitingConfirmationListResponse,
)
from app.schemas.messaging import OwnerClaimStatusResponse, SendInquiryRequest, SendInquiryResponse
from app.services import claim_service, messaging_service

router = APIRouter(prefix="/claims", tags=["claims"])


@router.post("/path-a/{found_item_id}", response_model=ClaimSubmitResponse)
def submit_claim_path_a(
    found_item_id: UUID,
    payload: ClaimFormSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Path A — requires AI PotentialMatch linking claimant's lost item (Section 8.1)."""
    result = claim_service.submit_path_a(db, current_user, found_item_id, payload)
    db.commit()
    return result


@router.post("/path-c/{found_item_id}", response_model=ClaimSubmitResponse)
def submit_claim_path_c(
    found_item_id: UUID,
    payload: ClaimFormSubmit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Path C — no match required; includes lost_location (Section 8.3)."""
    result = claim_service.submit_path_c(db, current_user, found_item_id, payload)
    db.commit()
    return result


@router.get("/me", response_model=MyClaimsListResponse)
def list_my_claims(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """V5 — dashboard My Claims section."""
    return claim_service.list_my_claims(db, current_user)


@router.get("/me/awaiting-confirmation", response_model=AwaitingConfirmationListResponse)
def list_awaiting_confirmation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """V5 — dashboard Awaiting Your Confirmation section."""
    return claim_service.list_awaiting_confirmation(db, current_user)


@router.get("/{claim_id}/status", response_model=OwnerClaimStatusResponse)
def get_claim_status(
    claim_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Section 13.1 — owner claim status and inquiry state."""
    return messaging_service.get_owner_claim_status(db, current_user, claim_id)


@router.post("/{claim_id}/inquiry", response_model=SendInquiryResponse)
def send_claim_inquiry(
    claim_id: UUID,
    payload: SendInquiryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Section 13.2 — one predefined inquiry per active claim."""
    result = messaging_service.send_owner_inquiry(db, current_user, claim_id, payload)
    db.commit()
    return result

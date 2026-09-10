"""
Owner handover sign-off API — Section 11.
"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.handover import HandoverConfirmResponse, HandoverOwnerResponse
from app.services import handover_service

router = APIRouter(prefix="/handover", tags=["handover"])


@router.get("/{handover_id}", response_model=HandoverOwnerResponse)
def get_handover(
    handover_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner views handover details before digital sign-off."""
    return handover_service.get_handover_for_owner(db, current_user, handover_id)


@router.post("/{handover_id}/confirm", response_model=HandoverConfirmResponse)
def confirm_handover(
    handover_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Owner digital sign-off — marks item RETURNED (Section 11)."""
    result = handover_service.confirm_handover(db, current_user, handover_id)
    db.commit()
    return result

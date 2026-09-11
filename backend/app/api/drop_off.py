"""
Drop-off confirmation API (Section 7.5, Section 9).
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.drop_off import DropOffQrRedeemRequest
from app.schemas.item import FoundItemTrackResponse
from app.schemas.token import TokenEscrowInfo
from app.services import drop_off_service, item_service
from app.services.token_service import EscrowAwardResult

router = APIRouter(prefix="/drop-off", tags=["drop-off"])


class DropOffActionResponse(BaseModel):
    message: str
    item: FoundItemTrackResponse
    token_escrow: TokenEscrowInfo


def _build_drop_off_response(
    db: Session,
    *,
    message: str,
    item_id: uuid.UUID,
    award: Optional[EscrowAwardResult],
) -> DropOffActionResponse:
    escrow_plain = award.escrow_token if award else None
    try:
        item = item_service.get_found_item_track_by_id(
            db, item_id, escrow_token_plain=escrow_plain
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return DropOffActionResponse(
        message=message,
        item=item,
        token_escrow=item.token_escrow,
    )


def _build_drop_off_response_by_ref(
    db: Session,
    *,
    message: str,
    tracking_reference: str,
    award: Optional[EscrowAwardResult],
) -> DropOffActionResponse:
    escrow_plain = award.escrow_token if award else None
    try:
        item = item_service.get_found_item_by_tracking_reference(
            db, tracking_reference, escrow_token_plain=escrow_plain
        )
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return DropOffActionResponse(
        message=message,
        item=item,
        token_escrow=item.token_escrow,
    )


@router.post(
    "/track/{tracking_reference}/finder-confirm",
    response_model=DropOffActionResponse,
)
def finder_confirm_by_tracking_reference(
    tracking_reference: str,
    db: Session = Depends(get_db),
):
    message, item, award = drop_off_service.finder_confirm_by_tracking_ref(
        db, tracking_reference
    )
    db.commit()
    return _build_drop_off_response_by_ref(
        db,
        message=message,
        tracking_reference=tracking_reference,
        award=award,
    )


@router.post(
    "/found/{item_id}/finder-confirm",
    response_model=DropOffActionResponse,
)
def finder_confirm_by_item_id(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message, _, award = drop_off_service.finder_confirm_by_item_id(
        db, item_id, current_user
    )
    db.commit()
    return _build_drop_off_response(
        db, message=message, item_id=item_id, award=award
    )


@router.post(
    "/found/{item_id}/authority-received",
    response_model=DropOffActionResponse,
)
def authority_received_stub(
    item_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Stub — real authority auth in W6."""
    message, _, award = drop_off_service.authority_confirm_received_stub(db, item_id)
    db.commit()
    return _build_drop_off_response(
        db, message=message, item_id=item_id, award=award
    )


@router.post("/qr/redeem", response_model=DropOffActionResponse)
def redeem_drop_off_qr(
    payload: DropOffQrRedeemRequest,
    db: Session = Depends(get_db),
):
    message, item, award = drop_off_service.redeem_drop_off_qr(db, payload.token)
    db.commit()
    return _build_drop_off_response(
        db, message=message, item_id=item.id, award=award
    )

"""Tipping API — Paystack appreciation (Section 20)."""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.tipping import (
    InitializeTipRequest,
    InitializeTipResponse,
    VerifyTipResponse,
    TipHistoryResponse,
    TipHistoryItem,
)
from app.services import tipping_service

router = APIRouter(prefix="/tips", tags=["tipping"])


@router.post("/returns/{return_id}/initialize", response_model=InitializeTipResponse)
def initialize_tip(
    return_id: uuid.UUID,
    payload: InitializeTipRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = tipping_service.initialize_tip_payment(
        db,
        return_id=return_id,
        sender=current_user,
        amount_ghs=payload.amount_ghs,
    )
    return InitializeTipResponse(**result)


@router.get("/verify/{reference}", response_model=VerifyTipResponse)
def verify_tip(
    reference: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    result = tipping_service.verify_tip_by_reference(db, reference, current_user)
    return VerifyTipResponse(**result)


@router.get("/me/sent", response_model=TipHistoryResponse)
def my_sent_tips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = tipping_service.list_sent_tips(db, current_user)
    return TipHistoryResponse(tips=[TipHistoryItem.model_validate(r) for r in rows])


@router.get("/me/received", response_model=TipHistoryResponse)
def my_received_tips(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = tipping_service.list_received_tips(db, current_user)
    return TipHistoryResponse(tips=[TipHistoryItem.model_validate(r) for r in rows])


@router.post("/webhook/paystack")
async def paystack_webhook(request: Request, db: Session = Depends(get_db)):
    """Paystack webhook — signature verified, no JWT."""
    body = await request.body()
    signature = request.headers.get("x-paystack-signature")
    return tipping_service.handle_paystack_webhook(db, body, signature)

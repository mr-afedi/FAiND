"""
Admin fraud monitoring API (Section 18 — Feature O).

Internal only. Full admin UI is Feature R; these endpoints power monitoring now.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.user import User
from app.schemas.fraud import (
    AdminConfirmFraudResponse,
    FraudAlertsResponse,
    FraudAlertUser,
    FraudEventOut,
    FraudUserEventsResponse,
    FraudUserSummary,
)
from app.services import fraud_service

router = APIRouter(prefix="/admin/fraud", tags=["admin-fraud"])


@router.get("/alerts", response_model=FraudAlertsResponse)
def get_fraud_alerts(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = fraud_service.list_fraud_alerts(db)
    return FraudAlertsResponse(
        alerts=[FraudAlertUser.model_validate(r) for r in rows]
    )


@router.get("/users/{user_id}", response_model=FraudUserEventsResponse)
def get_user_fraud_history(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    summary = fraud_service.get_user_fraud_summary(db, user_id)
    events = fraud_service.list_user_fraud_events(db, user_id)
    return FraudUserEventsResponse(
        user=FraudUserSummary.model_validate(summary),
        events=[FraudEventOut.model_validate(e) for e in events],
    )


@router.post("/users/{user_id}/confirm", response_model=AdminConfirmFraudResponse)
def confirm_user_fraud(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    event = fraud_service.admin_confirm_fraud(
        db, target_user_id=user_id, admin=admin
    )
    db.commit()
    db.refresh(admin)
    target = fraud_service.get_user_fraud_summary(db, user_id)
    return AdminConfirmFraudResponse(
        fraud_risk_score=target["fraud_risk_score"],
        risk_tier=target["risk_tier"],
        event=FraudEventOut.model_validate(event),
    )

"""Admin fraud monitoring schemas (Section 18 — internal only)."""
import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel


class FraudAlertUser(BaseModel):
    user_id: uuid.UUID
    email: str
    username: str
    full_name: str
    trust_score: int
    fraud_risk_score: int
    risk_tier: str
    verification_blocked: bool
    fraud_verification_override: bool = False
    last_signal: Optional[str] = None
    last_event_at: Optional[datetime] = None


class FraudAlertsResponse(BaseModel):
    alerts: list[FraudAlertUser]


class FraudEventOut(BaseModel):
    id: uuid.UUID
    signal_type: str
    delta: int
    score_after: int
    reference_id: Optional[uuid.UUID] = None
    detail: dict[str, Any]
    note: Optional[str] = None
    applied_by_id: Optional[uuid.UUID] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class FraudUserSummary(BaseModel):
    user_id: uuid.UUID
    email: str
    fraud_risk_score: int
    risk_tier: str
    verification_blocked: bool
    fraud_verification_override: bool = False
    event_count: int


class FraudUserEventsResponse(BaseModel):
    user: FraudUserSummary
    events: list[FraudEventOut]


class AdminConfirmFraudResponse(BaseModel):
    fraud_risk_score: int
    risk_tier: str
    event: FraudEventOut

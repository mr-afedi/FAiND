"""
Authority authentication API — Section 16.
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.deps import get_current_authority
from app.core.security import verify_access_token
from app.models.authority import Authority
from app.schemas.authority import (
    AuthorityAlertResponse,
    AuthorityAlertsActionResponse,
    AuthorityAlertsListResponse,
    AuthorityClaimActionResponse,
    AuthorityClaimsComparisonResponse,
    AuthorityClaimsListResponse,
    AuthorityDashboardListResponse,
    AuthorityDropOffActionResponse,
    AuthorityDropPointSettingsResponse,
    AuthorityDropPointSettingsUpdate,
    AuthorityLoginRequest,
    AuthorityOtpStepResponse,
    AuthorityProfileResponse,
    AuthorityScanQrRequest,
    AuthorityScopedItemResponse,
    AuthorityTokenResponse,
    AuthorityVerifyOtpRequest,
)
from app.schemas.messaging import ReplyToInquiryRequest
from app.schemas.handover import (
    HandoverAuthorityDetail,
    HandoverOverrideRequest,
    HandoverQueueResponse,
    HandoverStartRequest,
    HandoverStartResponse,
)
from app.schemas.staff_push import (
    StaffPushSettingsResponse,
    StaffPushSettingsUpdate,
    StaffPushSubscribeRequest,
    StaffPushUnsubscribeRequest,
)
from app.services import authority_alert_service, authority_claim_service, authority_dashboard_service, authority_service, handover_service

router = APIRouter(prefix="/authority", tags=["authority"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=AuthorityOtpStepResponse)
@limiter.limit("5/minute")
async def authority_login(
    request: Request,
    payload: AuthorityLoginRequest,
    db: Session = Depends(get_db),
):
    session_token = await authority_service.start_authority_login(
        db, payload.email, payload.password
    )
    db.commit()
    return AuthorityOtpStepResponse(session_token=session_token)


@router.post("/verify-otp", response_model=AuthorityTokenResponse)
@limiter.limit("10/minute")
async def authority_verify_otp(
    request: Request,
    payload: AuthorityVerifyOtpRequest,
    db: Session = Depends(get_db),
):
    token_payload = verify_access_token(payload.session_token)
    if not token_payload or not token_payload.get("otp_pending"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        )
    if token_payload.get("role") != "authority":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token.",
        )

    access_token = authority_service.verify_authority_otp(
        db, token_payload, payload.code
    )
    db.commit()
    return AuthorityTokenResponse(access_token=access_token)


@router.get("/me", response_model=AuthorityProfileResponse)
def authority_me(authority: Authority = Depends(get_current_authority)):
    return authority_service.build_authority_profile(authority)


@router.get("/items/{item_id}", response_model=AuthorityScopedItemResponse)
def authority_get_item(
    item_id: UUID,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """Scoped item peek — drop_point_id enforced (Section 16.2)."""
    return authority_service.get_scoped_found_item(db, authority, item_id)


@router.get("/incoming", response_model=AuthorityDashboardListResponse)
def authority_incoming(
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """Items routed to this drop point, not yet AT_DROPPOINT (Section 17.1)."""
    return authority_dashboard_service.list_incoming_items(db, authority)


@router.get("/at-droppoint", response_model=AuthorityDashboardListResponse)
def authority_at_droppoint(
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """Items confirmed received, awaiting claim (Section 17.1)."""
    return authority_dashboard_service.list_at_droppoint_items(db, authority)


@router.post("/confirm-dropoff/{item_id}", response_model=AuthorityDropOffActionResponse)
def authority_confirm_dropoff(
    item_id: UUID,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """Authority half of dual drop-off confirmation (Section 9.1)."""
    result = authority_dashboard_service.confirm_dropoff(db, authority, item_id)
    db.commit()
    return result


@router.post("/scan-qr", response_model=AuthorityDropOffActionResponse)
def authority_scan_qr(
    payload: AuthorityScanQrRequest,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """QR scan confirmation — instant AT_DROPPOINT (Section 9.2)."""
    result = authority_dashboard_service.scan_qr(db, authority, payload.token)
    db.commit()
    return result


@router.get("/drop-point/settings", response_model=AuthorityDropPointSettingsResponse)
def authority_get_drop_point_settings(
    authority: Authority = Depends(get_current_authority),
):
    return authority_dashboard_service.get_drop_point_settings(authority)


@router.patch("/drop-point/settings", response_model=AuthorityDropPointSettingsResponse)
def authority_update_drop_point_settings(
    payload: AuthorityDropPointSettingsUpdate,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    result = authority_dashboard_service.update_drop_point_settings(db, authority, payload)
    db.commit()
    return result


@router.get("/claims", response_model=AuthorityClaimsListResponse)
def authority_list_claim_items(
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """Found items at this drop point with one or more claims (Section 8.5)."""
    return authority_claim_service.list_claim_items(db, authority)


@router.get("/claims/{found_item_id}", response_model=AuthorityClaimsComparisonResponse)
def authority_get_claims(
    found_item_id: UUID,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """All claims on a found item — side-by-side comparison (Section 8.5)."""
    return authority_claim_service.get_claims_for_item(db, authority, found_item_id)


@router.post("/claims/{claim_id}/call-to-collect", response_model=AuthorityClaimActionResponse)
def authority_call_to_collect(
    claim_id: UUID,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    result = authority_claim_service.call_to_collect(db, authority, claim_id)
    db.commit()
    return result


@router.post("/claims/{claim_id}/verify", response_model=AuthorityClaimActionResponse)
def authority_verify_claim(
    claim_id: UUID,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    result = authority_claim_service.verify_claim(db, authority, claim_id)
    db.commit()
    return result


@router.post("/claims/{claim_id}/reject", response_model=AuthorityClaimActionResponse)
def authority_reject_claim(
    claim_id: UUID,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    result = authority_claim_service.reject_claim(db, authority, claim_id)
    db.commit()
    return result


@router.post("/inquiries/{inquiry_id}/reply", response_model=AuthorityClaimActionResponse)
def authority_reply_to_inquiry(
    inquiry_id: UUID,
    payload: ReplyToInquiryRequest,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """Section 13.3 — authority quick reply to owner inquiry."""
    result = authority_claim_service.reply_to_inquiry(
        db, authority, inquiry_id, payload.reply_type
    )
    db.commit()
    return result


@router.get("/handover", response_model=HandoverQueueResponse)
def authority_handover_queue(
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """Verified claims and in-progress handovers at this drop point (Section 11)."""
    return handover_service.list_handover_queue(db, authority)


@router.get("/handover/{handover_id}", response_model=HandoverAuthorityDetail)
def authority_get_handover(
    handover_id: UUID,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    return handover_service.get_handover_for_authority(db, authority, handover_id)


@router.post("/handover/{claim_id}/start", response_model=HandoverStartResponse)
def authority_start_handover(
    claim_id: UUID,
    payload: HandoverStartRequest,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """Capture condition photo + claimant details (Section 11)."""
    result = handover_service.start_handover(db, authority, claim_id, payload)
    db.commit()
    return result


@router.post("/handover/{handover_id}/override", response_model=HandoverAuthorityDetail)
def authority_override_handover(
    handover_id: UUID,
    payload: HandoverOverrideRequest,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    """Complete handover without owner digital confirmation (Section 11)."""
    result = handover_service.override_handover(db, authority, handover_id, payload)
    db.commit()
    return result


def _alert_response(row) -> AuthorityAlertResponse:
    return AuthorityAlertResponse(
        id=row.id,
        alert_type=row.alert_type.value,
        title=row.title,
        body=row.body,
        link=row.link,
        reference_id=row.reference_id,
        read=row.read,
        deletable=authority_alert_service.is_alert_deletable(row),
        created_at=row.created_at.isoformat(),
    )


@router.get("/alerts", response_model=AuthorityAlertsListResponse)
def authority_list_alerts(
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    rows = authority_alert_service.list_alerts(db, authority.id, skip=skip, limit=limit)
    unread = authority_alert_service.get_unread_count(db, authority.id)
    return AuthorityAlertsListResponse(
        alerts=[_alert_response(r) for r in rows],
        unread_count=unread,
    )


@router.patch("/alerts/{alert_id}/read", response_model=AuthorityAlertsActionResponse)
def authority_mark_alert_read(
    alert_id: UUID,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    if not authority_alert_service.mark_read(db, authority.id, alert_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    db.commit()
    return AuthorityAlertsActionResponse(message="Alert marked as read.")


@router.post("/alerts/read-all", response_model=AuthorityAlertsActionResponse)
def authority_mark_all_alerts_read(
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    count = authority_alert_service.mark_all_read(db, authority.id)
    db.commit()
    return AuthorityAlertsActionResponse(message=f"Marked {count} alert(s) as read.")


@router.delete("/alerts/{alert_id}", response_model=AuthorityAlertsActionResponse)
def authority_delete_alert(
    alert_id: UUID,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    if not authority_alert_service.delete_alert(db, authority.id, alert_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    db.commit()
    return AuthorityAlertsActionResponse(message="Alert deleted.")


@router.post("/alerts/clear-deletable", response_model=AuthorityAlertsActionResponse)
def authority_clear_deletable_alerts(
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    deleted = authority_alert_service.delete_deletable_alerts(db, authority.id)
    db.commit()
    return AuthorityAlertsActionResponse(
        message=f"Deleted {deleted} alert(s).",
        deleted_count=deleted,
    )


@router.get("/push-settings", response_model=StaffPushSettingsResponse)
def authority_get_push_settings(authority: Authority = Depends(get_current_authority)):
    return StaffPushSettingsResponse(push_notifications_enabled=authority.push_notifications_enabled)


@router.patch("/push-settings", response_model=StaffPushSettingsResponse)
def authority_update_push_settings(
    payload: StaffPushSettingsUpdate,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    authority.push_notifications_enabled = payload.push_notifications_enabled
    db.commit()
    return StaffPushSettingsResponse(push_notifications_enabled=authority.push_notifications_enabled)


@router.post("/push/subscribe", status_code=status.HTTP_201_CREATED)
def authority_push_subscribe(
    payload: StaffPushSubscribeRequest,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    from app.models.staff_push_subscription import StaffPushType
    from app.services.push_service import save_staff_subscription

    save_staff_subscription(
        db,
        staff_type=StaffPushType.AUTHORITY,
        staff_id=authority.id,
        endpoint=payload.endpoint,
        p256dh=payload.p256dh,
        auth=payload.auth,
    )
    return {"detail": "Subscribed to push notifications."}


@router.delete("/push/subscribe", status_code=status.HTTP_200_OK)
def authority_push_unsubscribe(
    payload: StaffPushUnsubscribeRequest,
    authority: Authority = Depends(get_current_authority),
    db: Session = Depends(get_db),
):
    from app.models.staff_push_subscription import StaffPushType
    from app.services.push_service import delete_staff_subscription

    deleted = delete_staff_subscription(
        db,
        staff_type=StaffPushType.AUTHORITY,
        staff_id=authority.id,
        endpoint=payload.endpoint,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    return {"detail": "Unsubscribed."}

"""
Supervisor API — Section 5.4 / 15.2 (W14).
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.database import get_db
from app.core.deps import get_current_supervisor
from app.models.supervisor import Supervisor
from app.schemas.authority import (
    AuthorityClaimActionResponse,
    AuthorityClaimsComparisonResponse,
    AuthorityListItem,
    CreateAuthorityRequest,
)
from app.schemas.handover import HandoverAuthorityDetail, HandoverQueueResponse
from app.schemas.messaging import ReplyToInquiryRequest
from app.schemas.redemption import RedemptionLookupRequest, RedemptionLookupResponse
from app.schemas.supervisor import (
    ResetAuthorityPasswordRequest,
    SupervisorAlertsActionResponse,
    SupervisorAlertsListResponse,
    SupervisorAlertResponse,
    SupervisorAuthoritiesResponse,
    SupervisorClaimsListResponse,
    SupervisorEscalateDisputeRequest,
    SupervisorItemsResponse,
    SupervisorLoginRequest,
    SupervisorOverviewResponse,
    SupervisorProfileResponse,
    SupervisorScopedDashboardListResponse,
    SupervisorTokenResponse,
)
from app.schemas.staff_push import (
    StaffPushSettingsResponse,
    StaffPushSettingsUpdate,
    StaffPushSubscribeRequest,
    StaffPushUnsubscribeRequest,
)
from app.services import (
    authority_service,
    handover_service,
    redemption_service,
    supervisor_claim_service,
    supervisor_dashboard_service,
    supervisor_service,
)

router = APIRouter(prefix="/supervisor", tags=["supervisor"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/login", response_model=SupervisorTokenResponse)
@limiter.limit("5/minute")
def supervisor_login(
    request: Request,
    payload: SupervisorLoginRequest,
    db: Session = Depends(get_db),
):
    """Email + password login — no OTP (Section 15.2)."""
    token = supervisor_service.login_supervisor(db, payload.email, payload.password)
    return SupervisorTokenResponse(access_token=token)


@router.get("/me", response_model=SupervisorProfileResponse)
def supervisor_me(supervisor: Supervisor = Depends(get_current_supervisor)):
    return supervisor_service.build_supervisor_profile(supervisor)


@router.get("/overview", response_model=SupervisorOverviewResponse)
def supervisor_overview(
    drop_point_id: Optional[UUID] = Query(None),
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    return supervisor_dashboard_service.get_overview(db, supervisor, drop_point_id=drop_point_id)


@router.get("/incoming", response_model=SupervisorScopedDashboardListResponse)
def supervisor_list_incoming(
    drop_point_id: Optional[UUID] = Query(None),
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    return supervisor_dashboard_service.list_incoming_items(
        db, supervisor, drop_point_id=drop_point_id
    )


@router.get("/at-droppoint", response_model=SupervisorScopedDashboardListResponse)
def supervisor_list_at_droppoint(
    drop_point_id: Optional[UUID] = Query(None),
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    return supervisor_dashboard_service.list_at_droppoint_items(
        db, supervisor, drop_point_id=drop_point_id
    )


@router.get("/items", response_model=SupervisorItemsResponse)
def supervisor_list_items(
    drop_point_id: Optional[UUID] = Query(None),
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    return supervisor_dashboard_service.list_items(db, supervisor, drop_point_id=drop_point_id)


@router.get("/claims", response_model=SupervisorClaimsListResponse)
def supervisor_list_claims(
    drop_point_id: Optional[UUID] = Query(None),
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    return supervisor_dashboard_service.list_claim_items(
        db, supervisor, drop_point_id=drop_point_id
    )


@router.get("/claims/{found_item_id}", response_model=AuthorityClaimsComparisonResponse)
def supervisor_get_claims(
    found_item_id: UUID,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    return supervisor_dashboard_service.get_claims_for_item(db, supervisor, found_item_id)


@router.post("/claims/{claim_id}/call-to-collect", response_model=AuthorityClaimActionResponse)
def supervisor_call_to_collect(
    claim_id: UUID,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    result = supervisor_claim_service.call_claim_to_collect(db, supervisor, claim_id)
    db.commit()
    return result


@router.post("/claims/{claim_id}/verify", response_model=AuthorityClaimActionResponse)
def supervisor_verify_claim(
    claim_id: UUID,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    result = supervisor_claim_service.verify_claim(db, supervisor, claim_id)
    db.commit()
    return result


@router.post("/claims/{claim_id}/reject", response_model=AuthorityClaimActionResponse)
def supervisor_reject_claim(
    claim_id: UUID,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    result = supervisor_claim_service.reject_claim(db, supervisor, claim_id)
    db.commit()
    return result


@router.post("/inquiries/{inquiry_id}/reply", response_model=AuthorityClaimActionResponse)
def supervisor_reply_to_inquiry(
    inquiry_id: UUID,
    payload: ReplyToInquiryRequest,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    result = supervisor_claim_service.reply_to_inquiry(
        db, supervisor, inquiry_id, payload.reply_type
    )
    db.commit()
    return result


@router.post("/disputes/{found_item_id}/escalate")
def supervisor_escalate_dispute(
    found_item_id: UUID,
    payload: SupervisorEscalateDisputeRequest,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    result = supervisor_claim_service.escalate_dispute(
        db, supervisor, found_item_id, payload.note
    )
    db.commit()
    return result


@router.get("/handover", response_model=HandoverQueueResponse)
def supervisor_handover_queue(
    drop_point_id: Optional[UUID] = Query(None),
    completed_only: bool = Query(True),
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    return supervisor_dashboard_service.list_handovers(
        db, supervisor, drop_point_id=drop_point_id, completed_only=completed_only
    )


@router.get("/handover/{handover_id}", response_model=HandoverAuthorityDetail)
def supervisor_get_handover(
    handover_id: UUID,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    return handover_service.get_handover_for_supervisor(db, supervisor, handover_id)


@router.get("/authorities", response_model=SupervisorAuthoritiesResponse)
def supervisor_list_authorities(
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    scope = supervisor_service.assigned_drop_point_ids(supervisor)
    authorities = authority_service.list_authority_accounts_for_drop_points(db, scope)
    return SupervisorAuthoritiesResponse(authorities=authorities)


@router.post("/authorities", response_model=AuthorityListItem, status_code=201)
def supervisor_create_authority(
    payload: CreateAuthorityRequest,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    scope = supervisor_service.assigned_drop_point_ids(supervisor)
    result = authority_service.create_authority_account(
        db, payload, allowed_drop_point_ids=scope
    )
    db.commit()
    return result


@router.patch("/authorities/{authority_id}/deactivate", response_model=AuthorityListItem)
def supervisor_deactivate_authority(
    authority_id: UUID,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    scope = supervisor_service.assigned_drop_point_ids(supervisor)
    result = authority_service.set_authority_active(
        db, authority_id, active=False, allowed_drop_point_ids=scope
    )
    db.commit()
    return result


@router.patch("/authorities/{authority_id}/activate", response_model=AuthorityListItem)
def supervisor_activate_authority(
    authority_id: UUID,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    scope = supervisor_service.assigned_drop_point_ids(supervisor)
    result = authority_service.set_authority_active(
        db, authority_id, active=True, allowed_drop_point_ids=scope
    )
    db.commit()
    return result


@router.post("/authorities/{authority_id}/reset-password", response_model=AuthorityListItem)
def supervisor_reset_authority_password(
    authority_id: UUID,
    payload: ResetAuthorityPasswordRequest,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    scope = supervisor_service.assigned_drop_point_ids(supervisor)
    result = authority_service.reset_authority_password(
        db,
        authority_id,
        payload.password,
        allowed_drop_point_ids=scope,
    )
    db.commit()
    return result


@router.post("/redemption/lookup", response_model=RedemptionLookupResponse)
def supervisor_redemption_lookup(
    payload: RedemptionLookupRequest,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    result = redemption_service.lookup_and_redeem_code(
        db, payload.code, supervisor=supervisor
    )
    db.commit()
    return result


@router.get("/alerts", response_model=SupervisorAlertsListResponse)
def supervisor_list_alerts(
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    from app.services import supervisor_alert_service

    rows = supervisor_alert_service.list_alerts(db, supervisor.id, skip=skip, limit=limit)
    unread = supervisor_alert_service.get_unread_count(db, supervisor.id)
    return SupervisorAlertsListResponse(
        alerts=[_supervisor_alert_response(r) for r in rows],
        unread_count=unread,
    )


def _supervisor_alert_response(row) -> SupervisorAlertResponse:
    from app.services import supervisor_alert_service

    return SupervisorAlertResponse(
        id=row.id,
        alert_type=row.alert_type.value,
        title=row.title,
        body=row.body,
        link=row.link,
        read=row.read,
        created_at=row.created_at,
        deletable=supervisor_alert_service.is_alert_deletable(row),
    )


@router.patch("/alerts/{alert_id}/read", response_model=SupervisorAlertsActionResponse)
def supervisor_mark_alert_read(
    alert_id: UUID,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    from app.services import supervisor_alert_service

    if not supervisor_alert_service.mark_read(db, supervisor.id, alert_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    db.commit()
    return SupervisorAlertsActionResponse(message="Alert marked as read.")


@router.post("/alerts/read-all", response_model=SupervisorAlertsActionResponse)
def supervisor_mark_all_alerts_read(
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    from app.services import supervisor_alert_service

    count = supervisor_alert_service.mark_all_read(db, supervisor.id)
    db.commit()
    return SupervisorAlertsActionResponse(message=f"Marked {count} alert(s) as read.")


@router.delete("/alerts/{alert_id}", response_model=SupervisorAlertsActionResponse)
def supervisor_delete_alert(
    alert_id: UUID,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    from app.services import supervisor_alert_service

    if not supervisor_alert_service.delete_alert(db, supervisor.id, alert_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    db.commit()
    return SupervisorAlertsActionResponse(message="Alert deleted.")


@router.post("/alerts/clear-deletable", response_model=SupervisorAlertsActionResponse)
def supervisor_clear_deletable_alerts(
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    from app.services import supervisor_alert_service

    deleted = supervisor_alert_service.delete_deletable_alerts(db, supervisor.id)
    db.commit()
    return SupervisorAlertsActionResponse(message=f"Deleted {deleted} alert(s).")


@router.get("/push-settings", response_model=StaffPushSettingsResponse)
def supervisor_get_push_settings(supervisor: Supervisor = Depends(get_current_supervisor)):
    return StaffPushSettingsResponse(push_notifications_enabled=supervisor.push_notifications_enabled)


@router.patch("/push-settings", response_model=StaffPushSettingsResponse)
def supervisor_update_push_settings(
    payload: StaffPushSettingsUpdate,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    supervisor.push_notifications_enabled = payload.push_notifications_enabled
    db.commit()
    return StaffPushSettingsResponse(push_notifications_enabled=supervisor.push_notifications_enabled)


@router.post("/push/subscribe", status_code=201)
def supervisor_push_subscribe(
    payload: StaffPushSubscribeRequest,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    from app.models.staff_push_subscription import StaffPushType
    from app.services.push_service import save_staff_subscription

    save_staff_subscription(
        db,
        staff_type=StaffPushType.SUPERVISOR,
        staff_id=supervisor.id,
        endpoint=payload.endpoint,
        p256dh=payload.p256dh,
        auth=payload.auth,
    )
    return {"detail": "Subscribed to push notifications."}


@router.delete("/push/subscribe")
def supervisor_push_unsubscribe(
    payload: StaffPushUnsubscribeRequest,
    supervisor: Supervisor = Depends(get_current_supervisor),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    from app.models.staff_push_subscription import StaffPushType
    from app.services.push_service import delete_staff_subscription

    deleted = delete_staff_subscription(
        db,
        staff_type=StaffPushType.SUPERVISOR,
        staff_id=supervisor.id,
        endpoint=payload.endpoint,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Subscription not found.")
    return {"detail": "Unsubscribed."}

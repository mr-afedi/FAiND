"""Admin dashboard API — Feature R (Section 26)."""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin_access, require_root_admin_access, require_redemption_admin_access
from app.models.user import User
from app.schemas.admin import (
    AdminGateResponse,
    PlatformAnalytics,
    AdminUsersResponse,
    AdminUserListItem,
    DisputesQueueResponse,
    DisputeQueueItem,
    PostsModerationResponse,
    PostModerationItem,
    AdminLogsResponse,
    AdminLogItem,
    AdminActionResult,
    AdminDetailResponse,
    SuspendUserRequest,
    ResolveDisputeRequest,
    ForceClosePostRequest,
    LockDisputeItemRequest,
    EscalateDisputeRequest,
    AdminSearchResponse,
    ReturnedItemsResponse,
    ReturnedItemListItem,
    OpenReturnDisputeRequest,
    AdminClaimsOverviewResponse,
    AdminClaimOverviewItem,
)
from app.schemas.admin_drop_point import (
    AdminDropPointListResponse,
    AdminDropPointListItem,
    CreateDropPointRequest,
    UpdateDropPointRequest,
)
from app.schemas.authority import (
    AuthorityListItem,
    AuthorityListResponse,
    CreateAuthorityRequest,
    ReassignAuthorityRequest,
)
from app.schemas.token import TokenSettingsResponse, TokenSettingsUpdate
from app.schemas.redemption import RedemptionLookupRequest, RedemptionLookupResponse
from app.schemas.supervisor import (
    CreateSupervisorRequest,
    SupervisorListResponse,
    SupervisorListItem,
    UpdateSupervisorRequest,
)
from app.services import admin_dashboard_service, admin_detail_service, admin_drop_point_service, authority_service, token_settings_service, redemption_service, supervisor_service

router = APIRouter(prefix="/admin", tags=["admin-dashboard"])


@router.get("/gate", response_model=AdminGateResponse)
def admin_gate(admin: User = Depends(require_admin_access)):
    """Verify secret path header + admin JWT."""
    return AdminGateResponse(
        role=admin.role.value,
        is_root=admin.role.value == "root_admin",
    )


@router.get("/analytics", response_model=PlatformAnalytics)
def platform_analytics(
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return PlatformAnalytics(**admin_dashboard_service.get_platform_analytics(db))


@router.get("/search", response_model=AdminSearchResponse)
def admin_search(
    q: str = Query(..., min_length=2, max_length=120),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    data = admin_dashboard_service.admin_global_search(db, q)
    return AdminSearchResponse(**data)


@router.get("/users", response_model=AdminUsersResponse)
def list_users(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    data = admin_dashboard_service.list_admin_users(
        db,
        search=search,
        role=role,
        status=status,
        limit=limit,
        offset=offset,
    )
    return AdminUsersResponse(
        users=[AdminUserListItem.model_validate(u) for u in data["users"]],
        total=data["total"],
    )


@router.post("/users/{user_id}/suspend", response_model=AdminActionResult)
def suspend_user(
    user_id: uuid.UUID,
    payload: SuspendUserRequest,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    admin_dashboard_service.suspend_user(db, user_id, admin, payload.reason)
    return AdminActionResult(message="User suspended.")


@router.post("/users/{user_id}/unsuspend", response_model=AdminActionResult)
def unsuspend_user(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    admin_dashboard_service.unsuspend_user(db, user_id, admin)
    return AdminActionResult(message="User unsuspended.")


@router.get("/disputes", response_model=DisputesQueueResponse)
def disputes_queue(
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    rows = admin_dashboard_service.list_disputes_queue(db, limit=limit)
    return DisputesQueueResponse(disputes=[DisputeQueueItem.model_validate(r) for r in rows])


@router.get("/disputes/{dispute_id}", response_model=AdminDetailResponse)
def dispute_detail(
    dispute_id: uuid.UUID,
    dispute_type: Optional[str] = Query(None),
    _admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminDetailResponse(
        detail=admin_detail_service.get_dispute_detail(
            db, dispute_id, dispute_type=dispute_type
        )
    )


@router.post("/disputes/{return_id}/resolve", response_model=AdminActionResult)
def resolve_dispute(
    return_id: uuid.UUID,
    payload: ResolveDisputeRequest,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.resolve_dispute(
            db,
            return_id,
            admin,
            outcome=payload.outcome,
            note=payload.note,
        )
    )


@router.post("/disputes/{dispute_id}/lock-item", response_model=AdminActionResult)
def lock_dispute_item(
    dispute_id: uuid.UUID,
    payload: LockDisputeItemRequest,
    dispute_type: Optional[str] = Query(None),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.lock_dispute_item(
            db,
            dispute_id,
            admin,
            dispute_type=dispute_type,
            reason=payload.reason,
        )
    )


@router.post("/disputes/{dispute_id}/escalate", response_model=AdminActionResult)
def escalate_dispute(
    dispute_id: uuid.UUID,
    payload: EscalateDisputeRequest,
    dispute_type: Optional[str] = Query(None),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.escalate_dispute(
            db,
            dispute_id,
            admin,
            dispute_type=dispute_type,
            note=payload.note,
        )
    )


@router.get("/reports/{report_id}", response_model=AdminDetailResponse)
def report_detail(
    report_id: uuid.UUID,
    report_type: str = Query(..., pattern="^(post|user)$"),
    _admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminDetailResponse(
        detail=admin_detail_service.get_report_detail(
            db, report_id, report_type=report_type
        )
    )


@router.get("/users/{user_id}/detail", response_model=AdminDetailResponse)
def user_detail(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminDetailResponse(detail=admin_detail_service.get_user_detail(db, user_id))


@router.get("/returns", response_model=ReturnedItemsResponse)
def returned_items(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    university_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort: str = Query("returned_at_desc"),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    data = admin_dashboard_service.list_returned_items(
        db,
        limit=limit,
        offset=offset,
        category=category,
        university_id=university_id,
        date_from=date_from,
        date_to=date_to,
        sort=sort,
    )
    return ReturnedItemsResponse(
        items=[ReturnedItemListItem.model_validate(r) for r in data["items"]],
        total=data["total"],
    )


@router.get("/returns/{return_id}", response_model=AdminDetailResponse)
def returned_item_detail(
    return_id: uuid.UUID,
    _admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminDetailResponse(
        detail=admin_detail_service.get_returned_item_detail(db, return_id)
    )


@router.post("/returns/{return_id}/open-dispute", response_model=AdminActionResult)
def open_return_dispute(
    return_id: uuid.UUID,
    payload: OpenReturnDisputeRequest,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.admin_open_return_dispute(
            db, return_id, admin, reason=payload.reason
        )
    )


@router.get("/posts", response_model=PostsModerationResponse)
def posts_moderation(
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    has_reports: Optional[bool] = None,
    has_disputes: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    data = admin_dashboard_service.list_posts_moderation(
        db,
        limit=limit,
        offset=offset,
        search=search,
        status=status,
        category=category,
        has_reports=has_reports,
        has_disputes=has_disputes,
    )
    return PostsModerationResponse(
        posts=[PostModerationItem.model_validate(r) for r in data["posts"]],
        total=data["total"],
    )


@router.get("/posts/{item_id}", response_model=AdminDetailResponse)
def post_detail(
    item_id: uuid.UUID,
    _admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminDetailResponse(detail=admin_detail_service.get_post_detail(db, item_id))


@router.post("/posts/{item_id}/remove", response_model=AdminActionResult)
def remove_post(
    item_id: uuid.UUID,
    payload: ForceClosePostRequest,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.remove_post(db, item_id, admin, payload.reason)
    )


@router.post("/posts/{item_id}/force-close", response_model=AdminActionResult)
def remove_post_force_close(
    item_id: uuid.UUID,
    payload: ForceClosePostRequest,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.force_close_post(db, item_id, admin, payload.reason)
    )


@router.get("/logs", response_model=AdminLogsResponse)
def admin_logs(
    limit: int = Query(100, ge=1, le=200),
    admin_id: Optional[uuid.UUID] = None,
    action: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    rows = admin_dashboard_service.list_admin_logs(
        db,
        root,
        limit=limit,
        admin_id_filter=admin_id,
        action_filter=action,
        date_from=date_from,
        date_to=date_to,
    )
    return AdminLogsResponse(logs=[AdminLogItem.model_validate(r) for r in rows])


@router.get("/claims", response_model=AdminClaimsOverviewResponse)
def claims_overview(
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    rows = admin_dashboard_service.list_claims_overview(db)
    return AdminClaimsOverviewResponse(
        items=[AdminClaimOverviewItem.model_validate(r) for r in rows]
    )


@router.get("/claims/{found_item_id}", response_model=AdminDetailResponse)
def claim_overview_detail(
    found_item_id: uuid.UUID,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    return AdminDetailResponse(
        detail=admin_detail_service.get_claim_overview_detail(db, found_item_id)
    )


@router.get("/drop-points", response_model=AdminDropPointListResponse)
def list_admin_drop_points(
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    rows = admin_drop_point_service.list_all_drop_points(db)
    return AdminDropPointListResponse(
        drop_points=[AdminDropPointListItem.model_validate(r) for r in rows]
    )


@router.post("/drop-points", response_model=AdminDropPointListItem, status_code=status.HTTP_201_CREATED)
def create_admin_drop_point(
    payload: CreateDropPointRequest,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    result = admin_drop_point_service.create_drop_point(db, root, payload)
    db.commit()
    return result


@router.patch("/drop-points/{drop_point_id}", response_model=AdminDropPointListItem)
def update_admin_drop_point(
    drop_point_id: uuid.UUID,
    payload: UpdateDropPointRequest,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    result = admin_drop_point_service.update_drop_point(db, root, drop_point_id, payload)
    db.commit()
    return result


@router.get("/authorities", response_model=AuthorityListResponse)
def list_authorities(
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    return AuthorityListResponse(authorities=authority_service.list_authority_accounts(db))


@router.post("/authorities", response_model=AuthorityListItem, status_code=status.HTTP_201_CREATED)
def create_authority(
    payload: CreateAuthorityRequest,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    result = authority_service.create_authority_account(db, payload, actor=root)
    db.commit()
    return result


@router.patch("/authorities/{authority_id}/reassign", response_model=AuthorityListItem)
def reassign_authority(
    authority_id: uuid.UUID,
    payload: ReassignAuthorityRequest,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    result = authority_service.reassign_authority(
        db, authority_id, payload.drop_point_id, root
    )
    db.commit()
    return result


@router.patch("/authorities/{authority_id}/deactivate", response_model=AuthorityListItem)
def deactivate_authority(
    authority_id: uuid.UUID,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    result = authority_service.set_authority_active(db, authority_id, active=False, actor=root)
    db.commit()
    return result


@router.patch("/authorities/{authority_id}/activate", response_model=AuthorityListItem)
def activate_authority(
    authority_id: uuid.UUID,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    result = authority_service.set_authority_active(db, authority_id, active=True, actor=root)
    db.commit()
    return result


@router.get("/token-settings", response_model=TokenSettingsResponse)
def get_token_settings(
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    return token_settings_service.to_response(token_settings_service.get_settings(db))


@router.patch("/token-settings", response_model=TokenSettingsResponse)
def update_token_settings(
    payload: TokenSettingsUpdate,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    result = token_settings_service.update_settings(db, root, payload)
    db.commit()
    return result


@router.post("/redemption/lookup", response_model=RedemptionLookupResponse)
def redemption_lookup(
    payload: RedemptionLookupRequest,
    admin: User = Depends(require_redemption_admin_access),
    db: Session = Depends(get_db),
):
    result = redemption_service.lookup_and_redeem_code(db, payload.code, admin=admin)
    db.commit()
    return result


@router.get("/supervisors", response_model=SupervisorListResponse)
def list_supervisors(
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    rows = supervisor_service.list_supervisors(db)
    return SupervisorListResponse(supervisors=rows)


@router.post("/supervisors", response_model=SupervisorListItem, status_code=status.HTTP_201_CREATED)
def create_supervisor(
    payload: CreateSupervisorRequest,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    result = supervisor_service.create_supervisor(db, payload, actor=root)
    db.commit()
    return result


@router.patch("/supervisors/{supervisor_id}", response_model=SupervisorListItem)
def update_supervisor(
    supervisor_id: uuid.UUID,
    payload: UpdateSupervisorRequest,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    result = supervisor_service.update_supervisor(db, supervisor_id, payload, actor=root)
    db.commit()
    return result

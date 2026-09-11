"""Admin dashboard API — Feature R (Section 26)."""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin_access, require_root_admin_access
from app.models.user import User
from app.schemas.admin import (
    AdminGateResponse,
    PlatformAnalytics,
    AdminUsersResponse,
    AdminUserListItem,
    ClaimsQueueResponse,
    ClaimQueueItem,
    DisputesQueueResponse,
    DisputeQueueItem,
    PostsModerationResponse,
    PostModerationItem,
    AdminLogsResponse,
    AdminLogItem,
    AdminActionResult,
    AdminDetailResponse,
    PromoteAdminRequest,
    SuspendUserRequest,
    ResolveDisputeRequest,
    ResolveVerificationDisputeRequest,
    RejectClaimRequest,
    ForceClosePostRequest,
    RequestMoreInfoRequest,
    TrustAdjustRequest,
    LockDisputeItemRequest,
    EscalateDisputeRequest,
    AdminSearchResponse,
    ReturnedItemsResponse,
    ReturnedItemListItem,
    OpenReturnDisputeRequest,
)
from app.services import admin_dashboard_service, admin_detail_service

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
    trust_tier: Optional[str] = None,
    fraud_tier: Optional[str] = None,
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
        trust_tier=trust_tier,
        fraud_tier=fraud_tier,
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


@router.post("/users/{user_id}/trust-adjust", response_model=AdminActionResult)
def trust_adjust_user(
    user_id: uuid.UUID,
    payload: TrustAdjustRequest,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.adjust_user_trust(
            db, user_id, admin, delta=payload.delta, reason=payload.reason
        )
    )


@router.get("/claims", response_model=ClaimsQueueResponse)
def claims_queue(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    path: Optional[str] = None,
    score_min: Optional[float] = None,
    score_max: Optional[float] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    university_id: Optional[uuid.UUID] = None,
    sort: str = Query("created_at_asc"),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    data = admin_dashboard_service.list_claims_queue(
        db,
        limit=limit,
        offset=offset,
        path=path,
        score_min=score_min,
        score_max=score_max,
        date_from=date_from,
        date_to=date_to,
        university_id=university_id,
        sort=sort,
    )
    return ClaimsQueueResponse(
        claims=[ClaimQueueItem.model_validate(r) for r in data["claims"]],
        total=data["total"],
    )


@router.post("/claims/{match_id}/approve", response_model=AdminActionResult)
def approve_claim(
    match_id: uuid.UUID,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(**admin_dashboard_service.approve_claim(db, match_id, admin))


@router.post("/claims/{match_id}/reject", response_model=AdminActionResult)
def reject_claim(
    match_id: uuid.UUID,
    payload: RejectClaimRequest,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.reject_claim(db, match_id, admin, payload.note)
    )


@router.post("/claims/{match_id}/request-info", response_model=AdminActionResult)
def request_claim_info(
    match_id: uuid.UUID,
    payload: RequestMoreInfoRequest,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.request_more_info_claim(
            db, match_id, admin, payload.note
        )
    )


@router.get("/claims/{match_id}", response_model=AdminDetailResponse)
def claim_detail(
    match_id: uuid.UUID,
    _admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminDetailResponse(detail=admin_detail_service.get_claim_detail(db, match_id))


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


@router.post("/disputes/verification/{match_id}/resolve", response_model=AdminActionResult)
def resolve_verification_dispute(
    match_id: uuid.UUID,
    payload: ResolveVerificationDisputeRequest,
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminActionResult(
        **admin_dashboard_service.resolve_verification_dispute(
            db,
            match_id,
            admin,
            winner_match_id=payload.winner_match_id,
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


@router.get("/fraud/{user_id}/detail", response_model=AdminDetailResponse)
def fraud_detail(
    user_id: uuid.UUID,
    _admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    return AdminDetailResponse(detail=admin_detail_service.get_fraud_detail(db, user_id))


@router.get("/returns", response_model=ReturnedItemsResponse)
def returned_items(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    university_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    tipped: Optional[bool] = None,
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
        tipped=tipped,
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
def force_close_post(
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


@router.post("/admins/promote", response_model=AdminActionResult)
def promote_admin(
    payload: PromoteAdminRequest,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    admin_dashboard_service.promote_assistant_admin(db, payload.user_id, root)
    return AdminActionResult(message="User promoted to assistant root admin.")


@router.post("/admins/{user_id}/demote", response_model=AdminActionResult)
def demote_admin(
    user_id: uuid.UUID,
    root: User = Depends(require_root_admin_access),
    db: Session = Depends(get_db),
):
    admin_dashboard_service.demote_assistant_admin(db, user_id, root)
    return AdminActionResult(message="Assistant admin demoted to regular user.")

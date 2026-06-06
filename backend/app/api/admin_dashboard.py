"""Admin dashboard API — Feature R (Section 26)."""
import uuid
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
    PromoteAdminRequest,
    SuspendUserRequest,
    ResolveDisputeRequest,
    RejectClaimRequest,
    ForceClosePostRequest,
)
from app.services import admin_dashboard_service

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


@router.get("/users", response_model=AdminUsersResponse)
def list_users(
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    data = admin_dashboard_service.list_admin_users(db, search=search, limit=limit, offset=offset)
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


@router.get("/claims", response_model=ClaimsQueueResponse)
def claims_queue(
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    rows = admin_dashboard_service.list_claims_queue(db, limit=limit)
    return ClaimsQueueResponse(claims=[ClaimQueueItem.model_validate(r) for r in rows])


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


@router.get("/disputes", response_model=DisputesQueueResponse)
def disputes_queue(
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    rows = admin_dashboard_service.list_disputes_queue(db, limit=limit)
    return DisputesQueueResponse(disputes=[DisputeQueueItem.model_validate(r) for r in rows])


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


@router.get("/posts", response_model=PostsModerationResponse)
def posts_moderation(
    limit: int = Query(50, ge=1, le=100),
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    rows = admin_dashboard_service.list_posts_moderation(db, limit=limit)
    return PostsModerationResponse(posts=[PostModerationItem.model_validate(r) for r in rows])


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
    admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    rows = admin_dashboard_service.list_admin_logs(db, admin, limit=limit)
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

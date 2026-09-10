"""
AdminDashboardService — Feature R (Section 26).

Central admin operations: analytics, users, disputes, posts, audit logs.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.admin_log import AdminLog, AdminActionType
from app.models.item import Item, ItemStatus, ItemType
from app.models.item_return import ItemReturn
from app.models.potential_match import PotentialMatch, PotentialMatchStatus
from app.models.user import User, UserRole, AccountStatus
from app.models.notification import NotificationType
from app.models.report import PostReport, UserReport, ReportStatus
from app.models.drop_point import DropPoint
from app.models.claim import Claim, ClaimStatus
from app.models.handover import Handover
from app.models.token_ledger import TokenLedger, TokenLedgerReason
from app.services import notification_service, matching_service


def _now() -> datetime:
    return datetime.now(timezone.utc)


def log_action(
    db: Session,
    *,
    admin: User,
    action: AdminActionType,
    target_type: str,
    target_id: uuid.UUID | None = None,
    detail: dict | None = None,
) -> AdminLog:
    entry = AdminLog(
        admin_id=admin.id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail or {},
    )
    db.add(entry)
    db.flush()
    return entry


def log_actor_action(
    db: Session,
    *,
    action: AdminActionType,
    target_type: str,
    target_id: uuid.UUID | None = None,
    detail: dict | None = None,
    admin: User | None = None,
    authority_id: uuid.UUID | None = None,
) -> AdminLog:
    """Log actions by root admin or authority (authorities are not users)."""
    payload = dict(detail or {})
    if authority_id:
        payload["authority_id"] = str(authority_id)
        payload["actor_type"] = "authority"
    entry = AdminLog(
        admin_id=admin.id if admin else None,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=payload,
    )
    db.add(entry)
    db.flush()
    return entry


def get_platform_analytics(db: Session) -> dict:
    lost = db.query(func.count(Item.id)).filter(Item.item_type == ItemType.LOST).scalar() or 0
    found = db.query(func.count(Item.id)).filter(Item.item_type == ItemType.FOUND).scalar() or 0
    returned = (
        db.query(func.count(ItemReturn.id))
        .filter(ItemReturn.returned_at.isnot(None))
        .scalar()
        or 0
    )
    denom = lost + found
    return_rate = round((returned / denom) * 100, 1) if denom else 0.0

    claims_pending = (
        db.query(func.count(Claim.id))
        .filter(Claim.status == ClaimStatus.PENDING)
        .scalar()
        or 0
    )
    disputes_open = len(list_disputes_queue(db, limit=200))
    reports_pending = (
        db.query(func.count(PostReport.id)).filter(PostReport.status == ReportStatus.PENDING).scalar()
        or 0
    ) + (
        db.query(func.count(UserReport.id)).filter(UserReport.status == ReportStatus.PENDING).scalar()
        or 0
    )

    now = _now()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    lost_this_week = (
        db.query(func.count(Item.id))
        .filter(Item.item_type == ItemType.LOST, Item.created_at >= week_ago)
        .scalar()
        or 0
    )
    found_this_week = (
        db.query(func.count(Item.id))
        .filter(Item.item_type == ItemType.FOUND, Item.created_at >= week_ago)
        .scalar()
        or 0
    )
    returned_this_week = (
        db.query(func.count(ItemReturn.id))
        .filter(ItemReturn.returned_at.isnot(None), ItemReturn.returned_at >= week_ago)
        .scalar()
        or 0
    )

    avg_days_post_to_return: float | None = None
    completed_returns = (
        db.query(ItemReturn)
        .filter(ItemReturn.returned_at.isnot(None))
        .limit(500)
        .all()
    )
    if completed_returns:
        deltas: list[float] = []
        for rec in completed_returns:
            item = db.query(Item).filter(Item.id == rec.lost_item_id).first()
            if item and item.created_at and rec.returned_at:
                delta = (rec.returned_at - item.created_at).total_seconds() / 86400
                if delta >= 0:
                    deltas.append(delta)
        if deltas:
            avg_days_post_to_return = round(sum(deltas) / len(deltas), 1)

    disputes_opened_total = (
        db.query(func.count(ItemReturn.id))
        .filter(ItemReturn.dispute_filed_at.isnot(None))
        .scalar()
        or 0
    )
    disputes_resolved_total = (
        db.query(func.count(ItemReturn.id))
        .filter(ItemReturn.dispute_resolved_at.isnot(None))
        .scalar()
        or 0
    )

    active_daily = (
        db.query(func.count(User.id))
        .filter(User.last_login_at.isnot(None), User.last_login_at >= day_ago)
        .scalar()
        or 0
    )
    active_weekly = (
        db.query(func.count(User.id))
        .filter(User.last_login_at.isnot(None), User.last_login_at >= week_ago)
        .scalar()
        or 0
    )
    active_monthly = (
        db.query(func.count(User.id))
        .filter(User.last_login_at.isnot(None), User.last_login_at >= month_ago)
        .scalar()
        or 0
    )

    active_7d = (
        db.query(func.count(func.distinct(Item.posted_by_id)))
        .filter(Item.created_at >= week_ago)
        .scalar()
        or 0
    )
    active_30d = (
        db.query(func.count(func.distinct(Item.posted_by_id)))
        .filter(Item.created_at >= month_ago)
        .scalar()
        or 0
    )

    found_with_dropoff = (
        db.query(func.count(Item.id))
        .filter(Item.item_type == ItemType.FOUND, Item.dropoff_confirmed_at.isnot(None))
        .scalar()
        or 0
    )
    drop_off_rate = round((found_with_dropoff / found) * 100, 1) if found else 0.0

    dropoff_items = (
        db.query(Item)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.dropoff_confirmed_at.isnot(None),
            Item.created_at.isnot(None),
        )
        .limit(1000)
        .all()
    )
    dropoff_hours: list[float] = []
    for item in dropoff_items:
        if item.dropoff_confirmed_at and item.created_at:
            hrs = (item.dropoff_confirmed_at - item.created_at).total_seconds() / 3600
            if hrs >= 0:
                dropoff_hours.append(hrs)
    avg_hours_to_drop_off = round(sum(dropoff_hours) / len(dropoff_hours), 1) if dropoff_hours else None

    verified_claims = (
        db.query(Claim, Item)
        .join(Item, Claim.found_item_id == Item.id)
        .filter(Claim.status == ClaimStatus.VERIFIED, Item.dropoff_confirmed_at.isnot(None))
        .limit(1000)
        .all()
    )
    claim_hours: list[float] = []
    for claim, item in verified_claims:
        if claim.created_at and item.dropoff_confirmed_at:
            hrs = (claim.created_at - item.dropoff_confirmed_at).total_seconds() / 3600
            if hrs >= 0:
                claim_hours.append(hrs)
    avg_hours_to_claim = round(sum(claim_hours) / len(claim_hours), 1) if claim_hours else None

    dp_counts = (
        db.query(DropPoint.id, DropPoint.name, func.count(Item.id))
        .outerjoin(Item, (Item.drop_point_id == DropPoint.id) & (Item.item_type == ItemType.FOUND))
        .group_by(DropPoint.id, DropPoint.name)
        .order_by(DropPoint.name)
        .all()
    )
    items_per_drop_point = [
        {
            "drop_point_id": dp_id,
            "drop_point_name": dp_name,
            "found_item_count": int(cnt),
        }
        for dp_id, dp_name, cnt in dp_counts
    ]

    tokens_total_issued = (
        db.query(func.coalesce(func.sum(TokenLedger.delta), 0))
        .filter(TokenLedger.delta > 0)
        .scalar()
        or 0
    )
    tokens_total_redeemed = (
        db.query(func.coalesce(func.sum(func.abs(TokenLedger.delta)), 0))
        .filter(
            TokenLedger.reason == TokenLedgerReason.REDEMPTION,
            TokenLedger.delta < 0,
        )
        .scalar()
        or 0
    )

    return {
        "total_lost_items": lost,
        "total_found_items": found,
        "total_returned": returned,
        "return_rate_percent": return_rate,
        "drop_off_rate_percent": drop_off_rate,
        "avg_hours_to_drop_off": avg_hours_to_drop_off,
        "avg_hours_to_claim": avg_hours_to_claim,
        "items_per_drop_point": items_per_drop_point,
        "tokens_total_issued": int(tokens_total_issued),
        "tokens_total_redeemed": int(tokens_total_redeemed),
        "claims_pending_review": claims_pending,
        "disputes_open": disputes_open,
        "reports_pending": reports_pending,
        "active_users_7d": active_7d,
        "active_users_30d": active_30d,
        "lost_items_this_week": lost_this_week,
        "found_items_this_week": found_this_week,
        "returned_this_week": returned_this_week,
        "avg_days_post_to_return": avg_days_post_to_return,
        "disputes_opened_total": disputes_opened_total,
        "disputes_resolved_total": disputes_resolved_total,
        "active_users_daily": active_daily,
        "active_users_weekly": active_weekly,
        "active_users_monthly": active_monthly,
    }


def list_admin_users(
    db: Session,
    *,
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    q = db.query(User).order_by(User.created_at.desc())
    if search:
        term = f"%{search.strip().lower()}%"
        q = q.filter(
            or_(
                func.lower(User.email).like(term),
                func.lower(User.username).like(term),
                func.lower(User.full_name).like(term),
            )
        )
    if role:
        try:
            q = q.filter(User.role == UserRole(role))
        except ValueError:
            pass
    if status:
        try:
            q = q.filter(User.status == AccountStatus(status))
        except ValueError:
            pass
    total = q.count()
    rows = q.offset(offset).limit(min(limit, 200)).all()
    return {
        "users": [
            {
                "id": u.id,
                "email": u.email,
                "username": u.username,
                "full_name": u.full_name,
                "role": u.role.value,
                "status": u.status.value,
                "created_at": u.created_at,
                "suspended_at": u.suspended_at,
            }
            for u in rows
        ],
        "total": total,
    }


def suspend_user(db: Session, user_id: uuid.UUID, admin: User, reason: str | None = None) -> User:
    from app.services import suspension_service

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return suspension_service.suspend_user(
        db,
        target,
        admin,
        reason=reason,
        log_action=log_action,
    )


def unsuspend_user(db: Session, user_id: uuid.UUID, admin: User) -> User:
    from app.services import suspension_service

    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return suspension_service.unsuspend_user(
        db,
        target,
        admin,
        log_action=log_action,
    )


def list_disputes_queue(db: Session, limit: int = 50) -> list[dict]:
    items: list[dict] = []
    seen_keys: set[str] = set()

    return_rows = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.dispute_filed_at.isnot(None),
            ItemReturn.dispute_resolved_at.is_(None),
        )
        .order_by(ItemReturn.dispute_filed_at.asc())
        .limit(min(limit, 100))
        .all()
    )
    for r in return_rows:
        key = f"return:{r.id}"
        seen_keys.add(key)
        lost_owner = db.query(User).filter(User.id == r.lost_owner_id).first()
        found_owner = db.query(User).filter(User.id == r.found_owner_id).first()
        filed_by = (
            db.query(User).filter(User.id == r.dispute_filed_by_id).first()
            if r.dispute_filed_by_id
            else None
        )
        lost_item = db.query(Item).filter(Item.id == r.lost_item_id).first()
        label = lost_item.public_description[:80] if lost_item else "Return dispute"
        items.append(
            {
                "dispute_id": r.id,
                "dispute_type": "return",
                "return_id": r.id,
                "match_id": r.potential_match_id,
                "returned_at": r.returned_at,
                "dispute_filed_at": r.dispute_filed_at,
                "dispute_reason": r.dispute_reason or "",
                "filed_by_id": r.dispute_filed_by_id,
                "filed_by_name": filed_by.full_name if filed_by else "Unknown",
                "lost_owner_name": lost_owner.full_name if lost_owner else "",
                "found_owner_name": found_owner.full_name if found_owner else "",
                "item_label": label,
            }
        )

    manual_rows = (
        db.query(ItemReturn)
        .filter(
            ItemReturn.admin_review_flagged.is_(True),
            ItemReturn.dispute_filed_at.is_(None),
            ItemReturn.dispute_resolved_at.is_(None),
        )
        .order_by(ItemReturn.created_at.asc())
        .limit(min(limit, 100))
        .all()
    )
    for r in manual_rows:
        key = f"return:{r.id}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        lost_item = db.query(Item).filter(Item.id == r.lost_item_id).first()
        label = lost_item.public_description[:80] if lost_item else "Manual review"
        items.append(
            {
                "dispute_id": r.id,
                "dispute_type": "manual",
                "return_id": r.id,
                "match_id": r.potential_match_id,
                "returned_at": r.returned_at,
                "dispute_filed_at": None,
                "dispute_reason": "Flagged for admin review (unconfirmed return)",
                "filed_by_id": None,
                "filed_by_name": "System",
                "lost_owner_name": "",
                "found_owner_name": "",
                "item_label": label,
            }
        )

    items.sort(
        key=lambda x: (
            x["dispute_filed_at"] or x.get("returned_at") or datetime.min.replace(tzinfo=timezone.utc)
        )
    )
    return items[: min(limit, 100)]


def resolve_dispute(
    db: Session,
    return_id: uuid.UUID,
    admin: User,
    *,
    outcome: str,
    note: str,
) -> dict:
    record = db.query(ItemReturn).filter(ItemReturn.id == return_id).first()
    if not record or record.dispute_resolved_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open dispute not found.")

    is_return_dispute = record.dispute_filed_at is not None
    is_manual_review = record.admin_review_flagged and not record.dispute_filed_at
    if not is_return_dispute and not is_manual_review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Open dispute not found.")

    dispute_type = "return" if is_return_dispute else "manual"
    now = _now()
    record.dispute_resolved_at = now
    record.dispute_resolution_note = note.strip()
    record.dispute_resolved_by_id = admin.id
    record.admin_review_flagged = False

    item_status_before: dict[str, str] = {}
    for item_id in (record.lost_item_id, record.found_item_id):
        item = db.query(Item).filter(Item.id == item_id).first()
        if item:
            item_status_before[str(item_id)] = item.status.value
        if item and item.status == ItemStatus.UNDER_DISPUTE:
            if record.returned_at:
                item.status = ItemStatus.RETURNED
            else:
                item.status = ItemStatus.POTENTIAL_MATCH
            item.updated_at = now
        matching_service.resume_matches_for_item(db, item_id)

    flagged_user_id: Optional[uuid.UUID] = None
    if outcome == "flagged":
        if record.dispute_filed_by_id == record.lost_owner_id:
            flagged_user_id = record.found_owner_id
        elif record.dispute_filed_by_id == record.found_owner_id:
            flagged_user_id = record.lost_owner_id
        else:
            flagged_user_id = record.found_owner_id

    log_action(
        db,
        admin=admin,
        action=AdminActionType.RESOLVE_DISPUTE,
        target_type="item_return",
        target_id=record.id,
        detail={
            "dispute_type": dispute_type,
            "outcome": outcome,
            "note": note[:200],
            "item_status_before": item_status_before,
            **({"flagged_user_id": str(flagged_user_id)} if flagged_user_id else {}),
        },
    )
    db.commit()
    return {"success": True, "message": f"Dispute marked as {outcome.replace('_', ' ')}."}


def list_posts_moderation(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
    search: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    has_reports: Optional[bool] = None,
    has_disputes: Optional[bool] = None,
) -> dict:
    """All active campus posts — flagged/reported items sorted to the top."""
    q = db.query(Item).filter(
        Item.status.notin_([ItemStatus.ARCHIVED, ItemStatus.EXPIRED]),
    )
    if search and search.strip():
        term = f"%{search.strip()}%"
        q = q.filter(Item.public_description.ilike(term))
    if status:
        try:
            q = q.filter(Item.status == ItemStatus(status))
        except ValueError:
            pass
    if category:
        from app.models.item import ItemCategory

        try:
            q = q.filter(Item.category == ItemCategory(category))
        except ValueError:
            pass

    rows = q.order_by(Item.updated_at.desc()).limit(500).all()
    posts: list[dict] = []
    for item in rows:
        report_count = (
            db.query(func.count(PostReport.id))
            .filter(
                PostReport.item_id == item.id,
                PostReport.status == ReportStatus.PENDING,
            )
            .scalar()
            or 0
        )
        disputes_count = (
            db.query(func.count(ItemReturn.id))
            .filter(
                or_(
                    ItemReturn.lost_item_id == item.id,
                    ItemReturn.found_item_id == item.id,
                ),
                ItemReturn.dispute_filed_at.isnot(None),
                ItemReturn.dispute_resolved_at.is_(None),
            )
            .scalar()
            or 0
        )
        if has_reports is True and report_count == 0:
            continue
        if has_reports is False and report_count > 0:
            continue
        if has_disputes is True and disputes_count == 0:
            continue
        if has_disputes is False and disputes_count > 0:
            continue
        poster = db.query(User).filter(User.id == item.posted_by_id).first()
        flagged = (
            int(report_count or 0) > 0
            or bool(item.admin_locked)
            or item.status == ItemStatus.UNDER_DISPUTE
        )
        posts.append(
            {
                "item_id": item.id,
                "item_type": item.item_type.value,
                "category": item.category.value,
                "status": item.status.value,
                "public_description": item.public_description,
                "posted_by_name": poster.full_name if poster else "Anonymous finder",
                "posted_by_id": item.posted_by_id,
                "admin_locked": bool(item.admin_locked),
                "pending_reports": int(report_count or 0),
                "disputes_count": int(disputes_count or 0),
                "flagged": flagged,
                "created_at": item.created_at,
                "updated_at": item.updated_at,
            }
        )

    posts.sort(
        key=lambda p: (
            0 if p["pending_reports"] > 0 else 1,
            0 if p["admin_locked"] else 1,
            0 if p["status"] == ItemStatus.UNDER_DISPUTE.value else 1,
            -(p["updated_at"].timestamp() if p["updated_at"] else 0),
        )
    )
    total = len(posts)
    page = posts[offset : offset + min(limit, 100)]
    return {"posts": page, "total": total}


def remove_post(
    db: Session, item_id: uuid.UUID, admin: User, reason: str | None = None
) -> dict:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item or item.status == ItemStatus.ARCHIVED:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    before = item.status.value
    item.status = ItemStatus.ARCHIVED
    item.admin_locked = True
    item.updated_at = _now()
    matching_service.cleanup_on_item_archive(db, item.id)
    log_action(
        db,
        admin=admin,
        action=AdminActionType.REMOVE_POST,
        target_type="item",
        target_id=item.id,
        detail={"reason": reason or "", "status_before": before, "status_after": "archived"},
    )
    if item.drop_point_id:
        from app.models.drop_point import DropPoint
        from app.services import authority_notification_service

        drop_point = db.query(DropPoint).filter(DropPoint.id == item.drop_point_id).first()
        if drop_point:
            authority_notification_service.notify_authority_item_removed(
                db, item=item, drop_point=drop_point
            )
    db.commit()
    return {"success": True, "message": "Post removed."}


def force_close_post(
    db: Session, item_id: uuid.UUID, admin: User, reason: str | None = None
) -> dict:
    item = db.query(Item).filter(Item.id == item_id).first()
    if not item or item.status in (ItemStatus.ARCHIVED, ItemStatus.CLOSED):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    before = item.status.value
    item.status = ItemStatus.CLOSED
    item.admin_locked = True
    item.updated_at = _now()
    matching_service.cleanup_on_item_archive(db, item.id)
    log_action(
        db,
        admin=admin,
        action=AdminActionType.FORCE_CLOSE_POST,
        target_type="item",
        target_id=item.id,
        detail={
            "reason": reason or "",
            "status_before": before,
            "status_after": ItemStatus.CLOSED.value,
        },
    )
    db.commit()
    return {"success": True, "message": "Post force-closed."}


def list_returned_items(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    category: Optional[str] = None,
    university_id: Optional[uuid.UUID] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    sort: str = "returned_at_desc",
) -> dict:
    """Completed returns — historical record for admin Returned Items tab."""
    from app.models.item import ItemCategory

    rows = (
        db.query(ItemReturn)
        .filter(ItemReturn.returned_at.isnot(None))
        .order_by(ItemReturn.returned_at.desc())
        .limit(2000)
        .all()
    )
    items: list[dict] = []
    for record in rows:
        lost = db.query(Item).filter(Item.id == record.lost_item_id).first()
        found = db.query(Item).filter(Item.id == record.found_item_id).first()
        if not lost or not found:
            continue
        cat = lost.category.value
        if category:
            try:
                if cat != ItemCategory(category).value:
                    continue
            except ValueError:
                pass
        if university_id and record.university_id != university_id:
            continue
        if date_from and record.returned_at and record.returned_at < date_from:
            continue
        if date_to and record.returned_at and record.returned_at > date_to:
            continue
        owner = db.query(User).filter(User.id == record.lost_owner_id).first()
        finder = db.query(User).filter(User.id == record.found_owner_id).first()
        drop_point_name = None
        handover_completed = False
        handover_authority_override = False
        handover_owner_confirmed = False
        if found and found.drop_point_id:
            dp = db.query(DropPoint).filter(DropPoint.id == found.drop_point_id).first()
            drop_point_name = dp.name if dp else None
        handover = (
            db.query(Handover)
            .filter(Handover.item_id == record.found_item_id)
            .first()
        )
        if handover:
            handover_completed = bool(handover.owner_confirmed or handover.authority_override_note)
            handover_authority_override = bool(handover.authority_override_note)
            handover_owner_confirmed = bool(handover.owner_confirmed)
        date_dropped_off = found.authority_received_at if found and found.authority_received_at else None
        items.append(
            {
                "return_id": record.id,
                "item_description": (lost.public_description if lost and lost.id != found.id else found.public_description)[:120],
                "category": cat,
                "owner_name": owner.full_name if owner else "",
                "owner_username": owner.username if owner else "",
                "finder_name": finder.full_name if finder else ("Anonymous finder" if found and not found.posted_by_id else ""),
                "finder_username": finder.username if finder else "",
                "date_lost": lost.date_occurred if lost and lost.id != found.id else None,
                "date_found": found.date_occurred,
                "date_dropped_off": date_dropped_off,
                "date_returned": record.returned_at,
                "university_id": record.university_id,
                "drop_point_name": drop_point_name,
                "handover_completed": handover_completed,
                "handover_authority_override": handover_authority_override,
                "handover_owner_confirmed": handover_owner_confirmed,
            }
        )

    reverse = sort.endswith("_desc")
    key_name = sort.replace("_asc", "").replace("_desc", "")
    if key_name == "category":
        items.sort(key=lambda x: x["category"], reverse=reverse)
    elif key_name == "owner":
        items.sort(key=lambda x: (x["owner_name"] or "").lower(), reverse=reverse)
    elif key_name == "finder":
        items.sort(key=lambda x: (x["finder_name"] or "").lower(), reverse=reverse)
    elif key_name == "date_lost":
        items.sort(key=lambda x: x["date_lost"] or datetime.min.replace(tzinfo=timezone.utc), reverse=reverse)
    elif key_name == "date_found":
        items.sort(key=lambda x: x["date_found"] or datetime.min.replace(tzinfo=timezone.utc), reverse=reverse)
    else:
        items.sort(key=lambda x: x["date_returned"] or datetime.min.replace(tzinfo=timezone.utc), reverse=reverse)

    total = len(items)
    page = items[offset : offset + min(limit, 100)]
    return {"items": page, "total": total}


def list_claims_overview(db: Session) -> list[dict]:
    """Platform-wide claims grouped by found item (W15)."""
    rows = (
        db.query(
            Item,
            DropPoint,
            func.count(Claim.id).label("claim_count"),
            func.count(Claim.id).filter(Claim.status == ClaimStatus.PENDING).label("pending_count"),
            func.count(Claim.id).filter(Claim.status == ClaimStatus.VERIFIED).label("verified_count"),
            func.count(Claim.id).filter(Claim.status == ClaimStatus.REJECTED).label("rejected_count"),
        )
        .join(Claim, Claim.found_item_id == Item.id)
        .join(DropPoint, Item.drop_point_id == DropPoint.id)
        .filter(Item.item_type == ItemType.FOUND)
        .group_by(Item.id, DropPoint.id)
        .order_by(func.max(Claim.created_at).desc())
        .limit(500)
        .all()
    )
    return [
        {
            "found_item_id": item.id,
            "drop_point_id": drop_point.id,
            "drop_point_name": drop_point.name,
            "found_item_status": item.status.value,
            "found_item_category": item.category.value,
            "found_item_description": item.public_description,
            "claim_count": int(claim_count),
            "pending_count": int(pending_count),
            "verified_count": int(verified_count),
            "rejected_count": int(rejected_count),
        }
        for item, drop_point, claim_count, pending_count, verified_count, rejected_count in rows
    ]


def admin_open_return_dispute(
    db: Session,
    return_id: uuid.UUID,
    admin: User,
    *,
    reason: str,
) -> dict:
    """Admin-initiated manual dispute on a completed return (Section 19)."""
    record = db.query(ItemReturn).filter(ItemReturn.id == return_id).first()
    if not record or not record.returned_at:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Return not found.")

    dispute_open = bool(
        record.dispute_filed_at
        or (record.admin_review_flagged and not record.dispute_resolved_at)
    )
    if dispute_open:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A dispute is already open for this return.",
        )

    reason = reason.strip()
    if len(reason) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason must be at least 10 characters.",
        )

    now = _now()
    record.admin_review_flagged = True
    record.dispute_reason = reason[:2000]
    record.dispute_resolved_at = None
    record.dispute_resolution_note = None

    for item_id in (record.lost_item_id, record.found_item_id):
        item = db.query(Item).filter(Item.id == item_id).first()
        if item:
            item.status = ItemStatus.UNDER_DISPUTE
            item.updated_at = now
        matching_service.pause_matches_for_item(db, item_id)

    from app.services import admin_notification_service

    admin_notification_service.notify_admins_manual_dispute(db, return_id=record.id)
    log_action(
        db,
        admin=admin,
        action=AdminActionType.OPEN_MANUAL_DISPUTE,
        target_type="item_return",
        target_id=record.id,
        detail={"reason": reason[:500]},
    )
    db.commit()
    return {
        "success": True,
        "message": "Manual dispute opened. Item status set to under dispute.",
    }


def admin_global_search(db: Session, query: str, *, limit: int = 8) -> dict:
    q = query.strip()
    if len(q) < 2:
        return {"query": q, "users": [], "items": []}

    term = f"%{q.lower()}%"
    users = (
        db.query(User)
        .filter(
            or_(
                func.lower(User.email).like(term),
                func.lower(User.username).like(term),
                func.lower(User.full_name).like(term),
            )
        )
        .limit(limit)
        .all()
    )
    user_hits = [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "full_name": u.full_name,
        }
        for u in users
    ]

    items_q = db.query(Item).filter(Item.public_description.ilike(f"%{q}%"))
    try:
        item_uuid = uuid.UUID(q)
        items_q = db.query(Item).filter(
            or_(Item.id == item_uuid, Item.public_description.ilike(f"%{q}%")),
        )
    except ValueError:
        pass
    items = items_q.limit(limit).all()
    item_hits = [
        {
            "id": i.id,
            "item_type": i.item_type.value,
            "public_description": i.public_description[:120],
            "status": i.status.value,
        }
        for i in items
    ]

    return {
        "query": q,
        "users": user_hits,
        "items": item_hits,
    }


def lock_dispute_item(
    db: Session,
    dispute_id: uuid.UUID,
    admin: User,
    *,
    dispute_type: Optional[str],
    reason: str,
) -> dict:
    reason = reason.strip()
    if len(reason) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reason must be at least 10 characters.",
        )
    record = db.query(ItemReturn).filter(ItemReturn.id == dispute_id).first()
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dispute not found.")
    item_ids = [record.lost_item_id, record.found_item_id]

    now = _now()
    locked: list[str] = []
    for item_id in item_ids:
        if not item_id:
            continue
        item = db.query(Item).filter(Item.id == item_id).first()
        if item:
            item.admin_locked = True
            item.updated_at = now
            matching_service.pause_matches_for_item(db, item_id)
            locked.append(str(item_id))

    log_action(
        db,
        admin=admin,
        action=AdminActionType.LOCK_ITEM,
        target_type="dispute",
        target_id=dispute_id,
        detail={"reason": reason, "locked_item_ids": locked, "dispute_type": dispute_type},
    )
    db.commit()
    return {"success": True, "message": "Item locked. No further claims until resolved."}


def escalate_dispute(
    db: Session,
    dispute_id: uuid.UUID,
    admin: User,
    *,
    dispute_type: Optional[str],
    note: str,
) -> dict:
    note = note.strip()
    if len(note) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Note must be at least 10 characters.",
        )
    from app.services import admin_notification_service

    link = admin_notification_service.admin_link(
        "disputes",
        dispute_id,
    )
    roots = (
        db.query(User)
        .filter(User.role == UserRole.ROOT_ADMIN, User.status == AccountStatus.ACTIVE)
        .all()
    )
    for root in roots:
        if root.id == admin.id:
            continue
        notification_service.create_notification(
            db,
            root.id,
            NotificationType.GENERAL,
            title="Dispute escalated",
            body=note[:500],
            link=link,
            reference_id=dispute_id,
        )
    log_action(
        db,
        admin=admin,
        action=AdminActionType.ESCALATE_DISPUTE,
        target_type="dispute",
        target_id=dispute_id,
        detail={"note": note, "dispute_type": dispute_type or "unknown"},
    )
    db.commit()
    return {"success": True, "message": "Escalated to root admin."}


def list_admin_logs(
    db: Session,
    admin: User,
    *,
    limit: int = 100,
    admin_id_filter: Optional[uuid.UUID] = None,
    action_filter: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> list[dict]:
    if admin.role != UserRole.ROOT_ADMIN:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")

    q = db.query(AdminLog).order_by(AdminLog.created_at.desc())
    if admin_id_filter:
        q = q.filter(AdminLog.admin_id == admin_id_filter)
    if action_filter:
        try:
            action_enum = AdminActionType(action_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action filter.",
            )
        q = q.filter(AdminLog.action == action_enum)
    if date_from:
        q = q.filter(AdminLog.created_at >= date_from)
    if date_to:
        q = q.filter(AdminLog.created_at <= date_to)
    rows = q.limit(min(limit, 200)).all()
    out = []
    for row in rows:
        actor = db.query(User).filter(User.id == row.admin_id).first() if row.admin_id else None
        out.append(
            {
                "id": row.id,
                "admin_id": row.admin_id,
                "admin_email": actor.email if actor else None,
                "action": row.action.value,
                "target_type": row.target_type,
                "target_id": row.target_id,
                "detail": row.detail or {},
                "created_at": row.created_at,
            }
        )
    return out

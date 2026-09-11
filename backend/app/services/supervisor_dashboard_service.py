"""
Supervisor dashboard — scoped items and claims (Section 5.4 / 15.2, W14).
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.claim import Claim, ClaimStatus
from app.models.drop_point import DropPoint
from app.models.handover import Handover
from app.models.item import Item, ItemStatus, ItemType
from app.models.supervisor import Supervisor
from app.schemas.authority import AuthorityClaimsComparisonResponse
from app.schemas.handover import HandoverQueueItem, HandoverQueueResponse
from app.schemas.supervisor import (
    SupervisorClaimItemSummary,
    SupervisorClaimsListResponse,
    SupervisorDashboardItem,
    SupervisorItemsResponse,
    SupervisorOverviewResponse,
    SupervisorOverviewStats,
    SupervisorScopedDashboardItem,
    SupervisorScopedDashboardListResponse,
)
from app.services import authority_claim_service, authority_dashboard_service, supervisor_service
from app.services.handover_service import _handover_status

_INCOMING_STATUSES = authority_dashboard_service._INCOMING_STATUSES


def _scoped_drop_point_ids(supervisor: Supervisor) -> list[uuid.UUID]:
    ids = list(supervisor_service.assigned_drop_point_ids(supervisor))
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No drop points assigned to this supervisor.",
        )
    return ids


def _resolve_filter_ids(
    supervisor: Supervisor,
    drop_point_id: Optional[uuid.UUID],
) -> list[uuid.UUID]:
    allowed = _scoped_drop_point_ids(supervisor)
    if drop_point_id:
        supervisor_service.assert_drop_point_in_scope(supervisor, drop_point_id)
        return [drop_point_id]
    return allowed


def _build_scoped_dashboard_item(item: Item, drop_point_name: str) -> SupervisorScopedDashboardItem:
    base = authority_dashboard_service._build_dashboard_item(item)
    return SupervisorScopedDashboardItem(
        **base.model_dump(),
        drop_point_id=item.drop_point_id,
        drop_point_name=drop_point_name,
    )


def get_overview(
    db: Session,
    supervisor: Supervisor,
    *,
    drop_point_id: Optional[uuid.UUID] = None,
) -> SupervisorOverviewResponse:
    filter_ids = _resolve_filter_ids(supervisor, drop_point_id)

    total_incoming = (
        db.query(Item)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id.in_(filter_ids),
            Item.status.in_(_INCOMING_STATUSES),
        )
        .count()
    )
    at_drop_point = (
        db.query(Item)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id.in_(filter_ids),
            Item.status == ItemStatus.AT_DROPPOINT,
        )
        .count()
    )
    active_claims = (
        db.query(Claim)
        .join(Item, Claim.found_item_id == Item.id)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id.in_(filter_ids),
            Claim.status == ClaimStatus.PENDING,
        )
        .count()
    )
    completed_handovers = (
        db.query(Handover)
        .join(Item, Handover.item_id == Item.id)
        .filter(
            Item.drop_point_id.in_(filter_ids),
            or_(
                Handover.owner_confirmed.is_(True),
                Handover.authority_override_note.isnot(None),
            ),
        )
        .count()
    )
    return SupervisorOverviewResponse(
        stats=SupervisorOverviewStats(
            total_incoming=total_incoming,
            at_drop_point=at_drop_point,
            active_claims=active_claims,
            completed_handovers=completed_handovers,
        )
    )


def list_incoming_items(
    db: Session,
    supervisor: Supervisor,
    *,
    drop_point_id: Optional[uuid.UUID] = None,
) -> SupervisorScopedDashboardListResponse:
    filter_ids = _resolve_filter_ids(supervisor, drop_point_id)
    rows = (
        db.query(Item, DropPoint.name)
        .join(DropPoint, Item.drop_point_id == DropPoint.id)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id.in_(filter_ids),
            Item.status.in_(_INCOMING_STATUSES),
        )
        .order_by(Item.created_at.asc())
        .all()
    )
    return SupervisorScopedDashboardListResponse(
        items=[_build_scoped_dashboard_item(item, dp_name) for item, dp_name in rows]
    )


def list_at_droppoint_items(
    db: Session,
    supervisor: Supervisor,
    *,
    drop_point_id: Optional[uuid.UUID] = None,
) -> SupervisorScopedDashboardListResponse:
    filter_ids = _resolve_filter_ids(supervisor, drop_point_id)
    rows = (
        db.query(Item, DropPoint.name)
        .join(DropPoint, Item.drop_point_id == DropPoint.id)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id.in_(filter_ids),
            Item.status == ItemStatus.AT_DROPPOINT,
        )
        .order_by(Item.dropoff_confirmed_at.desc().nullslast(), Item.updated_at.desc())
        .all()
    )
    return SupervisorScopedDashboardListResponse(
        items=[_build_scoped_dashboard_item(item, dp_name) for item, dp_name in rows]
    )


def list_handovers(
    db: Session,
    supervisor: Supervisor,
    *,
    drop_point_id: Optional[uuid.UUID] = None,
    completed_only: bool = False,
) -> HandoverQueueResponse:
    filter_ids = _resolve_filter_ids(supervisor, drop_point_id)

    if completed_only:
        handovers = (
            db.query(Handover)
            .join(Item, Handover.item_id == Item.id)
            .join(DropPoint, Item.drop_point_id == DropPoint.id)
            .options(
                joinedload(Handover.claim).joinedload(Claim.claimant),
                joinedload(Handover.item),
            )
            .filter(
                Item.drop_point_id.in_(filter_ids),
                or_(
                    Handover.owner_confirmed.is_(True),
                    Handover.authority_override_note.isnot(None),
                ),
            )
            .order_by(Handover.created_at.desc())
            .limit(200)
            .all()
        )
        items: list[HandoverQueueItem] = []
        for handover in handovers:
            claim = handover.claim
            item = handover.item
            if not claim or not item:
                continue
            dp = item.drop_point
            items.append(
                HandoverQueueItem(
                    claim_id=handover.claim_id,
                    handover_id=handover.id,
                    found_item_id=item.id,
                    found_item_description=item.public_description,
                    found_item_category=item.category.value,
                    claimant_name=handover.claimant_name,
                    queue_status="completed",
                    owner_confirmed=handover.owner_confirmed,
                    authority_override=bool(handover.authority_override_note),
                    condition_photo_url=handover.condition_photo_url,
                    created_at=handover.created_at,
                    completed_at=handover.owner_confirmed_at or handover.created_at,
                    drop_point_id=item.drop_point_id,
                    drop_point_name=dp.name if dp else None,
                )
            )
        return HandoverQueueResponse(items=items)

    claims = (
        db.query(Claim)
        .options(joinedload(Claim.claimant), joinedload(Claim.found_item).joinedload(Item.drop_point))
        .join(Item, Claim.found_item_id == Item.id)
        .filter(
            Item.drop_point_id.in_(filter_ids),
            Claim.status == ClaimStatus.VERIFIED,
        )
        .order_by(Claim.created_at.desc())
        .all()
    )

    handover_by_claim: dict[uuid.UUID, Handover] = {}
    claim_ids = [c.id for c in claims]
    if claim_ids:
        handover_by_claim = {
            h.claim_id: h
            for h in db.query(Handover).filter(Handover.claim_id.in_(claim_ids)).all()
        }

    items = []
    seen_claim_ids: set[uuid.UUID] = set()
    for claim in claims:
        handover = handover_by_claim.get(claim.id)
        status_key = _handover_status(handover)
        seen_claim_ids.add(claim.id)
        completed_at = None
        if handover and status_key == "completed":
            completed_at = handover.owner_confirmed_at or handover.created_at
        dp = claim.found_item.drop_point if claim.found_item else None
        items.append(
            HandoverQueueItem(
                claim_id=claim.id,
                handover_id=handover.id if handover else None,
                found_item_id=claim.found_item_id,
                found_item_description=claim.found_item.public_description,
                found_item_category=claim.found_item.category.value,
                claimant_name=(
                    handover.claimant_name
                    if handover
                    else (claim.claimant.full_name or claim.claimant.username)
                ),
                queue_status=status_key,
                owner_confirmed=handover.owner_confirmed if handover else False,
                authority_override=bool(handover.authority_override_note) if handover else False,
                condition_photo_url=handover.condition_photo_url if handover else None,
                created_at=handover.created_at if handover else None,
                completed_at=completed_at,
                drop_point_id=claim.found_item.drop_point_id,
                drop_point_name=dp.name if dp else None,
            )
        )
    return HandoverQueueResponse(items=items)


def list_items(
    db: Session,
    supervisor: Supervisor,
    *,
    drop_point_id: Optional[uuid.UUID] = None,
) -> SupervisorItemsResponse:
    filter_ids = _resolve_filter_ids(supervisor, drop_point_id)

    rows = (
        db.query(Item, DropPoint.name)
        .join(DropPoint, Item.drop_point_id == DropPoint.id)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id.in_(filter_ids),
            Item.status.notin_((ItemStatus.RETURNED, ItemStatus.CLOSED, ItemStatus.ARCHIVED)),
        )
        .order_by(Item.created_at.desc())
        .all()
    )
    items = [
        SupervisorDashboardItem(
            id=item.id,
            drop_point_id=item.drop_point_id,
            drop_point_name=dp_name,
            status=item.status.value,
            category=item.category.value,
            public_description=item.public_description,
            location_label=item.location_label,
            created_at=item.created_at,
            tracking_reference=item.tracking_reference,
        )
        for item, dp_name in rows
    ]
    return SupervisorItemsResponse(items=items)


def list_claim_items(
    db: Session,
    supervisor: Supervisor,
    *,
    drop_point_id: Optional[uuid.UUID] = None,
) -> SupervisorClaimsListResponse:
    filter_ids = _resolve_filter_ids(supervisor, drop_point_id)
    rows = (
        db.query(
            Item,
            DropPoint,
            func.count(Claim.id).label("claim_count"),
            func.count(Claim.id).filter(Claim.status == ClaimStatus.PENDING).label("pending_count"),
            func.count(Claim.id).filter(Claim.status == ClaimStatus.VERIFIED).label("verified_count"),
        )
        .join(Claim, Claim.found_item_id == Item.id)
        .join(DropPoint, Item.drop_point_id == DropPoint.id)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id.in_(filter_ids),
        )
        .group_by(Item.id, DropPoint.id)
        .order_by(func.max(Claim.created_at).desc())
        .all()
    )
    items = [
        SupervisorClaimItemSummary(
            found_item_id=item.id,
            drop_point_id=drop_point.id,
            drop_point_name=drop_point.name,
            found_item_status=item.status.value,
            found_item_category=item.category.value,
            found_item_description=item.public_description,
            claim_count=int(claim_count),
            pending_count=int(pending_count),
            has_dispute=int(pending_count) >= 2 or int(verified_count) >= 2,
        )
        for item, drop_point, claim_count, pending_count, verified_count in rows
    ]
    return SupervisorClaimsListResponse(items=items)


def get_claims_for_item(
    db: Session,
    supervisor: Supervisor,
    found_item_id: uuid.UUID,
) -> AuthorityClaimsComparisonResponse:
    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(Item.id == found_item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item or item.drop_point_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    supervisor_service.assert_drop_point_in_scope(supervisor, item.drop_point_id)

    claims = (
        db.query(Claim)
        .options(joinedload(Claim.claimant))
        .filter(Claim.found_item_id == found_item_id)
        .order_by(Claim.created_at.asc())
        .all()
    )
    return authority_claim_service._build_comparison(db, item, claims)

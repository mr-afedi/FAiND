"""
Authority dashboard — Section 17 (W7).

All queries and mutations are scoped to the authenticated authority's drop_point_id.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.authority import Authority
from app.models.drop_point import DropPoint
from app.models.item import Item, ItemStatus, ItemType
from app.schemas.authority import (
    AuthorityDashboardItem,
    AuthorityDashboardListResponse,
    AuthorityDropOffActionResponse,
    AuthorityDropPointSettingsResponse,
    AuthorityDropPointSettingsUpdate,
)
from app.services import drop_off_service

_INCOMING_STATUSES = (
    ItemStatus.FOUND,
    ItemStatus.OVERDUE,
)


def _build_dashboard_item(item: Item) -> AuthorityDashboardItem:
    drop_off = drop_off_service.build_drop_off_info(item)
    can_authority_confirm = (
        item.status in _INCOMING_STATUSES
        and not drop_off_service.is_dropoff_complete(item)
        and not item.authority_received_at
    )
    return AuthorityDashboardItem(
        id=item.id,
        status=item.status.value,
        category=item.category.value,
        public_description=item.public_description,
        location_label=item.location_label,
        image_urls=item.image_urls or [],
        date_occurred=item.date_occurred,
        created_at=item.created_at,
        tracking_reference=item.tracking_reference,
        dropoff_hours_remaining=drop_off.hours_remaining,
        dropoff_hours_until_unconfirmed=drop_off.hours_until_unconfirmed,
        dropoff_late=drop_off.dropoff_late,
        dropoff_phase=drop_off.dropoff_phase,
        finder_dropped_off_at=item.finder_dropped_off_at,
        authority_received_at=item.authority_received_at,
        dropoff_confirmed_at=item.dropoff_confirmed_at,
        can_authority_confirm=can_authority_confirm,
    )


def _get_found_item_for_authority(
    db: Session,
    authority: Authority,
    item_id: uuid.UUID,
) -> Item:
    item = (
        db.query(Item)
        .filter(Item.id == item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    if item.drop_point_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found.")
    if item.drop_point_id != authority.drop_point_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This item belongs to a different drop point.",
        )
    return item


def list_incoming_items(db: Session, authority: Authority) -> AuthorityDashboardListResponse:
    items = (
        db.query(Item)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id == authority.drop_point_id,
            Item.status.in_(_INCOMING_STATUSES),
        )
        .order_by(Item.created_at.asc())
        .all()
    )
    return AuthorityDashboardListResponse(
        items=[_build_dashboard_item(item) for item in items]
    )


def list_at_droppoint_items(db: Session, authority: Authority) -> AuthorityDashboardListResponse:
    items = (
        db.query(Item)
        .filter(
            Item.item_type == ItemType.FOUND,
            Item.drop_point_id == authority.drop_point_id,
            Item.status == ItemStatus.AT_DROPPOINT,
        )
        .order_by(Item.dropoff_confirmed_at.desc().nullslast(), Item.updated_at.desc())
        .all()
    )
    return AuthorityDashboardListResponse(
        items=[_build_dashboard_item(item) for item in items]
    )


def confirm_dropoff(
    db: Session,
    authority: Authority,
    item_id: uuid.UUID,
) -> AuthorityDropOffActionResponse:
    item = _get_found_item_for_authority(db, authority, item_id)
    message, _, _ = drop_off_service.authority_confirm_received_for_item(db, item)
    db.refresh(item)
    return AuthorityDropOffActionResponse(message=message, item=_build_dashboard_item(item))


def scan_qr(
    db: Session,
    authority: Authority,
    raw_token: str,
) -> AuthorityDropOffActionResponse:
    message, item, _ = drop_off_service.redeem_drop_off_qr_for_authority(
        db, authority, raw_token
    )
    db.refresh(item)
    return AuthorityDropOffActionResponse(message=message, item=_build_dashboard_item(item))


def get_drop_point_settings(authority: Authority) -> AuthorityDropPointSettingsResponse:
    point = authority.drop_point
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop point not found.")
    return AuthorityDropPointSettingsResponse(
        drop_point_id=point.id,
        drop_point_name=point.name,
        operating_hours=point.operating_hours,
        is_temporarily_closed=point.is_temporarily_closed,
        closed_reason=point.closed_reason,
    )


def update_drop_point_settings(
    db: Session,
    authority: Authority,
    payload: AuthorityDropPointSettingsUpdate,
) -> AuthorityDropPointSettingsResponse:
    point = (
        db.query(DropPoint)
        .filter(DropPoint.id == authority.drop_point_id)
        .first()
    )
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop point not found.")

    was_closed = point.is_temporarily_closed

    if payload.operating_hours is not None:
        hours = payload.operating_hours.strip()
        if not hours:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Operating hours cannot be empty.",
            )
        point.operating_hours = hours

    if payload.is_temporarily_closed is not None:
        point.is_temporarily_closed = payload.is_temporarily_closed
        if not payload.is_temporarily_closed:
            point.closed_reason = None

    if payload.closed_reason is not None:
        point.closed_reason = payload.closed_reason.strip() or None

    if point.is_temporarily_closed and not (point.closed_reason or "").strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A reason is required while temporarily closed.",
        )

    point.updated_at = datetime.now(timezone.utc)
    db.flush()
    authority.drop_point = point

    if point.is_temporarily_closed and not was_closed:
        from app.services import notification_service
        from app.services import authority_notification_service

        notification_service.notify_owners_drop_point_temporarily_closed(
            db, drop_point=point
        )
        authority_notification_service.notify_authority_drop_point_closed(
            db, drop_point=point
        )

    return get_drop_point_settings(authority)

"""Admin drop point CRUD — W15 Section 4."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.admin_log import AdminActionType
from app.models.drop_point import DropPoint
from app.models.university import University
from app.models.user import User
from app.schemas.admin_drop_point import (
    AdminDropPointListItem,
    CreateDropPointRequest,
    UpdateDropPointRequest,
)
from app.services.admin_dashboard_service import log_action


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _to_list_item(point: DropPoint, university_name: str) -> AdminDropPointListItem:
    return AdminDropPointListItem(
        id=point.id,
        university_id=point.university_id,
        university_name=university_name,
        name=point.name,
        type=point.type,
        latitude=point.latitude,
        longitude=point.longitude,
        operating_hours=point.operating_hours,
        is_temporarily_closed=point.is_temporarily_closed,
        closed_reason=point.closed_reason,
        created_at=point.created_at,
        updated_at=point.updated_at,
    )


def list_all_drop_points(db: Session) -> list[AdminDropPointListItem]:
    rows = (
        db.query(DropPoint, University.name)
        .join(University, DropPoint.university_id == University.id)
        .order_by(University.name, DropPoint.name)
        .all()
    )
    return [_to_list_item(point, uni_name) for point, uni_name in rows]


def create_drop_point(
    db: Session,
    admin: User,
    payload: CreateDropPointRequest,
) -> AdminDropPointListItem:
    university = db.query(University).filter(University.id == payload.university_id).first()
    if not university:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found.")

    existing = (
        db.query(DropPoint)
        .filter(
            DropPoint.university_id == payload.university_id,
            DropPoint.name == payload.name.strip(),
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A drop point with this name already exists for this university.",
        )

    point = DropPoint(
        university_id=payload.university_id,
        name=payload.name.strip(),
        type=payload.type,
        latitude=payload.latitude,
        longitude=payload.longitude,
        operating_hours=payload.operating_hours.strip(),
        is_temporarily_closed=payload.is_temporarily_closed,
        closed_reason=payload.closed_reason.strip() if payload.closed_reason else None,
    )
    db.add(point)
    db.flush()

    log_action(
        db,
        admin=admin,
        action=AdminActionType.DROP_POINT_CREATE,
        target_type="drop_point",
        target_id=point.id,
        detail={
            "name": point.name,
            "university_id": str(point.university_id),
            "type": point.type.value,
        },
    )
    return _to_list_item(point, university.name)


def update_drop_point(
    db: Session,
    admin: User,
    drop_point_id: uuid.UUID,
    payload: UpdateDropPointRequest,
) -> AdminDropPointListItem:
    point = (
        db.query(DropPoint)
        .options(joinedload(DropPoint.university))
        .filter(DropPoint.id == drop_point_id)
        .first()
    )
    if not point:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drop point not found.")

    was_closed = point.is_temporarily_closed
    changes: dict[str, dict] = {}
    if payload.name is not None and payload.name.strip() != point.name:
        dup = (
            db.query(DropPoint)
            .filter(
                DropPoint.university_id == point.university_id,
                DropPoint.name == payload.name.strip(),
                DropPoint.id != point.id,
            )
            .first()
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A drop point with this name already exists for this university.",
            )
        changes["name"] = {"from": point.name, "to": payload.name.strip()}
        point.name = payload.name.strip()

    for field in ("type", "latitude", "longitude", "operating_hours", "is_temporarily_closed", "closed_reason"):
        value = getattr(payload, field)
        if value is None:
            continue
        if field == "operating_hours":
            value = value.strip()
        if field == "closed_reason":
            value = value.strip() if value else None
        old = getattr(point, field)
        old_cmp = old.value if hasattr(old, "value") else old
        new_cmp = value.value if hasattr(value, "value") else value
        if old_cmp != new_cmp:
            changes[field] = {"from": old_cmp, "to": new_cmp}
            setattr(point, field, value)

    if not changes:
        uni_name = point.university.name if point.university else "Unknown"
        return _to_list_item(point, uni_name)

    point.updated_at = _now()
    db.flush()

    if point.is_temporarily_closed and not was_closed:
        from app.services import notification_service

        notification_service.notify_owners_drop_point_temporarily_closed(
            db, drop_point=point
        )

    log_action(
        db,
        admin=admin,
        action=AdminActionType.DROP_POINT_UPDATE,
        target_type="drop_point",
        target_id=point.id,
        detail=changes,
    )
    uni_name = point.university.name if point.university else "Unknown"
    return _to_list_item(point, uni_name)

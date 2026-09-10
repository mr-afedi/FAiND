"""
Supervisor authentication and administration — Section 5.4 / 15.2 (W14).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import create_access_token, hash_password, verify_password
from app.models.drop_point import DropPoint
from app.models.supervisor import Supervisor, supervisor_drop_points
from app.models.user import User
from app.models.admin_log import AdminActionType
from app.schemas.supervisor import (
    CreateSupervisorRequest,
    SupervisorDropPointSummary,
    SupervisorListItem,
    SupervisorProfileResponse,
    UpdateSupervisorRequest,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def get_supervisor_by_id(db: Session, supervisor_id: uuid.UUID) -> Supervisor | None:
    return (
        db.query(Supervisor)
        .options(joinedload(Supervisor.drop_points))
        .filter(Supervisor.id == supervisor_id)
        .first()
    )


def assigned_drop_point_ids(supervisor: Supervisor) -> set[uuid.UUID]:
    return {dp.id for dp in supervisor.drop_points}


def assert_drop_point_in_scope(
    supervisor: Supervisor,
    drop_point_id: uuid.UUID,
    *,
    resource_exists: bool = True,
) -> None:
    if not resource_exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    if drop_point_id not in assigned_drop_point_ids(supervisor):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )


def authenticate_supervisor(db: Session, email: str, password: str) -> Supervisor:
    normalized = email.strip().lower()
    supervisor = (
        db.query(Supervisor)
        .options(joinedload(Supervisor.drop_points))
        .filter(Supervisor.email == normalized)
        .first()
    )
    if not supervisor or not verify_password(password, supervisor.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not supervisor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This supervisor account has been deactivated.",
        )
    return supervisor


def login_supervisor(db: Session, email: str, password: str) -> str:
    supervisor = authenticate_supervisor(db, email, password)
    drop_point_ids = [str(dp.id) for dp in supervisor.drop_points]
    return create_access_token(
        {
            "sub": str(supervisor.id),
            "role": "supervisor",
            "university_id": str(supervisor.university_id),
            "drop_point_ids": drop_point_ids,
        }
    )


def build_supervisor_profile(supervisor: Supervisor) -> SupervisorProfileResponse:
    return SupervisorProfileResponse(
        id=supervisor.id,
        email=supervisor.email,
        university_id=supervisor.university_id,
        is_active=supervisor.is_active,
        created_at=supervisor.created_at,
        drop_points=[
            SupervisorDropPointSummary(
                id=dp.id,
                name=dp.name,
                type=dp.type.value,
                operating_hours=dp.operating_hours,
                is_temporarily_closed=dp.is_temporarily_closed,
            )
            for dp in supervisor.drop_points
        ],
    )


def _validate_drop_points(
    db: Session,
    university_id: uuid.UUID,
    drop_point_ids: list[uuid.UUID],
) -> list[DropPoint]:
    if not drop_point_ids:
        return []
    rows = (
        db.query(DropPoint)
        .filter(DropPoint.id.in_(drop_point_ids))
        .all()
    )
    found = {row.id for row in rows}
    missing = set(drop_point_ids) - found
    if missing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="One or more drop points were not found.",
        )
    for row in rows:
        if row.university_id != university_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="All drop points must belong to the supervisor's university.",
            )
    return rows


def _set_supervisor_drop_points(
    db: Session,
    supervisor: Supervisor,
    drop_points: list[DropPoint],
) -> None:
    db.execute(
        supervisor_drop_points.delete().where(
            supervisor_drop_points.c.supervisor_id == supervisor.id
        )
    )
    for dp in drop_points:
        db.execute(
            supervisor_drop_points.insert().values(
                supervisor_id=supervisor.id,
                drop_point_id=dp.id,
            )
        )
    db.flush()
    db.refresh(supervisor)


def create_supervisor(
    db: Session,
    payload: CreateSupervisorRequest,
    *,
    actor: User | None = None,
) -> SupervisorListItem:
    email = payload.email.strip().lower()
    if db.query(Supervisor).filter(Supervisor.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A supervisor with this email already exists.",
        )

    drop_points = _validate_drop_points(db, payload.university_id, payload.drop_point_ids)
    supervisor = Supervisor(
        email=email,
        hashed_password=hash_password(payload.password),
        university_id=payload.university_id,
        is_active=True,
    )
    db.add(supervisor)
    db.flush()
    _set_supervisor_drop_points(db, supervisor, drop_points)
    db.refresh(supervisor)

    if actor:
        from app.services.admin_dashboard_service import log_action

        log_action(
            db,
            admin=actor,
            action=AdminActionType.SUPERVISOR_CREATE,
            target_type="supervisor",
            target_id=supervisor.id,
            detail={
                "email": supervisor.email,
                "drop_point_ids": [str(dp.id) for dp in drop_points],
            },
        )

    from app.services import admin_notification_service

    admin_notification_service.notify_admins_supervisor_created(
        db,
        supervisor_id=supervisor.id,
        email=supervisor.email,
    )

    return _to_list_item(supervisor)


def update_supervisor(
    db: Session,
    supervisor_id: uuid.UUID,
    payload: UpdateSupervisorRequest,
    *,
    actor: User | None = None,
) -> SupervisorListItem:
    supervisor = get_supervisor_by_id(db, supervisor_id)
    if not supervisor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor not found.")

    changes: dict = {}
    if payload.is_active is not None and payload.is_active != supervisor.is_active:
        changes["is_active"] = {"from": supervisor.is_active, "to": payload.is_active}
        supervisor.is_active = payload.is_active
    if payload.password:
        changes["password_reset"] = True
        supervisor.hashed_password = hash_password(payload.password)
    if payload.drop_point_ids is not None:
        drop_points = _validate_drop_points(
            db, supervisor.university_id, payload.drop_point_ids
        )
        changes["drop_point_ids"] = {
            "from": [str(dp.id) for dp in supervisor.drop_points],
            "to": [str(dp.id) for dp in drop_points],
        }
        _set_supervisor_drop_points(db, supervisor, drop_points)

    supervisor.updated_at = _now()
    db.flush()
    db.refresh(supervisor)

    if actor and changes:
        from app.services.admin_dashboard_service import log_action

        log_action(
            db,
            admin=actor,
            action=AdminActionType.SUPERVISOR_UPDATE,
            target_type="supervisor",
            target_id=supervisor.id,
            detail={"email": supervisor.email, **changes},
        )

        from app.services import admin_notification_service

        admin_notification_service.notify_admins_supervisor_modified(
            db,
            supervisor_id=supervisor.id,
            email=supervisor.email,
        )

    return _to_list_item(supervisor)


def list_supervisors(db: Session) -> list[SupervisorListItem]:
    rows = (
        db.query(Supervisor)
        .options(joinedload(Supervisor.drop_points))
        .order_by(Supervisor.created_at.desc())
        .all()
    )
    return [_to_list_item(row) for row in rows]


def _to_list_item(supervisor: Supervisor) -> SupervisorListItem:
    return SupervisorListItem(
        id=supervisor.id,
        email=supervisor.email,
        university_id=supervisor.university_id,
        is_active=supervisor.is_active,
        created_at=supervisor.created_at,
        drop_point_ids=[dp.id for dp in supervisor.drop_points],
        drop_point_names=[dp.name for dp in supervisor.drop_points],
    )

"""
Supervisor in-app alerts — mirrors authority alerts (V5 Section 14).
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.supervisor import Supervisor, supervisor_drop_points
from app.models.supervisor_alert import SupervisorAlert, SupervisorAlertType

_DELETABLE_TYPES = frozenset({
    SupervisorAlertType.HANDOVER_COMPLETE,
    SupervisorAlertType.ITEM_REMOVED,
    SupervisorAlertType.DROP_POINT_CLOSED,
})


def is_alert_deletable(alert: SupervisorAlert) -> bool:
    return alert.alert_type in _DELETABLE_TYPES


def create_alert(
    db: Session,
    *,
    supervisor_id: uuid.UUID,
    alert_type: SupervisorAlertType,
    title: str,
    body: str,
    link: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> SupervisorAlert:
    row = SupervisorAlert(
        supervisor_id=supervisor_id,
        alert_type=alert_type,
        title=title,
        body=body,
        link=link,
        reference_id=reference_id,
    )
    db.add(row)
    db.flush()
    return row


def _supervisors_for_drop_point(db: Session, drop_point_id: uuid.UUID) -> list[Supervisor]:
    return (
        db.query(Supervisor)
        .join(supervisor_drop_points, Supervisor.id == supervisor_drop_points.c.supervisor_id)
        .filter(
            supervisor_drop_points.c.drop_point_id == drop_point_id,
            Supervisor.is_active.is_(True),
        )
        .all()
    )


def create_alerts_for_drop_point(
    db: Session,
    *,
    drop_point_id: uuid.UUID,
    alert_type: SupervisorAlertType,
    title: str,
    body: str,
    link: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> list[SupervisorAlert]:
    rows: list[SupervisorAlert] = []
    for supervisor in _supervisors_for_drop_point(db, drop_point_id):
        rows.append(
            create_alert(
                db,
                supervisor_id=supervisor.id,
                alert_type=alert_type,
                title=title,
                body=body,
                link=link,
                reference_id=reference_id,
            )
        )
    return rows


def list_alerts(
    db: Session,
    supervisor_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[SupervisorAlert]:
    return (
        db.query(SupervisorAlert)
        .filter(SupervisorAlert.supervisor_id == supervisor_id)
        .order_by(SupervisorAlert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_unread_count(db: Session, supervisor_id: uuid.UUID) -> int:
    return (
        db.query(SupervisorAlert)
        .filter(
            SupervisorAlert.supervisor_id == supervisor_id,
            SupervisorAlert.read.is_(False),
        )
        .count()
    )


def mark_read(db: Session, supervisor_id: uuid.UUID, alert_id: uuid.UUID) -> bool:
    row = (
        db.query(SupervisorAlert)
        .filter(SupervisorAlert.id == alert_id, SupervisorAlert.supervisor_id == supervisor_id)
        .first()
    )
    if not row:
        return False
    row.read = True
    db.flush()
    return True


def mark_all_read(db: Session, supervisor_id: uuid.UUID) -> int:
    rows = (
        db.query(SupervisorAlert)
        .filter(SupervisorAlert.supervisor_id == supervisor_id, SupervisorAlert.read.is_(False))
        .all()
    )
    for row in rows:
        row.read = True
    db.flush()
    return len(rows)


def delete_alert(db: Session, supervisor_id: uuid.UUID, alert_id: uuid.UUID) -> bool:
    row = (
        db.query(SupervisorAlert)
        .filter(SupervisorAlert.id == alert_id, SupervisorAlert.supervisor_id == supervisor_id)
        .first()
    )
    if not row:
        return False
    if not is_alert_deletable(row):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This alert cannot be deleted.",
        )
    db.delete(row)
    db.flush()
    return True


def delete_deletable_alerts(db: Session, supervisor_id: uuid.UUID) -> int:
    rows = (
        db.query(SupervisorAlert)
        .filter(SupervisorAlert.supervisor_id == supervisor_id)
        .all()
    )
    deleted = 0
    for row in rows:
        if is_alert_deletable(row):
            db.delete(row)
            deleted += 1
    db.flush()
    return deleted

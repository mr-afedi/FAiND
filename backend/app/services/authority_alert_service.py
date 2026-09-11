"""
Authority in-app alerts — Section 14.1 / 17 (deletion rules mirror user notifications).
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.authority import Authority
from app.models.authority_alert import AuthorityAlert, AuthorityAlertType

_DELETABLE_TYPES = frozenset({
    AuthorityAlertType.HANDOVER_COMPLETE,
    AuthorityAlertType.ITEM_REMOVED,
    AuthorityAlertType.DROP_POINT_CLOSED,
})


def is_alert_deletable(alert: AuthorityAlert) -> bool:
    return alert.alert_type in _DELETABLE_TYPES


def create_alert(
    db: Session,
    *,
    authority_id: uuid.UUID,
    alert_type: AuthorityAlertType,
    title: str,
    body: str,
    link: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> AuthorityAlert:
    row = AuthorityAlert(
        authority_id=authority_id,
        alert_type=alert_type,
        title=title,
        body=body,
        link=link,
        reference_id=reference_id,
    )
    db.add(row)
    db.flush()
    return row


def create_alert_for_drop_point(
    db: Session,
    *,
    drop_point_id: uuid.UUID,
    alert_type: AuthorityAlertType,
    title: str,
    body: str,
    link: str | None = None,
    reference_id: uuid.UUID | None = None,
) -> AuthorityAlert | None:
    authority = (
        db.query(Authority)
        .filter(Authority.drop_point_id == drop_point_id, Authority.is_active.is_(True))
        .first()
    )
    if not authority:
        return None
    return create_alert(
        db,
        authority_id=authority.id,
        alert_type=alert_type,
        title=title,
        body=body,
        link=link,
        reference_id=reference_id,
    )


def get_unread_count(db: Session, authority_id: uuid.UUID) -> int:
    return (
        db.query(AuthorityAlert)
        .filter(AuthorityAlert.authority_id == authority_id, AuthorityAlert.read.is_(False))
        .count()
    )


def list_alerts(
    db: Session,
    authority_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[AuthorityAlert]:
    return (
        db.query(AuthorityAlert)
        .filter(AuthorityAlert.authority_id == authority_id)
        .order_by(AuthorityAlert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def mark_read(db: Session, authority_id: uuid.UUID, alert_id: uuid.UUID) -> bool:
    row = (
        db.query(AuthorityAlert)
        .filter(AuthorityAlert.id == alert_id, AuthorityAlert.authority_id == authority_id)
        .first()
    )
    if not row:
        return False
    row.read = True
    db.flush()
    return True


def mark_all_read(db: Session, authority_id: uuid.UUID) -> int:
    rows = (
        db.query(AuthorityAlert)
        .filter(AuthorityAlert.authority_id == authority_id, AuthorityAlert.read.is_(False))
        .all()
    )
    for row in rows:
        row.read = True
    db.flush()
    return len(rows)


def delete_alert(db: Session, authority_id: uuid.UUID, alert_id: uuid.UUID) -> bool:
    row = (
        db.query(AuthorityAlert)
        .filter(AuthorityAlert.id == alert_id, AuthorityAlert.authority_id == authority_id)
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


def delete_deletable_alerts(db: Session, authority_id: uuid.UUID) -> int:
    rows = (
        db.query(AuthorityAlert)
        .filter(AuthorityAlert.authority_id == authority_id)
        .all()
    )
    deleted = 0
    for row in rows:
        if is_alert_deletable(row):
            db.delete(row)
            deleted += 1
    if deleted:
        db.flush()
    return deleted

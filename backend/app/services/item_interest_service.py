"""
Item interest — "Notify Me When Dropped Off" before drop-off (V5).
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.item import Item, ItemStatus, ItemType
from app.models.item_interest import ItemInterest
from app.models.user import User
from app.schemas.item_interest import ItemInterestRegisterResponse, ItemInterestStatusResponse

_INTERESTABLE_STATUSES = frozenset({ItemStatus.FOUND, ItemStatus.OVERDUE})


def _get_found_item(db: Session, found_item_id: uuid.UUID) -> Item:
    item = (
        db.query(Item)
        .options(joinedload(Item.drop_point))
        .filter(Item.id == found_item_id, Item.item_type == ItemType.FOUND)
        .first()
    )
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Found item not found.")
    return item


def get_interest_status(
    db: Session,
    user: User | None,
    found_item_id: uuid.UUID,
) -> ItemInterestStatusResponse:
    item = _get_found_item(db, found_item_id)
    drop_point = item.drop_point
    registered = False
    if user:
        registered = (
            db.query(ItemInterest)
            .filter(
                ItemInterest.found_item_id == found_item_id,
                ItemInterest.user_id == user.id,
            )
            .first()
            is not None
        )
    can_register = (
        user is not None
        and item.status in _INTERESTABLE_STATUSES
        and not registered
    )
    can_claim = item.status not in _INTERESTABLE_STATUSES and item.status in {
        ItemStatus.AT_DROPPOINT,
        ItemStatus.UNDER_CLAIM_REVIEW,
        ItemStatus.FOUND,
        ItemStatus.OVERDUE,
    }
    return ItemInterestStatusResponse(
        found_item_id=item.id,
        item_status=item.status.value,
        drop_point_name=drop_point.name if drop_point else None,
        operating_hours=drop_point.operating_hours if drop_point else None,
        registered=registered,
        can_register=can_register,
        requires_interest_flow=item.status in _INTERESTABLE_STATUSES,
        can_claim_now=item.status in {ItemStatus.AT_DROPPOINT, ItemStatus.UNDER_CLAIM_REVIEW},
    )


def register_interest(
    db: Session,
    user: User,
    found_item_id: uuid.UUID,
) -> ItemInterestRegisterResponse:
    item = _get_found_item(db, found_item_id)
    if item.status not in _INTERESTABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This item is already at the drop point or no longer accepting interest.",
        )
    existing = (
        db.query(ItemInterest)
        .filter(
            ItemInterest.found_item_id == found_item_id,
            ItemInterest.user_id == user.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already registered for notifications on this item.",
        )
    interest = ItemInterest(user_id=user.id, found_item_id=found_item_id)
    db.add(interest)
    db.flush()
    drop_point = item.drop_point
    dp_name = drop_point.name if drop_point else "the drop point"
    return ItemInterestRegisterResponse(
        message=(
            f"We will notify you the moment this item arrives at {dp_name} "
            "so you can submit your claim."
        ),
        drop_point_name=dp_name,
        operating_hours=drop_point.operating_hours if drop_point else None,
    )


def list_interested_user_ids(db: Session, found_item_id: uuid.UUID) -> list[uuid.UUID]:
    rows = (
        db.query(ItemInterest.user_id)
        .filter(ItemInterest.found_item_id == found_item_id)
        .all()
    )
    return [row[0] for row in rows]

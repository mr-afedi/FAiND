"""
Item route handlers — Features C & D (Lost & Found Item Reporting).
Rate limiting: 10 item posts / user / day enforced in service layer.
IDOR checks: enforced in service layer for every owner-scoped action.
"""
import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user, get_optional_user
from app.models.user import User
from app.models.item import ItemType, ItemCategory, ItemStatus
from app.models.campus_zone import CampusZone
from app.schemas.item import (
    CheckHiddenAnswersRequest,
    CheckHiddenAnswersResponse,
    CreateLostItemRequest,
    UpdateLostItemRequest,
    LostItemPublicResponse,
    LostItemOwnerResponse,
    LostItemListResponse,
    CampusZoneOption,
    CreateFoundItemRequest,
    UpdateFoundItemRequest,
    FoundItemListResponse,
    BrowseListResponse,
    HomepageResponse,
)
import app.services.item_service as item_service
from app.services.matching_service import run_matching_background, get_matched_item_ids

router = APIRouter(prefix="/items", tags=["items"])


# ── Campus Zones ─────────────────────────────────────────────────────────────

@router.get("/campus-zones", response_model=list[CampusZoneOption])
def get_campus_zones(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return active campus zones scoped to the authenticated user's university."""
    zones = (
        db.query(CampusZone)
        .filter(
            CampusZone.university_id == current_user.university_id,
            CampusZone.is_active == True,
        )
        .order_by(CampusZone.name)
        .all()
    )
    return zones


@router.get("/public/campus-zones", response_model=list[CampusZoneOption])
def get_public_campus_zones(db: Session = Depends(get_db)):
    """Return all active campus zones — no auth required (used by public browse filter)."""
    return (
        db.query(CampusZone)
        .filter(CampusZone.is_active == True)
        .order_by(CampusZone.name)
        .all()
    )


# ── Public Browse (Feature F) — defined BEFORE /{item_id} to avoid shadowing ─

@router.get("/public/homepage", response_model=HomepageResponse)
def get_homepage_data(
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    No auth required. Returns 5 latest lost, 5 latest found, and recently
    returned items for the homepage (Section 24.1).
    Authenticated users see POTENTIAL_MATCH status on items they are a party to.
    """
    matched_ids = get_matched_item_ids(db, current_user.id) if current_user else None
    viewer_id = current_user.id if current_user else None
    return item_service.get_homepage_data(db, viewer_matched_ids=matched_ids, viewer_id=viewer_id)


@router.get("/public", response_model=BrowseListResponse)
def browse_public(
    item_type: Optional[str]        = Query(default=None),
    category:  Optional[List[str]]  = Query(default=None),
    location_id: Optional[uuid.UUID]= Query(default=None),
    date_from: Optional[datetime]   = Query(default=None),
    date_to:   Optional[datetime]   = Query(default=None),
    item_status: Optional[List[str]]= Query(default=None, alias="status"),
    q:         Optional[str]        = Query(default=None),
    sort:      str                  = Query(default="newest", pattern="^(newest|oldest|activity)$"),
    skip:      int                  = Query(default=0, ge=0),
    limit:     int                  = Query(default=20, ge=1, le=50),
    current_user: Optional[User]    = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """
    No auth required. Public filterable browse for /lost and /found pages
    (Section 24.2). Suspended users' posts are always excluded.
    Authenticated users see POTENTIAL_MATCH status on items they are a party to.
    """
    parsed_type     = ItemType(item_type) if item_type else None
    parsed_cats     = [ItemCategory(c) for c in category]    if category     else None
    parsed_statuses = [ItemStatus(s)    for s in item_status] if item_status else None
    matched_ids     = get_matched_item_ids(db, current_user.id) if current_user else None
    viewer_id       = current_user.id if current_user else None

    return item_service.browse_items(
        db,
        item_type=parsed_type,
        categories=parsed_cats,
        location_id=location_id,
        date_from=date_from,
        date_to=date_to,
        statuses=parsed_statuses,
        q=q,
        sort=sort,
        skip=skip,
        limit=limit,
        viewer_matched_ids=matched_ids,
        viewer_id=viewer_id,
    )


# ── Lost Item CRUD ────────────────────────────────────────────────────────────

@router.post("/lost/check-hidden-answers", response_model=CheckHiddenAnswersResponse)
def check_lost_hidden_answers(
    payload: CheckHiddenAnswersRequest,
    current_user: User = Depends(get_current_user),
):
    """Warn when hidden answers are too similar to the public description (V4.3)."""
    return CheckHiddenAnswersResponse(warnings=item_service.check_hidden_answers(payload))


@router.post("/lost", response_model=LostItemOwnerResponse, status_code=status.HTTP_201_CREATED)
def create_lost_item(
    payload: CreateLostItemRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = item_service.create_lost_item(db, current_user, payload)
        background_tasks.add_task(run_matching_background, result.id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/my/lost", response_model=LostItemListResponse)
def list_my_lost_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return item_service.list_my_lost_items(db, current_user, skip=skip, limit=limit)


@router.get("/{item_id}", response_model=LostItemPublicResponse | LostItemOwnerResponse)
def get_item(
    item_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    try:
        return item_service.get_item_detail(db, item_id, current_user)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")


@router.patch("/{item_id}", response_model=LostItemOwnerResponse)
def update_item(
    item_id: uuid.UUID,
    payload: UpdateLostItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return item_service.update_lost_item(db, item_id, current_user, payload)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        item_service.delete_lost_item(db, item_id, current_user)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/{item_id}/extend", response_model=LostItemOwnerResponse)
def extend_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return item_service.extend_lost_item(db, item_id, current_user)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


# ── Found Item CRUD (Feature D) ───────────────────────────────────────────────

@router.post("/found", response_model=LostItemPublicResponse, status_code=status.HTTP_201_CREATED)
def create_found_item(
    payload: CreateFoundItemRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = item_service.create_found_item(db, current_user, payload)
        background_tasks.add_task(run_matching_background, result.id)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/my/found", response_model=FoundItemListResponse)
def list_my_found_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return item_service.list_my_found_items(db, current_user, skip=skip, limit=limit)


@router.patch("/found/{item_id}", response_model=LostItemPublicResponse)
def update_found_item(
    item_id: uuid.UUID,
    payload: UpdateFoundItemRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return item_service.update_found_item(db, item_id, current_user, payload)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.delete("/found/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_found_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        item_service.delete_found_item(db, item_id, current_user)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.post("/found/{item_id}/extend", response_model=LostItemPublicResponse)
def extend_found_item(
    item_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return item_service.extend_found_item(db, item_id, current_user)
    except LookupError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

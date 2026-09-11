"""
Drop point lookup endpoints (Section 4).
Public — used by the found-item form and browse flows.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_optional_user
from app.models.user import User
from app.schemas.drop_point import (
    DropPointListResponse,
    DropPointResponse,
    NearestDropPointResponse,
)
from app.services import drop_point_service

router = APIRouter(prefix="/drop-points", tags=["drop-points"])


def _resolve_university_id(
    current_user: User | None,
    university_id: uuid.UUID | None,
) -> uuid.UUID:
    if current_user is not None:
        return current_user.university_id
    if university_id is not None:
        return university_id
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="university_id is required when not authenticated.",
    )


@router.get("", response_model=DropPointListResponse)
def list_drop_points(
    university_id: uuid.UUID | None = Query(None, description="Required for guests"),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    uid = _resolve_university_id(current_user, university_id)
    points = drop_point_service.get_all_drop_points(db, uid)
    return DropPointListResponse(
        drop_points=[DropPointResponse.model_validate(p) for p in points],
    )


@router.get("/nearest", response_model=NearestDropPointResponse)
def nearest_drop_point(
    lat: float = Query(..., ge=-90, le=90, description="Campus zone latitude"),
    lng: float = Query(..., ge=-180, le=180, description="Campus zone longitude"),
    university_id: uuid.UUID | None = Query(None, description="Required for guests"),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    uid = _resolve_university_id(current_user, university_id)
    try:
        result = drop_point_service.get_nearest_drop_point(db, lat, lng, uid)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return NearestDropPointResponse.model_validate(result)

"""Drop point lookup and nearest-point suggestion (Section 4.2)."""
from __future__ import annotations

import uuid

from geopy.distance import geodesic
from sqlalchemy.orm import Session

from app.models.drop_point import DropPoint


def _distance_km(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> float:
    try:
        metres = geodesic((lat_a, lng_a), (lat_b, lng_b)).meters
    except Exception:
        return 0.0
    return round(metres / 1000, 3)


def _serialize_with_distance(point: DropPoint, distance_km: float) -> dict:
    return {
        "id": point.id,
        "university_id": point.university_id,
        "name": point.name,
        "type": point.type,
        "latitude": point.latitude,
        "longitude": point.longitude,
        "operating_hours": point.operating_hours,
        "is_temporarily_closed": point.is_temporarily_closed,
        "closed_reason": point.closed_reason,
        "distance_km": distance_km,
    }


def get_all_drop_points(db: Session, university_id: uuid.UUID) -> list[DropPoint]:
    return (
        db.query(DropPoint)
        .filter(DropPoint.university_id == university_id)
        .order_by(DropPoint.name)
        .all()
    )


def get_nearest_drop_point(
    db: Session,
    campus_zone_lat: float,
    campus_zone_lng: float,
    university_id: uuid.UUID,
) -> dict:
    points = get_all_drop_points(db, university_id)
    if not points:
        raise LookupError("No drop points configured for this university.")

    ranked = sorted(
        points,
        key=lambda p: _distance_km(campus_zone_lat, campus_zone_lng, p.latitude, p.longitude),
    )
    with_distances = [
        _serialize_with_distance(
            p,
            _distance_km(campus_zone_lat, campus_zone_lng, p.latitude, p.longitude),
        )
        for p in ranked
    ]
    return {
        "nearest": with_distances[0],
        "alternatives": with_distances,
    }

"""Campus location resolution shared by item and verification services."""
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.campus_zone import CampusZone


def _resolve_location(
    db: Session, location_id: Optional[uuid.UUID], university_id: uuid.UUID
) -> tuple[str, Optional[float], Optional[float], Optional[uuid.UUID]]:
    """Return (label, lat, lng, zone_id) for the chosen zone, or raise ValueError."""
    if location_id is None:
        return ("Unknown Location", None, None, None)

    zone: Optional[CampusZone] = (
        db.query(CampusZone)
        .filter(
            CampusZone.id == location_id,
            CampusZone.university_id == university_id,
            CampusZone.is_active == True,
        )
        .first()
    )
    if not zone:
        raise ValueError("Campus zone not found or does not belong to your university")
    return (zone.name, zone.latitude, zone.longitude, zone.id)

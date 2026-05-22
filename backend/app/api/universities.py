"""
Public university and campus zone lookup endpoints.
No auth required — used by the frontend to populate location dropdowns.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.core.database import get_db
from app.models.university import University
from app.models.campus_zone import CampusZone
from app.schemas.university import UniversityResponse, CampusZoneResponse

router = APIRouter(prefix="/universities", tags=["universities"])


@router.get("/", response_model=List[UniversityResponse])
def list_universities(db: Session = Depends(get_db)):
    return db.query(University).filter(University.is_active == True).all()


@router.get("/{university_id}/zones", response_model=List[CampusZoneResponse])
def list_campus_zones(university_id: uuid.UUID, db: Session = Depends(get_db)):
    univ = db.query(University).filter(
        University.id == university_id, University.is_active == True
    ).first()
    if not univ:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found.")
    return db.query(CampusZone).filter(
        CampusZone.university_id == university_id,
        CampusZone.is_active == True,
    ).order_by(CampusZone.name).all()

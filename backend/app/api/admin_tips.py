"""Admin tipping API — amounts visible to admins only (Section 20.2)."""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin_access
from app.models.user import User
from app.schemas.tipping import AdminTipDetail
from app.services import tipping_service

router = APIRouter(prefix="/admin/tips", tags=["admin-tips"])


@router.get("/returns/{return_id}", response_model=AdminTipDetail)
def get_return_tip(
    return_id: uuid.UUID,
    _admin: User = Depends(require_admin_access),
    db: Session = Depends(get_db),
):
    tip = tipping_service.admin_get_tip_for_return(db, return_id)
    return AdminTipDetail.model_validate(tipping_service.admin_tip_detail(db, tip))

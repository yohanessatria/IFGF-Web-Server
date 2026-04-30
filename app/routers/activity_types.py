from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import ActivityType
from app.schemas.schemas import ActivityTypeOut

router = APIRouter(prefix="/api/activity-types", tags=["Activity Types"])


@router.get("", response_model=List[ActivityTypeOut])
def list_activity_types(db: Session = Depends(get_db), _=Depends(require_active_user)):
    return db.query(ActivityType).filter(ActivityType.is_active == True).all()


@router.get("/{type_id}", response_model=ActivityTypeOut)
def get_activity_type(type_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    record = db.get(ActivityType, type_id)
    if not record:
        raise HTTPException(status_code=404, detail="Activity type not found")
    return record

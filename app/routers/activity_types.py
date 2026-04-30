from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import ActivityType
from app.schemas.schemas import ActivityTypeCreate, ActivityTypeUpdate, ActivityTypeOut

router = APIRouter(prefix="/api/activity-types", tags=["Activity Types"])


@router.get("", response_model=List[ActivityTypeOut])
def list_activity_types(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = db.query(ActivityType)
    if not include_inactive:
        q = q.filter(ActivityType.is_active == True)
    return q.order_by(ActivityType.name).all()


@router.post("", response_model=ActivityTypeOut, status_code=201)
def create_activity_type(
    payload: ActivityTypeCreate,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    if db.query(ActivityType).filter(ActivityType.name == payload.name).first():
        raise HTTPException(status_code=409, detail="Activity type with this name already exists")
    record = ActivityType(name=payload.name, description=payload.description, is_active=payload.is_active)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{type_id}", response_model=ActivityTypeOut)
def get_activity_type(type_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    record = db.get(ActivityType, type_id)
    if not record:
        raise HTTPException(status_code=404, detail="Activity type not found")
    return record


@router.patch("/{type_id}", response_model=ActivityTypeOut)
def update_activity_type(
    type_id: int,
    payload: ActivityTypeUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    record = db.get(ActivityType, type_id)
    if not record:
        raise HTTPException(status_code=404, detail="Activity type not found")
    if payload.name is not None and payload.name != record.name:
        if db.query(ActivityType).filter(ActivityType.name == payload.name).first():
            raise HTTPException(status_code=409, detail="Activity type with this name already exists")
        record.name = payload.name
    if payload.description is not None:
        record.description = payload.description
    if payload.is_active is not None:
        record.is_active = payload.is_active
    db.commit()
    db.refresh(record)
    return record


@router.delete("/{type_id}", status_code=204)
def delete_activity_type(type_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    record = db.get(ActivityType, type_id)
    if not record:
        raise HTTPException(status_code=404, detail="Activity type not found")
    db.delete(record)
    db.commit()

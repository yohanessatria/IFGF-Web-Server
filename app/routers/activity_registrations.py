from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import ActivityRegistration, ActivitySession, Member
from app.schemas.schemas import (
    ActivityRegistrationCreate,
    ActivityRegistrationUpdate,
    ActivityRegistrationOut,
)

router = APIRouter(prefix="/api/activity-registrations", tags=["Activity Registrations"])


@router.get("", response_model=List[ActivityRegistrationOut])
def list_registrations(
    session_id: Optional[int] = None,
    member_id: Optional[int] = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = db.query(ActivityRegistration)
    if session_id:
        q = q.filter(ActivityRegistration.session_id == session_id)
    if member_id:
        q = q.filter(ActivityRegistration.member_id == member_id)
    return q.order_by(ActivityRegistration.registered_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=ActivityRegistrationOut, status_code=201)
def create_registration(
    payload: ActivityRegistrationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    if not db.get(ActivitySession, payload.session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    if not db.get(Member, payload.member_id):
        raise HTTPException(status_code=404, detail="Member not found")

    reg = ActivityRegistration(
        session_id=payload.session_id,
        member_id=payload.member_id,
        notes=payload.notes,
        created_by=current_user.id,
    )
    if payload.registered_at:
        reg.registered_at = payload.registered_at

    db.add(reg)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Member is already registered for this session")
    db.refresh(reg)
    return reg


@router.get("/{registration_id}", response_model=ActivityRegistrationOut)
def get_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    reg = db.get(ActivityRegistration, registration_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    return reg


@router.patch("/{registration_id}", response_model=ActivityRegistrationOut)
def update_registration(
    registration_id: int,
    payload: ActivityRegistrationUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    reg = db.get(ActivityRegistration, registration_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reg, field, value)

    db.commit()
    db.refresh(reg)
    return reg


@router.delete("/{registration_id}", status_code=204)
def delete_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    reg = db.get(ActivityRegistration, registration_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    db.delete(reg)
    db.commit()

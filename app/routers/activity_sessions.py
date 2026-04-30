from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import ActivitySession, ActivityType
from app.schemas.schemas import ActivitySessionCreate, ActivitySessionUpdate, ActivitySessionOut

router = APIRouter(prefix="/api/activity-sessions", tags=["Activity Sessions"])


@router.get("", response_model=List[ActivitySessionOut])
def list_sessions(
    activity_type_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = db.query(ActivitySession)
    if activity_type_id:
        q = q.filter(ActivitySession.activity_type_id == activity_type_id)
    if date_from:
        q = q.filter(ActivitySession.session_date >= date_from)
    if date_to:
        q = q.filter(ActivitySession.session_date <= date_to)
    return q.order_by(ActivitySession.session_date.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=ActivitySessionOut, status_code=201)
def create_session(
    payload: ActivitySessionCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    activity = db.get(ActivityType, payload.activity_type_id)
    if not activity or not activity.is_active:
        raise HTTPException(status_code=404, detail="Activity type not found or inactive")

    session = ActivitySession(
        activity_type_id=payload.activity_type_id,
        session_date=payload.session_date,
        expected_count=payload.expected_count,
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(session)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Session already exists for this activity on that date")
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=ActivitySessionOut)
def get_session(session_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    session = db.get(ActivitySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/{session_id}", response_model=ActivitySessionOut)
def update_session(
    session_id: int,
    payload: ActivitySessionUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    session = db.get(ActivitySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(session, field, value)

    db.commit()
    db.refresh(session)
    return session


@router.delete("/{session_id}", status_code=204)
def delete_session(session_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    session = db.get(ActivitySession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()

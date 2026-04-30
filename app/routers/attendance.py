from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, text, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import Attendance, Member, ActivityType
from app.schemas.schemas import AttendanceCheckIn, AttendanceOut, AttendanceWithMember

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


@router.post("/checkin", response_model=AttendanceOut, status_code=201)
def check_in(
    payload: AttendanceCheckIn,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    """Record attendance for a member. Prevents duplicate on the same day+activity."""
    member = db.get(Member, payload.member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    activity = db.get(ActivityType, payload.activity_type_id)
    if not activity or not activity.is_active:
        raise HTTPException(status_code=404, detail="Activity type not found or inactive")

    ts = payload.timestamp or datetime.utcnow()
    check_date = ts.date()

    # Check duplicate
    existing = db.query(Attendance).filter(
        Attendance.member_id == payload.member_id,
        Attendance.activity_type_id == payload.activity_type_id,
        func.date(Attendance.timestamp) == check_date,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Attendance already recorded for this session")

    record = Attendance(
        member_id=payload.member_id,
        activity_type_id=payload.activity_type_id,
        timestamp=ts,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=List[AttendanceWithMember])
def list_attendance(
    activity_type_id: Optional[int] = None,
    member_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = (
        db.query(
            Attendance.id,
            Attendance.member_id,
            Attendance.activity_type_id,
            Attendance.timestamp,
            Member.full_name.label("member_name"),
            Member.nickname.label("member_nickname"),
            ActivityType.name.label("activity_name"),
        )
        .join(Member, Attendance.member_id == Member.id)
        .join(ActivityType, Attendance.activity_type_id == ActivityType.id)
    )
    if activity_type_id:
        q = q.filter(Attendance.activity_type_id == activity_type_id)
    if member_id:
        q = q.filter(Attendance.member_id == member_id)
    if date_from:
        q = q.filter(func.date(Attendance.timestamp) >= date_from)
    if date_to:
        q = q.filter(func.date(Attendance.timestamp) <= date_to)

    rows = q.order_by(Attendance.timestamp.desc()).offset(skip).limit(limit).all()
    return [AttendanceWithMember(**row._mapping) for row in rows]


@router.get("/session/{activity_type_id}/{session_date}", response_model=List[AttendanceWithMember])
def get_session_attendance(
    activity_type_id: int,
    session_date: date,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    """Get all attendees for a specific activity on a specific date."""
    rows = (
        db.query(
            Attendance.id,
            Attendance.member_id,
            Attendance.activity_type_id,
            Attendance.timestamp,
            Member.full_name.label("member_name"),
            Member.nickname.label("member_nickname"),
            ActivityType.name.label("activity_name"),
        )
        .join(Member, Attendance.member_id == Member.id)
        .join(ActivityType, Attendance.activity_type_id == ActivityType.id)
        .filter(
            Attendance.activity_type_id == activity_type_id,
            func.date(Attendance.timestamp) == session_date,
        )
        .order_by(Attendance.timestamp)
        .all()
    )
    return [AttendanceWithMember(**row._mapping) for row in rows]


@router.delete("/{attendance_id}", status_code=204)
def delete_attendance(attendance_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    record = db.get(Attendance, attendance_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    db.delete(record)
    db.commit()

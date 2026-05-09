from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    require_active_user,
    is_super_admin,
    get_user_role_names,
    ROLE_ICARE_LEADER,
)
from app.models.church import (
    IcareGroup, IcareMember, Member,
    ActivityType, ActivitySession, ActivityRegistration, Attendance,
)
from app.schemas.schemas import (
    IcareGroupCreate, IcareGroupUpdate, IcareGroupOut,
    IcareMemberCreate, IcareMemberOut,
    IcareSessionBulkCreate, IcareSessionBulkOut,
    IcareAttendanceBulkCreate, IcareAttendanceBulkOut,
)
from datetime import date, datetime, time
from sqlalchemy import func

router = APIRouter(prefix="/api/icare", tags=["iCare Groups"])


def _activity_type_name(icare_name: str) -> str:
    return icare_name


# ── Groups ────────────────────────────────────────────────────────────────────

@router.get("/groups", response_model=List[IcareGroupOut])
def list_groups(db: Session = Depends(get_db), _=Depends(require_active_user)):
    return db.query(IcareGroup).order_by(IcareGroup.name).all()


@router.get("/groups/mine", response_model=List[IcareGroupOut])
def list_my_groups(
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """iCare groups led by the current user (active only)."""
    if current_user.member_id is None:
        return []
    return (
        db.query(IcareGroup)
        .filter(
            IcareGroup.leader_id == current_user.member_id,
            IcareGroup.is_active == True,  # noqa: E712
        )
        .order_by(IcareGroup.name)
        .all()
    )


@router.post("/groups", response_model=IcareGroupOut, status_code=201)
def create_group(
    payload: IcareGroupCreate,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    type_name = _activity_type_name(payload.name)
    if db.query(ActivityType).filter(ActivityType.name == type_name).first():
        raise HTTPException(
            status_code=409,
            detail=f"Activity type '{type_name}' already exists; choose a different iCare name",
        )

    activity = ActivityType(name=type_name, description="Auto-created for iCare group", is_active=True)
    db.add(activity)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Failed to create linked activity type")

    group = IcareGroup(**payload.model_dump(), activity_type_id=activity.id)
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="iCare group with this name already exists")
    db.refresh(group)
    return group


@router.get("/groups/{group_id}", response_model=IcareGroupOut)
def get_group(group_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    group = db.get(IcareGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="iCare group not found")
    return group


@router.patch("/groups/{group_id}", response_model=IcareGroupOut)
def update_group(
    group_id: int,
    payload: IcareGroupUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    group = db.get(IcareGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="iCare group not found")

    data = payload.model_dump(exclude_unset=True)
    new_name = data.get("name")

    if new_name is not None and new_name != group.name and group.activity_type_id is not None:
        new_type_name = _activity_type_name(new_name)
        clash = (
            db.query(ActivityType)
            .filter(ActivityType.name == new_type_name, ActivityType.id != group.activity_type_id)
            .first()
        )
        if clash:
            raise HTTPException(
                status_code=409,
                detail=f"Activity type '{new_type_name}' already exists; choose a different iCare name",
            )
        activity = db.get(ActivityType, group.activity_type_id)
        if activity:
            activity.name = new_type_name

    for field, value in data.items():
        setattr(group, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="iCare group with this name already exists")
    db.refresh(group)
    return group


@router.delete("/groups/{group_id}", status_code=204)
def delete_group(group_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    group = db.get(IcareGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="iCare group not found")
    db.delete(group)
    db.commit()


# ── Members in a group ────────────────────────────────────────────────────────

@router.get("/groups/{group_id}/members", response_model=List[IcareMemberOut])
def list_group_members(group_id: int, active_only: bool = True, db: Session = Depends(get_db), _=Depends(require_active_user)):
    q = db.query(IcareMember).filter(IcareMember.icare_id == group_id)
    if active_only:
        q = q.filter(IcareMember.is_active == True)
    return q.all()


@router.post("/members", response_model=IcareMemberOut, status_code=201)
def add_member_to_group(payload: IcareMemberCreate, db: Session = Depends(get_db), _=Depends(require_active_user)):
    if not db.get(IcareGroup, payload.icare_id):
        raise HTTPException(status_code=404, detail="iCare group not found")
    if not db.get(Member, payload.member_id):
        raise HTTPException(status_code=404, detail="Member not found")

    record = IcareMember(
        icare_id=payload.icare_id,
        member_id=payload.member_id,
        joined_date=payload.joined_date or date.today(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/members/{record_id}/leave", response_model=IcareMemberOut)
def remove_member_from_group(record_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    record = db.get(IcareMember, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="iCare membership record not found")
    record.is_active = False
    record.left_date = date.today()
    db.commit()
    db.refresh(record)
    return record


# ── Sessions for an iCare (auto-creates session + registrations) ──────────────

@router.post("/groups/{group_id}/sessions", response_model=IcareSessionBulkOut, status_code=201)
def create_icare_session(
    group_id: int,
    payload: IcareSessionBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Create an activity_session for the iCare on `session_date` and register
    the listed members in one transaction. expected_count = len(member_ids).
    Caller must be super_admin or the iCare's leader."""
    group = db.get(IcareGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="iCare group not found")
    if group.activity_type_id is None:
        raise HTTPException(status_code=400, detail="iCare has no linked activity type")

    roles = get_user_role_names(current_user, db)
    is_admin = "super_admin" in roles
    is_leader_of_group = (
        ROLE_ICARE_LEADER in roles and current_user.member_id == group.leader_id
    )
    if not (is_admin or is_leader_of_group):
        raise HTTPException(status_code=403, detail="Not permitted for this iCare")

    if not payload.member_ids:
        raise HTTPException(status_code=400, detail="At least one member must be selected")

    member_ids = list(dict.fromkeys(payload.member_ids))  # preserve order, dedupe

    valid_member_ids = {
        mid for (mid,) in (
            db.query(IcareMember.member_id)
            .filter(
                IcareMember.icare_id == group_id,
                IcareMember.member_id.in_(member_ids),
                IcareMember.is_active == True,  # noqa: E712
            )
            .all()
        )
    }
    invalid = [mid for mid in member_ids if mid not in valid_member_ids]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Some member_ids are not active members of this iCare", "invalid": invalid},
        )

    session = ActivitySession(
        activity_type_id=group.activity_type_id,
        session_date=payload.session_date,
        expected_count=len(member_ids),
        notes=payload.notes,
        created_by=current_user.id,
    )
    db.add(session)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Session already exists for this iCare on that date")

    for mid in member_ids:
        db.add(ActivityRegistration(
            session_id=session.id,
            member_id=mid,
            created_by=current_user.id,
        ))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Failed to register members for this session")

    db.refresh(session)
    return IcareSessionBulkOut(
        session_id=session.id,
        activity_type_id=session.activity_type_id,
        session_date=session.session_date,
        expected_count=session.expected_count,
        registered_member_ids=member_ids,
    )


# ── Attendance recording for an iCare (bulk) ──────────────────────────────────

@router.post("/groups/{group_id}/attendance", response_model=IcareAttendanceBulkOut, status_code=201)
def record_icare_attendance(
    group_id: int,
    payload: IcareAttendanceBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    """Record attendance for the listed members of this iCare on `attendance_date`
    (defaults to today). Skips (member, day) pairs that already have a record for
    this iCare's activity type. Caller must be super_admin or the iCare's leader."""
    group = db.get(IcareGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="iCare group not found")
    if group.activity_type_id is None:
        raise HTTPException(status_code=400, detail="iCare has no linked activity type")

    roles = get_user_role_names(current_user, db)
    is_admin = "super_admin" in roles
    is_leader_of_group = (
        ROLE_ICARE_LEADER in roles and current_user.member_id == group.leader_id
    )
    if not (is_admin or is_leader_of_group):
        raise HTTPException(status_code=403, detail="Not permitted for this iCare")

    if not payload.member_ids:
        raise HTTPException(status_code=400, detail="At least one member must be selected")

    member_ids = list(dict.fromkeys(payload.member_ids))
    valid_member_ids = {
        mid for (mid,) in (
            db.query(IcareMember.member_id)
            .filter(
                IcareMember.icare_id == group_id,
                IcareMember.member_id.in_(member_ids),
                IcareMember.is_active == True,  # noqa: E712
            )
            .all()
        )
    }
    invalid = [mid for mid in member_ids if mid not in valid_member_ids]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail={"message": "Some member_ids are not active members of this iCare", "invalid": invalid},
        )

    att_date = payload.attendance_date or date.today()
    ts = datetime.combine(att_date, time(12, 0))
    activity_type_id = group.activity_type_id

    existing_pairs = {
        mid for (mid,) in (
            db.query(Attendance.member_id)
            .filter(
                Attendance.activity_type_id == activity_type_id,
                Attendance.member_id.in_(member_ids),
                func.date(Attendance.timestamp) == att_date,
            )
            .all()
        )
    }

    inserted = 0
    skipped = 0
    for mid in member_ids:
        if mid in existing_pairs:
            skipped += 1
            continue
        db.add(Attendance(member_id=mid, activity_type_id=activity_type_id, timestamp=ts))
        inserted += 1

    db.commit()
    return IcareAttendanceBulkOut(
        activity_type_id=activity_type_id,
        attendance_date=att_date,
        inserted=inserted,
        skipped=skipped,
    )

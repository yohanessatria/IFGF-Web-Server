from typing import List, Optional
from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database import get_db
from app.core.security import (
    require_active_user,
    get_user_role_names,
    ROLE_SUPER_ADMIN,
    ROLE_CGSL_LEADER,
)
from app.models.church import (
    Cgsl, CgslMember, CgslTeacher, CgslMaterial, Member,
    ActivityType, ActivitySession, ActivityRegistration, Attendance,
)
from app.schemas.schemas import (
    CgslCreate, CgslUpdate, CgslOut,
    CgslMemberCreate, CgslMemberOut,
    CgslTeacherCreate, CgslTeacherOut,
    CgslMaterialCreate, CgslMaterialUpdate, CgslMaterialOut,
    CgslSessionBulkCreate, CgslSessionBulkOut,
    CgslAttendanceBulkCreate, CgslAttendanceBulkOut,
)

router = APIRouter(prefix="/api/cgsl", tags=["CGSL"])


def _require_cgsl_access(current_user, db: Session) -> None:
    roles = get_user_role_names(current_user, db)
    if ROLE_SUPER_ADMIN not in roles and ROLE_CGSL_LEADER not in roles:
        raise HTTPException(status_code=403, detail="CGSL leader or admin access required")


# ── Groups ────────────────────────────────────────────────────────────────────

@router.get("/groups", response_model=List[CgslOut])
def list_groups(db: Session = Depends(get_db), _=Depends(require_active_user)):
    return db.query(Cgsl).order_by(Cgsl.year.desc(), Cgsl.cgsl_category, Cgsl.batch_number).all()


@router.post("/groups", response_model=CgslOut, status_code=201)
def create_group(
    payload: CgslCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _require_cgsl_access(current_user, db)

    if db.query(ActivityType).filter(ActivityType.name == payload.name).first():
        raise HTTPException(status_code=409, detail=f"Activity type '{payload.name}' already exists")

    activity = ActivityType(name=payload.name, description="Auto-created for CGSL group", is_active=True)
    db.add(activity)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Failed to create linked activity type")

    group = Cgsl(**payload.model_dump(), activity_type_id=activity.id)
    db.add(group)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="CGSL group with this name already exists")
    db.refresh(group)
    return group


@router.get("/groups/{cgsl_id}", response_model=CgslOut)
def get_group(cgsl_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    group = db.get(Cgsl, cgsl_id)
    if not group:
        raise HTTPException(status_code=404, detail="CGSL group not found")
    return group


@router.patch("/groups/{cgsl_id}", response_model=CgslOut)
def update_group(
    cgsl_id: int,
    payload: CgslUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _require_cgsl_access(current_user, db)
    group = db.get(Cgsl, cgsl_id)
    if not group:
        raise HTTPException(status_code=404, detail="CGSL group not found")

    data = payload.model_dump(exclude_unset=True)
    new_name = data.get("name")

    if new_name is not None and new_name != group.name and group.activity_type_id is not None:
        clash = (
            db.query(ActivityType)
            .filter(ActivityType.name == new_name, ActivityType.id != group.activity_type_id)
            .first()
        )
        if clash:
            raise HTTPException(status_code=409, detail=f"Activity type '{new_name}' already exists")
        activity = db.get(ActivityType, group.activity_type_id)
        if activity:
            activity.name = new_name

    for field, value in data.items():
        setattr(group, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="CGSL group with this name already exists")
    db.refresh(group)
    return group


@router.delete("/groups/{cgsl_id}", status_code=204)
def delete_group(
    cgsl_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _require_cgsl_access(current_user, db)
    group = db.get(Cgsl, cgsl_id)
    if not group:
        raise HTTPException(status_code=404, detail="CGSL group not found")
    db.delete(group)
    db.commit()


# ── Members ───────────────────────────────────────────────────────────────────

@router.get("/groups/{cgsl_id}/members", response_model=List[CgslMemberOut])
def list_group_members(
    cgsl_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = db.query(CgslMember).filter(CgslMember.cgsl_id == cgsl_id)
    if active_only:
        q = q.filter(CgslMember.is_active == True)  # noqa: E712
    return q.all()


@router.post("/members", response_model=CgslMemberOut, status_code=201)
def add_member(
    payload: CgslMemberCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _require_cgsl_access(current_user, db)
    if not db.get(Cgsl, payload.cgsl_id):
        raise HTTPException(status_code=404, detail="CGSL group not found")
    if not db.get(Member, payload.member_id):
        raise HTTPException(status_code=404, detail="Member not found")

    record = CgslMember(
        cgsl_id=payload.cgsl_id,
        member_id=payload.member_id,
        joined_date=payload.joined_date or date.today(),
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Member already in this CGSL group")
    db.refresh(record)
    return record


@router.patch("/members/{record_id}/leave", response_model=CgslMemberOut)
def remove_member(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _require_cgsl_access(current_user, db)
    record = db.get(CgslMember, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="CGSL membership record not found")
    record.is_active = False
    record.left_date = date.today()
    db.commit()
    db.refresh(record)
    return record


# ── Teachers ──────────────────────────────────────────────────────────────────

@router.get("/groups/{cgsl_id}/teachers", response_model=List[CgslTeacherOut])
def list_group_teachers(
    cgsl_id: int,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = db.query(CgslTeacher).filter(CgslTeacher.cgsl_id == cgsl_id)
    if active_only:
        q = q.filter(CgslTeacher.is_active == True)  # noqa: E712
    return q.all()


@router.post("/teachers", response_model=CgslTeacherOut, status_code=201)
def add_teacher(
    payload: CgslTeacherCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _require_cgsl_access(current_user, db)
    if not db.get(Cgsl, payload.cgsl_id):
        raise HTTPException(status_code=404, detail="CGSL group not found")
    if not db.get(Member, payload.member_id):
        raise HTTPException(status_code=404, detail="Member not found")

    record = CgslTeacher(
        cgsl_id=payload.cgsl_id,
        member_id=payload.member_id,
        joined_date=payload.joined_date or date.today(),
    )
    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Member is already a teacher in this CGSL group")
    db.refresh(record)
    return record


@router.patch("/teachers/{record_id}/leave", response_model=CgslTeacherOut)
def remove_teacher(
    record_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _require_cgsl_access(current_user, db)
    record = db.get(CgslTeacher, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="CGSL teacher record not found")
    record.is_active = False
    record.left_date = date.today()
    db.commit()
    db.refresh(record)
    return record


# ── Materials ─────────────────────────────────────────────────────────────────

@router.get("/materials", response_model=List[CgslMaterialOut])
def list_materials(
    category: Optional[str] = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = db.query(CgslMaterial)
    if category:
        q = q.filter(CgslMaterial.category == category)
    if active_only:
        q = q.filter(CgslMaterial.is_active == True)  # noqa: E712
    return q.order_by(CgslMaterial.category, CgslMaterial.order_index).all()


@router.post("/materials", response_model=CgslMaterialOut, status_code=201)
def create_material(
    payload: CgslMaterialCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    roles = get_user_role_names(current_user, db)
    if ROLE_SUPER_ADMIN not in roles:
        raise HTTPException(status_code=403, detail="Admin only")

    material = CgslMaterial(**payload.model_dump())
    db.add(material)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A material with this category and chapter number already exists")
    db.refresh(material)
    return material


@router.patch("/materials/{material_id}", response_model=CgslMaterialOut)
def update_material(
    material_id: int,
    payload: CgslMaterialUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    roles = get_user_role_names(current_user, db)
    if ROLE_SUPER_ADMIN not in roles:
        raise HTTPException(status_code=403, detail="Admin only")

    material = db.get(CgslMaterial, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(material, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A material with this category and chapter number already exists")
    db.refresh(material)
    return material


@router.delete("/materials/{material_id}", status_code=204)
def delete_material(
    material_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    roles = get_user_role_names(current_user, db)
    if ROLE_SUPER_ADMIN not in roles:
        raise HTTPException(status_code=403, detail="Admin only")

    material = db.get(CgslMaterial, material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    db.delete(material)
    db.commit()


# ── Sessions (auto-register all active members + teachers) ────────────────────

@router.post("/groups/{cgsl_id}/sessions", response_model=CgslSessionBulkOut, status_code=201)
def create_cgsl_session(
    cgsl_id: int,
    payload: CgslSessionBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _require_cgsl_access(current_user, db)
    group = db.get(Cgsl, cgsl_id)
    if not group:
        raise HTTPException(status_code=404, detail="CGSL group not found")
    if group.activity_type_id is None:
        raise HTTPException(status_code=400, detail="CGSL group has no linked activity type")

    student_ids = [
        r[0] for r in (
            db.query(CgslMember.member_id)
            .filter(CgslMember.cgsl_id == cgsl_id, CgslMember.is_active == True)  # noqa: E712
            .all()
        )
    ]

    if not student_ids:
        raise HTTPException(status_code=400, detail="No active students in this CGSL group")

    session = ActivitySession(
        activity_type_id=group.activity_type_id,
        session_date=payload.session_date,
        expected_count=len(student_ids),
        notes=payload.notes,
        cgsl_material_id=payload.cgsl_material_id,
        created_by=current_user.id,
    )
    db.add(session)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Session already exists for this CGSL on that date")

    for mid in student_ids:
        db.add(ActivityRegistration(session_id=session.id, member_id=mid, created_by=current_user.id))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Failed to register members for this session")

    db.refresh(session)
    return CgslSessionBulkOut(
        session_id=session.id,
        activity_type_id=session.activity_type_id,
        session_date=session.session_date,
        expected_count=session.expected_count,
        registered_member_ids=student_ids,
    )


# ── Registered members for a session ─────────────────────────────────────────

@router.get("/groups/{cgsl_id}/sessions/{session_id}/registered", response_model=List[int])
def get_session_registered(
    cgsl_id: int,
    session_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    group = db.get(Cgsl, cgsl_id)
    if not group:
        raise HTTPException(status_code=404, detail="CGSL group not found")

    session = db.get(ActivitySession, session_id)
    if not session or session.activity_type_id != group.activity_type_id:
        raise HTTPException(status_code=404, detail="Session not found for this CGSL group")

    rows = db.query(ActivityRegistration.member_id).filter(ActivityRegistration.session_id == session_id).all()
    return [r[0] for r in rows]


# ── Attendance ────────────────────────────────────────────────────────────────

@router.post("/groups/{cgsl_id}/attendance", response_model=CgslAttendanceBulkOut, status_code=201)
def record_cgsl_attendance(
    cgsl_id: int,
    payload: CgslAttendanceBulkCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    _require_cgsl_access(current_user, db)
    group = db.get(Cgsl, cgsl_id)
    if not group:
        raise HTTPException(status_code=404, detail="CGSL group not found")
    if group.activity_type_id is None:
        raise HTTPException(status_code=400, detail="CGSL group has no linked activity type")

    if not payload.member_ids:
        raise HTTPException(status_code=400, detail="At least one member must be selected")

    member_ids = list(dict.fromkeys(payload.member_ids))
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
    return CgslAttendanceBulkOut(
        activity_type_id=activity_type_id,
        attendance_date=att_date,
        inserted=inserted,
        skipped=skipped,
    )

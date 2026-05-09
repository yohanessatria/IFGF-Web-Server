from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    require_active_user,
    get_allowed_activity_type_ids,
    assert_activity_type_allowed,
    get_user_role_names,
    ROLE_SUPER_ADMIN,
    ROLE_ICARE_LEADER,
)
from app.models.church import ActivityRegistration, ActivitySession, ActivityType, Member
from app.schemas.schemas import (
    ActivityRegistrationCreate,
    ActivityRegistrationUpdate,
    ActivityRegistrationOut,
    ActivityRegistrationWithDetails,
)

router = APIRouter(prefix="/api/activity-registrations", tags=["Activity Registrations"])


@router.get("", response_model=List[ActivityRegistrationWithDetails])
def list_registrations(
    session_id: Optional[int] = None,
    member_id: Optional[int] = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    roles = get_user_role_names(current_user, db)
    if ROLE_SUPER_ADMIN not in roles and ROLE_ICARE_LEADER not in roles:
        return []

    allowed = get_allowed_activity_type_ids(current_user, db)
    if allowed is not None and not allowed:
        return []

    q = (
        db.query(
            ActivityRegistration.id,
            ActivityRegistration.session_id,
            ActivityRegistration.member_id,
            ActivityRegistration.registered_at,
            ActivityRegistration.notes,
            ActivityRegistration.created_at,
            Member.full_name.label("member_name"),
            Member.nickname.label("member_nickname"),
            ActivitySession.session_date.label("session_date"),
            ActivityType.name.label("activity_type_name"),
        )
        .join(ActivitySession, ActivitySession.id == ActivityRegistration.session_id)
        .join(ActivityType, ActivityType.id == ActivitySession.activity_type_id)
        .join(Member, Member.id == ActivityRegistration.member_id)
    )
    if ROLE_SUPER_ADMIN not in roles:
        q = q.filter(ActivitySession.created_by == current_user.id)
    if allowed is not None:
        q = q.filter(ActivitySession.activity_type_id.in_(allowed))
    if session_id:
        q = q.filter(ActivityRegistration.session_id == session_id)
    if member_id:
        q = q.filter(ActivityRegistration.member_id == member_id)

    rows = q.order_by(ActivityRegistration.registered_at.desc()).offset(skip).limit(limit).all()
    return [ActivityRegistrationWithDetails(**row._mapping) for row in rows]


@router.post("", response_model=ActivityRegistrationOut, status_code=201)
def create_registration(
    payload: ActivityRegistrationCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    session = db.get(ActivitySession, payload.session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_activity_type_allowed(current_user, db, session.activity_type_id)
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


def _assert_reg_allowed(reg: ActivityRegistration, current_user, db: Session):
    session = db.get(ActivitySession, reg.session_id)
    if session is not None:
        assert_activity_type_allowed(current_user, db, session.activity_type_id)


@router.get("/{registration_id}", response_model=ActivityRegistrationOut)
def get_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    reg = db.get(ActivityRegistration, registration_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    _assert_reg_allowed(reg, current_user, db)
    return reg


@router.patch("/{registration_id}", response_model=ActivityRegistrationOut)
def update_registration(
    registration_id: int,
    payload: ActivityRegistrationUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    reg = db.get(ActivityRegistration, registration_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    _assert_reg_allowed(reg, current_user, db)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(reg, field, value)

    db.commit()
    db.refresh(reg)
    return reg


@router.delete("/{registration_id}", status_code=204)
def delete_registration(
    registration_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    reg = db.get(ActivityRegistration, registration_id)
    if not reg:
        raise HTTPException(status_code=404, detail="Registration not found")
    _assert_reg_allowed(reg, current_user, db)
    db.delete(reg)
    db.commit()

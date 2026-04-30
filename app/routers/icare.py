from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import IcareGroup, IcareMember, Member
from app.schemas.schemas import (
    IcareGroupCreate, IcareGroupUpdate, IcareGroupOut,
    IcareMemberCreate, IcareMemberOut,
)
from datetime import date

router = APIRouter(prefix="/api/icare", tags=["iCare Groups"])


# ── Groups ────────────────────────────────────────────────────────────────────

@router.get("/groups", response_model=List[IcareGroupOut])
def list_groups(db: Session = Depends(get_db), _=Depends(require_active_user)):
    return db.query(IcareGroup).order_by(IcareGroup.name).all()


@router.post("/groups", response_model=IcareGroupOut, status_code=201)
def create_group(payload: IcareGroupCreate, db: Session = Depends(get_db), _=Depends(require_active_user)):
    group = IcareGroup(**payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.get("/groups/{group_id}", response_model=IcareGroupOut)
def get_group(group_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    group = db.get(IcareGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="iCare group not found")
    return group


@router.patch("/groups/{group_id}", response_model=IcareGroupOut)
def update_group(group_id: int, payload: IcareGroupUpdate, db: Session = Depends(get_db), _=Depends(require_active_user)):
    group = db.get(IcareGroup, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="iCare group not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
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

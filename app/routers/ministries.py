from typing import List
from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import MinistryType, MemberMinistry, Member
from app.schemas.schemas import MinistryTypeOut, MemberMinistryCreate, MemberMinistryOut

router = APIRouter(prefix="/api/ministries", tags=["Ministries"])


@router.get("/types", response_model=List[MinistryTypeOut])
def list_ministry_types(db: Session = Depends(get_db), _=Depends(require_active_user)):
    return db.query(MinistryType).filter(MinistryType.is_active == True).all()


@router.get("/members", response_model=List[MemberMinistryOut])
def list_all_member_ministries(
    ministry_type_id: int = None,
    active_only: bool = True,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = db.query(MemberMinistry)
    if ministry_type_id:
        q = q.filter(MemberMinistry.ministry_type_id == ministry_type_id)
    if active_only:
        q = q.filter(MemberMinistry.is_active == True)
    return q.all()


@router.post("/members", response_model=MemberMinistryOut, status_code=201)
def assign_ministry(payload: MemberMinistryCreate, db: Session = Depends(get_db), _=Depends(require_active_user)):
    if not db.get(Member, payload.member_id):
        raise HTTPException(status_code=404, detail="Member not found")
    if not db.get(MinistryType, payload.ministry_type_id):
        raise HTTPException(status_code=404, detail="Ministry type not found")
    record = MemberMinistry(
        member_id=payload.member_id,
        ministry_type_id=payload.ministry_type_id,
        joined_date=payload.joined_date or date.today(),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.patch("/members/{record_id}/leave", response_model=MemberMinistryOut)
def leave_ministry(record_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    record = db.get(MemberMinistry, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Ministry record not found")
    record.is_active = False
    record.left_date = date.today()
    db.commit()
    db.refresh(record)
    return record


@router.get("/members/{member_id}", response_model=List[MemberMinistryOut])
def get_member_ministries(member_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    return db.query(MemberMinistry).filter(
        MemberMinistry.member_id == member_id,
        MemberMinistry.is_active == True,
    ).all()

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import Member
from app.schemas.schemas import MemberCreate, MemberUpdate, MemberOut

router = APIRouter(prefix="/api/members", tags=["Members"])


@router.get("", response_model=List[MemberOut])
def list_members(
    skip: int = 0,
    limit: int = Query(50, le=200),
    status: Optional[str] = None,
    category: Optional[str] = None,
    cgsl_status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = db.query(Member)
    if status:
        q = q.filter(Member.member_status == status)
    if category:
        q = q.filter(Member.category == category)
    if cgsl_status:
        q = q.filter(Member.cgsl_status == cgsl_status)
    if search:
        term = f"%{search}%"
        q = q.filter(
            Member.full_name.ilike(term) |
            Member.nickname.ilike(term) |
            Member.email.ilike(term) |
            Member.phone.ilike(term)
        )
    return q.order_by(Member.full_name).offset(skip).limit(limit).all()


@router.post("/", response_model=MemberOut, status_code=201)
def create_member(
    payload: MemberCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_active_user),
):
    member = Member(**payload.model_dump(), created_by=current_user.id)
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/{member_id}", response_model=MemberOut)
def get_member(member_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.patch("/{member_id}", response_model=MemberOut)
def update_member(
    member_id: int,
    payload: MemberUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(member, field, value)
    db.commit()
    db.refresh(member)
    return member


@router.delete("/{member_id}", status_code=204)
def delete_member(member_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    member = db.get(Member, member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    db.delete(member)
    db.commit()

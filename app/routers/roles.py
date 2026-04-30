from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.user import Role, Page, RolePermission
from app.schemas.schemas import RoleOut, PageOut, RolePermissionUpsert, RolePermissionOut

router = APIRouter(prefix="/api/roles", tags=["Roles"])


# ── Roles ─────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[RoleOut])
def list_roles(db: Session = Depends(get_db), _=Depends(require_active_user)):
    return db.query(Role).all()


@router.get("/{role_id}", response_model=RoleOut)
def get_role(role_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/pages/", response_model=list[PageOut])
def list_pages(db: Session = Depends(get_db), _=Depends(require_active_user)):
    return db.query(Page).all()


# ── Role Permissions ──────────────────────────────────────────────────────────

@router.get("/{role_id}/permissions", response_model=list[RolePermissionOut])
def list_permissions(role_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return db.query(RolePermission).filter(RolePermission.role_id == role_id).all()


@router.put("/{role_id}/permissions", response_model=RolePermissionOut)
def upsert_permission(
    role_id: int,
    payload: RolePermissionUpsert,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    if not db.query(Role).filter(Role.id == role_id).first():
        raise HTTPException(status_code=404, detail="Role not found")
    if not db.query(Page).filter(Page.id == payload.page_id).first():
        raise HTTPException(status_code=404, detail="Page not found")
    perm = db.query(RolePermission).filter(
        RolePermission.role_id == role_id, RolePermission.page_id == payload.page_id
    ).first()
    if perm:
        perm.can_read = payload.can_read
        perm.can_write = payload.can_write
    else:
        perm = RolePermission(
            role_id=role_id,
            page_id=payload.page_id,
            can_read=payload.can_read,
            can_write=payload.can_write,
        )
        db.add(perm)
    db.commit()
    db.refresh(perm)
    return perm


@router.delete("/{role_id}/permissions/{page_id}", status_code=204)
def delete_permission(
    role_id: int,
    page_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    perm = db.query(RolePermission).filter(
        RolePermission.role_id == role_id, RolePermission.page_id == page_id
    ).first()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    db.delete(perm)
    db.commit()

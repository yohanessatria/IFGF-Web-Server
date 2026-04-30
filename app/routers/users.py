from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user, get_password_hash
from app.models.user import User, UserRole, Role
from app.schemas.schemas import UserOut, UserWithRoles, UserRoleCreate, UserRoleOut

router = APIRouter(prefix="/api/users", tags=["Users"])


def _user_with_roles(user: User) -> UserWithRoles:
    data = UserWithRoles.model_validate(user)
    data.roles = [ur.role.name for ur in user.user_roles]
    return data


@router.get("/", response_model=list[UserWithRoles])
def list_users(db: Session = Depends(get_db), _=Depends(require_active_user)):
    users = db.query(User).all()
    return [_user_with_roles(u) for u in users]


@router.get("/{user_id}", response_model=UserWithRoles)
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_with_roles(user)


@router.patch("/{user_id}/deactivate", response_model=UserOut)
def deactivate_user(user_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/activate", response_model=UserOut)
def activate_user(user_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/password")
def change_password(
    user_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    new_password = payload.get("password")
    if not new_password:
        raise HTTPException(status_code=422, detail="password field required")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = get_password_hash(new_password)
    db.commit()
    return {"detail": "Password updated"}


@router.post("/{user_id}/roles", response_model=UserRoleOut, status_code=201)
def assign_role(
    user_id: int,
    payload: UserRoleCreate,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    role = db.query(Role).filter(Role.id == payload.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    existing = db.query(UserRole).filter(
        UserRole.user_id == user_id, UserRole.role_id == payload.role_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="User already has this role")
    user_role = UserRole(user_id=user_id, role_id=payload.role_id)
    db.add(user_role)
    db.commit()
    db.refresh(user_role)
    return user_role


@router.delete("/{user_id}/roles/{role_id}", status_code=204)
def remove_role(
    user_id: int,
    role_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    user_role = db.query(UserRole).filter(
        UserRole.user_id == user_id, UserRole.role_id == role_id
    ).first()
    if not user_role:
        raise HTTPException(status_code=404, detail="Role assignment not found")
    db.delete(user_role)
    db.commit()

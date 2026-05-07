from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import (
    verify_password, get_password_hash,
    create_access_token, require_active_user
)
from app.models.user import User, UserRole, Role, RolePermission
from app.models.church import Member
from app.schemas.schemas import Token, UserCreate, UserOut, UserWithRoles, PermissionOut

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/register", response_model=UserOut, status_code=201)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    if not db.query(Member).filter(Member.id == payload.member_id).first():
        raise HTTPException(status_code=404, detail="Member not found")
    if db.query(User).filter(User.member_id == payload.member_id).first():
        raise HTTPException(status_code=400, detail="Member already has a user account")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    user = User(
        member_id=payload.member_id,
        username=payload.username,
        password_hash=get_password_hash(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserWithRoles)
def me(current_user: User = Depends(require_active_user), db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(
            joinedload(User.member),
            joinedload(User.user_roles).joinedload(UserRole.role).joinedload(Role.role_permissions).joinedload(RolePermission.page),
        )
        .filter(User.id == current_user.id)
        .first()
    )

    permissions: dict[str, PermissionOut] = {}
    for ur in user.user_roles:
        for rp in ur.role.role_permissions:
            slug = rp.page.slug
            existing = permissions.get(slug)
            permissions[slug] = PermissionOut(
                read=rp.can_read   or (existing.read  if existing else False),
                write=rp.can_write or (existing.write if existing else False),
            )

    return UserWithRoles(
        id=user.id,
        member_id=user.member_id,
        username=user.username,
        full_name=user.member.full_name if user.member else None,
        is_active=user.is_active,
        last_login=user.last_login,
        created_at=user.created_at,
        permissions=permissions,
        roles=[ur.role.name for ur in user.user_roles],
    )

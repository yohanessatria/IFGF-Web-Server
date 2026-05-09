from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db

ROLE_SUPER_ADMIN = "super_admin"
ROLE_ICARE_LEADER = "icare_leader"
ROLE_CGSL_LEADER = "cgsl_leader"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    from app.models.user import User

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    return user


def require_active_user(current_user=Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_user_role_names(user, db: Session) -> set[str]:
    from app.models.user import UserRole, Role
    rows = (
        db.query(Role.name)
        .join(UserRole, UserRole.role_id == Role.id)
        .filter(UserRole.user_id == user.id)
        .all()
    )
    return {r[0] for r in rows}


def is_super_admin(user, db: Session) -> bool:
    return ROLE_SUPER_ADMIN in get_user_role_names(user, db)


def get_allowed_activity_type_ids(user, db: Session) -> Optional[list[int]]:
    """Activity-type scoping for the current user.

    Returns:
      None  → unrestricted (super_admin sees all)
      list  → restricted to these activity_type_ids (possibly empty if none)
    """
    from app.models.church import IcareGroup, Cgsl
    roles = get_user_role_names(user, db)
    if ROLE_SUPER_ADMIN in roles:
        return None
    allowed: list[int] = []
    if ROLE_ICARE_LEADER in roles and user.member_id is not None:
        rows = (
            db.query(IcareGroup.activity_type_id)
            .filter(
                IcareGroup.leader_id == user.member_id,
                IcareGroup.is_active == True,  # noqa: E712
                IcareGroup.activity_type_id.isnot(None),
            )
            .all()
        )
        allowed.extend(r[0] for r in rows)
    if ROLE_CGSL_LEADER in roles:
        rows = (
            db.query(Cgsl.activity_type_id)
            .filter(
                Cgsl.is_active == True,  # noqa: E712
                Cgsl.activity_type_id.isnot(None),
            )
            .all()
        )
        allowed.extend(r[0] for r in rows)
    return allowed


def assert_activity_type_allowed(user, db: Session, activity_type_id: int) -> None:
    allowed = get_allowed_activity_type_ids(user, db)
    if allowed is None:
        return
    if activity_type_id not in allowed:
        raise HTTPException(status_code=403, detail="Not permitted for this activity type")

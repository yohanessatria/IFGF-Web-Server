from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    member_id     = Column(Integer, ForeignKey("members.id", ondelete="RESTRICT"), nullable=False, unique=True)
    username      = Column(String(50), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active     = Column(Boolean, nullable=False, default=True)
    last_login    = Column(DateTime)
    created_at    = Column(DateTime, nullable=False, server_default=func.now())

    member     = relationship("Member", foreign_keys=[member_id])
    user_roles = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")


class Role(Base):
    __tablename__ = "roles"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(50), nullable=False, unique=True)
    description = Column(String)
    created_at  = Column(DateTime, nullable=False, server_default=func.now())

    user_roles       = relationship("UserRole", back_populates="role")
    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")


class UserRole(Base):
    __tablename__ = "user_roles"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_roles"),)

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    role_id    = Column(Integer, ForeignKey("roles.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    user = relationship("User", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class Page(Base):
    __tablename__ = "pages"

    id         = Column(Integer, primary_key=True, index=True)
    slug       = Column(String(100), nullable=False, unique=True)
    name       = Column(String(100), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    role_permissions = relationship("RolePermission", back_populates="page", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "page_id", name="uq_role_page"),)

    id         = Column(Integer, primary_key=True, index=True)
    role_id    = Column(Integer, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False)
    page_id    = Column(Integer, ForeignKey("pages.id", ondelete="CASCADE"), nullable=False)
    can_read   = Column(Boolean, nullable=False, default=False)
    can_write  = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    role = relationship("Role", back_populates="role_permissions")
    page = relationship("Page", back_populates="role_permissions")

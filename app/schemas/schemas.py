from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


# ── AUTH ──────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    member_id: int
    username: str
    password: str


class PermissionOut(BaseModel):
    read: bool
    write: bool


class UserOut(BaseModel):
    id: int
    member_id: int
    username: str
    full_name: Optional[str] = None
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime
    permissions: dict[str, PermissionOut] = {}
    model_config = ConfigDict(from_attributes=True)


class UserWithRoles(UserOut):
    roles: List[str] = []


# ── ROLE ──────────────────────────────────────────────────────────────────────

class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None


class RoleOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class UserRoleCreate(BaseModel):
    role_id: int


class UserRoleOut(BaseModel):
    id: int
    user_id: int
    role_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── PAGE ──────────────────────────────────────────────────────────────────────

class PageCreate(BaseModel):
    slug: str
    name: str


class PageOut(BaseModel):
    id: int
    slug: str
    name: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── ROLE PERMISSION ───────────────────────────────────────────────────────────

class RolePermissionUpsert(BaseModel):
    page_id: int
    can_read: bool = False
    can_write: bool = False


class RolePermissionOut(BaseModel):
    id: int
    role_id: int
    page_id: int
    can_read: bool
    can_write: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── MEMBER ────────────────────────────────────────────────────────────────────

class MemberBase(BaseModel):
    full_name: str
    nickname: Optional[str] = None
    chinese_name: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    address_home_country: Optional[str] = None
    photo_url: Optional[str] = None
    baptism_status: str = "no"
    baptism_date: Optional[date] = None
    cgsl_status: str = "none"
    category: Optional[str] = None
    marital_status: Optional[str] = None
    occupation: Optional[str] = None
    member_status: str = "visitor"
    join_date: Optional[date] = None
    home_church: Optional[str] = None
    notes: Optional[str] = None


class MemberCreate(MemberBase):
    pass


class MemberUpdate(MemberBase):
    full_name: Optional[str] = None
    baptism_status: Optional[str] = None
    cgsl_status: Optional[str] = None
    member_status: Optional[str] = None


class MemberOut(MemberBase):
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ── ACTIVITY TYPE ─────────────────────────────────────────────────────────────

class ActivityTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class ActivityTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ActivityTypeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# ── ATTENDANCE ────────────────────────────────────────────────────────────────

class AttendanceCheckIn(BaseModel):
    member_id: int
    activity_type_id: int
    timestamp: Optional[datetime] = None   # defaults to now


class AttendanceOut(BaseModel):
    id: int
    member_id: int
    activity_type_id: int
    timestamp: datetime
    model_config = ConfigDict(from_attributes=True)


class AttendanceWithMember(AttendanceOut):
    member_name: str
    member_nickname: Optional[str]
    activity_name: str


# ── ICARE GROUP ───────────────────────────────────────────────────────────────

class IcareGroupBase(BaseModel):
    name: str
    leader_id: Optional[int] = None
    is_active: bool = True


class IcareGroupCreate(IcareGroupBase):
    pass


class IcareGroupUpdate(BaseModel):
    name: Optional[str] = None
    leader_id: Optional[int] = None
    is_active: Optional[bool] = None


class IcareGroupOut(IcareGroupBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


# ── ICARE MEMBER ──────────────────────────────────────────────────────────────

class IcareMemberCreate(BaseModel):
    icare_id: int
    member_id: int
    joined_date: Optional[date] = None


class IcareMemberOut(BaseModel):
    id: int
    icare_id: int
    member_id: int
    joined_date: date
    left_date: Optional[date]
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# ── MINISTRY TYPE ─────────────────────────────────────────────────────────────

class MinistryTypeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True


class MinistryTypeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class MinistryTypeOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# ── MEMBER MINISTRY ───────────────────────────────────────────────────────────

class MemberMinistryCreate(BaseModel):
    member_id: int
    ministry_type_id: int
    joined_date: Optional[date] = None


class MemberMinistryOut(BaseModel):
    id: int
    member_id: int
    ministry_type_id: int
    joined_date: date
    left_date: Optional[date]
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# ── DASHBOARD ─────────────────────────────────────────────────────────────────

class DashboardStats(BaseModel):
    total_members: int
    active_members: int
    baptized_members: int
    members_by_category: dict
    members_by_cgsl: dict
    attendance_last_4_weeks: List[dict]
    icare_group_summary: List[dict]

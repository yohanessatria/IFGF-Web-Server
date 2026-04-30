from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict


# ── AUTH ──────────────────────────────────────────────────────────────────────

class Token(BaseModel):
    access_token: str
    token_type: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: str = "staff"


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    model_config = ConfigDict(from_attributes=True)


# ── MEMBER ────────────────────────────────────────────────────────────────────

class MemberBase(BaseModel):
    full_name: str
    nickname: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
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

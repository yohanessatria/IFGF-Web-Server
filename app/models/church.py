from sqlalchemy import (
    Column, Integer, String, Boolean, Date, DateTime,
    Text, ForeignKey, UniqueConstraint, CheckConstraint, func
)
from app.core.database import Base


class Member(Base):
    __tablename__ = "members"

    id                   = Column(Integer, primary_key=True, index=True)
    full_name            = Column(String(100), nullable=False)
    nickname             = Column(String(50))
    chinese_name         = Column(String(100))
    date_of_birth        = Column(Date)
    gender               = Column(String(1))
    phone                = Column(String(50))
    email                = Column(String(100))
    address              = Column(Text)
    address_home_country = Column(Text)
    photo_url            = Column(String(255))

    baptism_status   = Column(String(10), nullable=False, default="no")
    baptism_date     = Column(Date)
    cgsl_status      = Column(String(20), nullable=False, default="none")

    category         = Column(String(20))
    marital_status   = Column(String(10))
    occupation       = Column(String(100))

    member_status    = Column(String(10), nullable=False, default="visitor")
    join_date        = Column(Date)
    home_church      = Column(String(100))

    fp_user_id       = Column(Integer, unique=True)

    notes            = Column(Text)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by       = Column(Integer)

    __table_args__ = (
        CheckConstraint("gender IN ('M','F')", name="ck_members_gender"),
        CheckConstraint("baptism_status IN ('yes','no')", name="ck_members_baptism"),
        CheckConstraint("cgsl_status IN ('none','come','grow','lead','serve')", name="ck_members_cgsl"),
        CheckConstraint("category IN ('student','professional','family','teenager','children')", name="ck_members_category"),
        CheckConstraint("marital_status IN ('single','married','widowed')", name="ck_members_marital"),
        CheckConstraint("member_status IN ('active','inactive','visitor')", name="ck_members_status"),
    )


class ActivityType(Base):
    __tablename__ = "activity_types"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class ActivitySession(Base):
    __tablename__ = "activity_sessions"

    id               = Column(Integer, primary_key=True, index=True)
    activity_type_id = Column(Integer, ForeignKey("activity_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    session_date     = Column(Date, nullable=False, index=True)
    expected_count   = Column(Integer, nullable=True)
    notes            = Column(Text)
    cgsl_material_id = Column(Integer, ForeignKey("cgsl_materials.id", ondelete="SET NULL"), nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    created_by       = Column(Integer)

    __table_args__ = (
        UniqueConstraint("activity_type_id", "session_date", name="uq_session"),
    )


class ActivityRegistration(Base):
    __tablename__ = "activity_registrations"

    id            = Column(Integer, primary_key=True, index=True)
    session_id    = Column(Integer, ForeignKey("activity_sessions.id", ondelete="RESTRICT"), nullable=False, index=True)
    member_id     = Column(Integer, ForeignKey("members.id", ondelete="RESTRICT"), nullable=False, index=True)
    registered_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    notes         = Column(Text)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    created_by    = Column(Integer)

    __table_args__ = (
        UniqueConstraint("session_id", "member_id", name="uq_activity_registration"),
    )


class Attendance(Base):
    __tablename__ = "attendance"

    id               = Column(Integer, primary_key=True, index=True)
    member_id        = Column(Integer, ForeignKey("members.id", ondelete="RESTRICT"), nullable=False, index=True)
    activity_type_id = Column(Integer, ForeignKey("activity_types.id", ondelete="RESTRICT"), nullable=False, index=True)
    timestamp        = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class IcareGroup(Base):
    __tablename__ = "icare_groups"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(100), nullable=False, unique=True)
    leader_id        = Column(Integer, ForeignKey("members.id", ondelete="SET NULL"))
    activity_type_id = Column(Integer, ForeignKey("activity_types.id", ondelete="SET NULL"), unique=True)
    is_active        = Column(Boolean, nullable=False, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())


class IcareMember(Base):
    __tablename__ = "icare_members"

    id          = Column(Integer, primary_key=True, index=True)
    icare_id    = Column(Integer, ForeignKey("icare_groups.id", ondelete="RESTRICT"), nullable=False, index=True)
    member_id   = Column(Integer, ForeignKey("members.id", ondelete="RESTRICT"), nullable=False, index=True)
    joined_date = Column(Date, nullable=False, server_default=func.current_date())
    left_date   = Column(Date)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class MinistryType(Base):
    __tablename__ = "ministry_types"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())


class CgslMaterial(Base):
    __tablename__ = "cgsl_materials"

    id          = Column(Integer, primary_key=True, index=True)
    order_index = Column(Integer, nullable=False)
    category    = Column(String(10), nullable=False)
    title       = Column(String(200), nullable=False)
    description = Column(Text)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("category IN ('come','grow','lead','serve')", name="ck_cgsl_material_category"),
        UniqueConstraint("category", "order_index", name="uq_cgsl_material_chapter"),
    )


class Cgsl(Base):
    __tablename__ = "cgsl"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(200), nullable=False, unique=True)
    cgsl_category    = Column(String(10), nullable=False)
    batch_number     = Column(Integer, nullable=False)
    year             = Column(Integer, nullable=False)
    activity_type_id = Column(Integer, ForeignKey("activity_types.id", ondelete="SET NULL"), unique=True)
    is_active        = Column(Boolean, nullable=False, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        CheckConstraint("cgsl_category IN ('come','grow','lead','serve')", name="ck_cgsl_category"),
    )


class CgslMember(Base):
    __tablename__ = "cgsl_members"

    id          = Column(Integer, primary_key=True, index=True)
    cgsl_id     = Column(Integer, ForeignKey("cgsl.id", ondelete="RESTRICT"), nullable=False, index=True)
    member_id   = Column(Integer, ForeignKey("members.id", ondelete="RESTRICT"), nullable=False, index=True)
    joined_date = Column(Date, nullable=False, server_default=func.current_date())
    left_date   = Column(Date)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("cgsl_id", "member_id", name="uq_cgsl_member"),
    )


class CgslTeacher(Base):
    __tablename__ = "cgsl_teachers"

    id          = Column(Integer, primary_key=True, index=True)
    cgsl_id     = Column(Integer, ForeignKey("cgsl.id", ondelete="RESTRICT"), nullable=False, index=True)
    member_id   = Column(Integer, ForeignKey("members.id", ondelete="RESTRICT"), nullable=False, index=True)
    joined_date = Column(Date, nullable=False, server_default=func.current_date())
    left_date   = Column(Date)
    is_active   = Column(Boolean, nullable=False, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("cgsl_id", "member_id", name="uq_cgsl_teacher"),
    )


class MemberMinistry(Base):
    __tablename__ = "member_ministries"

    id               = Column(Integer, primary_key=True, index=True)
    member_id        = Column(Integer, ForeignKey("members.id", ondelete="RESTRICT"), nullable=False, index=True)
    ministry_type_id = Column(Integer, ForeignKey("ministry_types.id", ondelete="RESTRICT"), nullable=False)
    joined_date      = Column(Date, nullable=False, server_default=func.current_date())
    left_date        = Column(Date)
    is_active        = Column(Boolean, nullable=False, default=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

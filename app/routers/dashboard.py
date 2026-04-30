from datetime import date, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import Member, Attendance, IcareGroup, IcareMember, ActivityType
from app.schemas.schemas import DashboardStats

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db), _=Depends(require_active_user)):

    # Basic member counts
    total_members  = db.query(func.count(Member.id)).scalar()
    active_members = db.query(func.count(Member.id)).filter(Member.member_status == "active").scalar()
    baptized       = db.query(func.count(Member.id)).filter(Member.baptism_status == "yes").scalar()

    # Members by category
    cat_rows = (
        db.query(Member.category, func.count(Member.id))
        .filter(Member.member_status == "active")
        .group_by(Member.category)
        .all()
    )
    members_by_category = {(row[0] or "unknown"): row[1] for row in cat_rows}

    # Members by CGSL status
    cgsl_rows = (
        db.query(Member.cgsl_status, func.count(Member.id))
        .filter(Member.member_status == "active")
        .group_by(Member.cgsl_status)
        .all()
    )
    members_by_cgsl = {(row[0] or "none"): row[1] for row in cgsl_rows}

    # Attendance last 4 Sundays (per activity type per date)
    four_weeks_ago = date.today() - timedelta(weeks=4)
    att_rows = (
        db.query(
            func.date(Attendance.timestamp).label("session_date"),
            ActivityType.name.label("activity"),
            func.count(Attendance.id).label("count"),
        )
        .join(ActivityType, Attendance.activity_type_id == ActivityType.id)
        .filter(func.date(Attendance.timestamp) >= four_weeks_ago)
        .group_by(func.date(Attendance.timestamp), ActivityType.name)
        .order_by(func.date(Attendance.timestamp))
        .all()
    )
    attendance_last_4_weeks = [
        {"date": str(r.session_date), "activity": r.activity, "count": r.count}
        for r in att_rows
    ]

    # iCare group summary
    group_rows = (
        db.query(
            IcareGroup.id,
            IcareGroup.name,
            func.count(IcareMember.id).label("member_count"),
        )
        .outerjoin(IcareMember, and_(
            IcareMember.icare_id == IcareGroup.id,
            IcareMember.is_active == True,
        ))
        .filter(IcareGroup.is_active == True)
        .group_by(IcareGroup.id, IcareGroup.name)
        .order_by(IcareGroup.name)
        .all()
    )
    icare_group_summary = [
        {"id": r.id, "name": r.name, "member_count": r.member_count}
        for r in group_rows
    ]

    return DashboardStats(
        total_members=total_members,
        active_members=active_members,
        baptized_members=baptized,
        members_by_category=members_by_category,
        members_by_cgsl=members_by_cgsl,
        attendance_last_4_weeks=attendance_last_4_weeks,
        icare_group_summary=icare_group_summary,
    )


@router.get("/attendance/trends")
def attendance_trends(weeks: int = 8, db: Session = Depends(get_db), _=Depends(require_active_user)):
    """Weekly attendance count per activity type for the last N weeks."""
    start = date.today() - timedelta(weeks=weeks)
    rows = (
        db.query(
            func.date_trunc("week", Attendance.timestamp).label("week"),
            ActivityType.name.label("activity"),
            func.count(Attendance.id).label("count"),
        )
        .join(ActivityType, Attendance.activity_type_id == ActivityType.id)
        .filter(func.date(Attendance.timestamp) >= start)
        .group_by(func.date_trunc("week", Attendance.timestamp), ActivityType.name)
        .order_by(func.date_trunc("week", Attendance.timestamp))
        .all()
    )
    return [{"week": str(r.week.date()), "activity": r.activity, "count": r.count} for r in rows]


@router.get("/members/new")
def new_members(days: int = 30, db: Session = Depends(get_db), _=Depends(require_active_user)):
    """Members who joined in the last N days."""
    since = date.today() - timedelta(days=days)
    rows = (
        db.query(Member.id, Member.full_name, Member.join_date, Member.category)
        .filter(Member.join_date >= since)
        .order_by(Member.join_date.desc())
        .all()
    )
    return [{"id": r.id, "full_name": r.full_name, "join_date": str(r.join_date), "category": r.category} for r in rows]


@router.get("/members/inactive-risk")
def inactive_risk(db: Session = Depends(get_db), _=Depends(require_active_user)):
    """Active members who haven't attended any service in the last 4 weeks."""
    four_weeks_ago = date.today() - timedelta(weeks=4)

    attended_ids = (
        db.query(Attendance.member_id)
        .filter(func.date(Attendance.timestamp) >= four_weeks_ago)
        .distinct()
        .subquery()
    )

    at_risk = (
        db.query(Member.id, Member.full_name, Member.nickname, Member.phone, Member.email)
        .filter(
            Member.member_status == "active",
            ~Member.id.in_(attended_ids),
        )
        .order_by(Member.full_name)
        .all()
    )
    return [
        {"id": r.id, "full_name": r.full_name, "nickname": r.nickname,
         "phone": r.phone, "email": r.email}
        for r in at_risk
    ]

from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy import func, text, and_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_active_user
from app.models.church import Attendance, Member, ActivityType
from app.schemas.schemas import AttendanceCheckIn, AttendanceOut, AttendanceWithMember

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


@router.post("/checkin", response_model=AttendanceOut, status_code=201)
def check_in(
    payload: AttendanceCheckIn,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    """Record attendance for a member. Prevents duplicate on the same day+activity."""
    member = db.get(Member, payload.member_id)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    activity = db.get(ActivityType, payload.activity_type_id)
    if not activity or not activity.is_active:
        raise HTTPException(status_code=404, detail="Activity type not found or inactive")

    ts = payload.timestamp or datetime.utcnow()
    check_date = ts.date()

    # Check duplicate
    existing = db.query(Attendance).filter(
        Attendance.member_id == payload.member_id,
        Attendance.activity_type_id == payload.activity_type_id,
        func.date(Attendance.timestamp) == check_date,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Attendance already recorded for this session")

    record = Attendance(
        member_id=payload.member_id,
        activity_type_id=payload.activity_type_id,
        timestamp=ts,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=List[AttendanceWithMember])
def list_attendance(
    activity_type_id: Optional[int] = None,
    member_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    skip: int = 0,
    limit: int = Query(100, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    q = (
        db.query(
            Attendance.id,
            Attendance.member_id,
            Attendance.activity_type_id,
            Attendance.timestamp,
            Member.full_name.label("member_name"),
            Member.nickname.label("member_nickname"),
            ActivityType.name.label("activity_name"),
        )
        .join(Member, Attendance.member_id == Member.id)
        .join(ActivityType, Attendance.activity_type_id == ActivityType.id)
    )
    if activity_type_id:
        q = q.filter(Attendance.activity_type_id == activity_type_id)
    if member_id:
        q = q.filter(Attendance.member_id == member_id)
    if date_from:
        q = q.filter(func.date(Attendance.timestamp) >= date_from)
    if date_to:
        q = q.filter(func.date(Attendance.timestamp) <= date_to)

    rows = q.order_by(Attendance.timestamp.desc()).offset(skip).limit(limit).all()
    return [AttendanceWithMember(**row._mapping) for row in rows]


@router.get("/session/{activity_type_id}/{session_date}", response_model=List[AttendanceWithMember])
def get_session_attendance(
    activity_type_id: int,
    session_date: date,
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    """Get all attendees for a specific activity on a specific date."""
    rows = (
        db.query(
            Attendance.id,
            Attendance.member_id,
            Attendance.activity_type_id,
            Attendance.timestamp,
            Member.full_name.label("member_name"),
            Member.nickname.label("member_nickname"),
            ActivityType.name.label("activity_name"),
        )
        .join(Member, Attendance.member_id == Member.id)
        .join(ActivityType, Attendance.activity_type_id == ActivityType.id)
        .filter(
            Attendance.activity_type_id == activity_type_id,
            func.date(Attendance.timestamp) == session_date,
        )
        .order_by(Attendance.timestamp)
        .all()
    )
    return [AttendanceWithMember(**row._mapping) for row in rows]


@router.delete("/{attendance_id}", status_code=204)
def delete_attendance(attendance_id: int, db: Session = Depends(get_db), _=Depends(require_active_user)):
    record = db.get(Attendance, attendance_id)
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    db.delete(record)
    db.commit()


@router.post("/import")
def import_attendance_report(
    activity_type_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(require_active_user),
):
    """Import a tab-separated attendance report exported from a fingerprint device.

    Expected columns (with a header row): ID, Name, Dept., Time, Device ID.
    Each non-header row is validated against members.fp_user_id; if any row's ID
    does not match a member, the whole upload is rejected with the offending rows.
    Otherwise rows are mapped to member_id and inserted into `attendance`,
    skipping any (member, day) combinations that already exist for the chosen
    activity type.
    """
    activity = db.get(ActivityType, activity_type_id)
    if not activity or not activity.is_active:
        raise HTTPException(status_code=404, detail="Activity type not found or inactive")

    raw = file.file.read()
    try:
        text_content = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            text_content = raw.decode("utf-16")
        except UnicodeDecodeError:
            text_content = raw.decode("latin-1", errors="replace")

    lines = [ln for ln in text_content.splitlines() if ln.strip()]
    if not lines:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    # Skip header row (first line contains "ID" / "Name" labels)
    has_header = "\t" in lines[0] and any(
        h.strip().lower() in {"id", "name", "time"} for h in lines[0].split("\t")
    )
    data_lines = lines[1:] if has_header else lines
    base_row = 2 if has_header else 1

    parse_errors: list[dict] = []
    parsed: list[dict] = []
    for offset, line in enumerate(data_lines):
        row_no = offset + base_row
        parts = line.split("\t")
        if len(parts) < 4:
            parse_errors.append({"row": row_no, "reason": "not enough columns", "raw": line})
            continue
        id_str = parts[0].strip()
        name = parts[1].strip() if len(parts) > 1 else ""
        time_str = " ".join(parts[3].split())
        try:
            fp_id = int(id_str)
        except ValueError:
            parse_errors.append({"row": row_no, "reason": f"invalid ID '{id_str}'", "name": name})
            continue
        try:
            ts = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            parse_errors.append({"row": row_no, "reason": f"invalid time '{parts[3]}'", "name": name})
            continue
        parsed.append({"row": row_no, "fp_id": fp_id, "name": name, "ts": ts})

    if parse_errors:
        raise HTTPException(status_code=400, detail={
            "message": "Some rows could not be parsed",
            "errors": parse_errors,
        })
    if not parsed:
        raise HTTPException(status_code=400, detail="No data rows found in file")

    fp_ids = list({r["fp_id"] for r in parsed})
    rows = db.query(Member.id, Member.fp_user_id).filter(Member.fp_user_id.in_(fp_ids)).all()
    fp_to_member = {fp: mid for mid, fp in rows}

    invalid = [
        {"row": r["row"], "fp_user_id": r["fp_id"], "name": r["name"]}
        for r in parsed if r["fp_id"] not in fp_to_member
    ]
    if invalid:
        raise HTTPException(status_code=400, detail={
            "message": "Some IDs were not found in members",
            "invalid": invalid,
        })

    member_ids = list({fp_to_member[r["fp_id"]] for r in parsed})
    dates = list({r["ts"].date() for r in parsed})
    existing = db.query(
        Attendance.member_id,
        func.date(Attendance.timestamp),
    ).filter(
        Attendance.activity_type_id == activity_type_id,
        Attendance.member_id.in_(member_ids),
        func.date(Attendance.timestamp).in_(dates),
    ).all()
    existing_pairs = {(mid, d) for mid, d in existing}

    inserted = 0
    skipped = 0
    seen: set[tuple[int, date]] = set()
    for r in parsed:
        member_id = fp_to_member[r["fp_id"]]
        d = r["ts"].date()
        pair = (member_id, d)
        if pair in existing_pairs or pair in seen:
            skipped += 1
            continue
        seen.add(pair)
        db.add(Attendance(
            member_id=member_id,
            activity_type_id=activity_type_id,
            timestamp=r["ts"],
        ))
        inserted += 1

    db.commit()
    return {"inserted": inserted, "skipped": skipped, "total": len(parsed)}

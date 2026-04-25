"""
AI-HRMS — Attendance service layer.
All DB operations are tenant-scoped.
"""

from __future__ import annotations

import logging
from datetime  import date, datetime, timedelta, time as dtime
from typing    import Optional

from fastapi            import HTTPException, status
from sqlalchemy         import select, func, and_, or_, update
from sqlalchemy.orm     import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    AttendanceAdjustment,
    AttendanceRecord,
    Employee,
    LeaveRequest,
    PublicHoliday,
    Shift,
)
from app.api.v1.attendance.schemas import (
    AdjustmentReviewRequest,
    AdjustmentStatus,
    AttendanceAdjustmentRequest,
    AttendanceCheckInRequest,
    AttendanceCheckOutRequest,
    AttendanceFilterParams,
    AttendanceManualEntryRequest,
    AttendanceRecordListItem,
    AttendanceSummary,
    AttendanceStatus,
    CheckInSource,
    LiveAttendanceEntry,
    ShiftCreate,
    ShiftUpdate,
    TimesheetResponse,
    TimesheetRow,
)

logger = logging.getLogger(__name__)

# Default shift when none is assigned
_DEFAULT_SHIFT_START = dtime(9, 0, 0)
_DEFAULT_SHIFT_END   = dtime(17, 0, 0)
_DEFAULT_GRACE       = 15   # minutes
_DEFAULT_HOURS       = 8.0


# ─────────────────────────────────────────────────────────────────────────────
# Shifts
# ─────────────────────────────────────────────────────────────────────────────

async def get_shifts(tenant_id: str, db: AsyncSession) -> list[Shift]:
    rows = await db.execute(
        select(Shift)
        .where(Shift.tenant_id == tenant_id)
        .order_by(Shift.name)
    )
    return rows.scalars().all()


async def create_shift(
    tenant_id: str, data: ShiftCreate, db: AsyncSession
) -> Shift:
    from datetime import datetime as _dt

    s = _dt.combine(_dt.today(), data.start_time)
    e = _dt.combine(_dt.today(), data.end_time)
    total_hrs = (e - s).total_seconds() / 3600

    shift = Shift(
        tenant_id            = tenant_id,
        name                 = data.name,
        start_time           = data.start_time,
        end_time             = data.end_time,
        grace_period_minutes = data.grace_period_minutes,
        total_hours          = round(total_hrs, 2),
        is_active            = data.is_active,
    )
    db.add(shift)
    await db.flush()
    await db.refresh(shift)
    await db.commit()
    return shift


async def update_shift(
    tenant_id: str, shift_id: str, data: ShiftUpdate, db: AsyncSession
) -> Shift:
    row = await db.execute(
        select(Shift).where(Shift.id == shift_id, Shift.tenant_id == tenant_id)
    )
    shift = row.scalar_one_or_none()
    if not shift:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Shift not found.")

    update_data = data.model_dump(exclude_none=True)
    if "start_time" in update_data or "end_time" in update_data:
        from datetime import datetime as _dt
        st = update_data.get("start_time", shift.start_time)
        et = update_data.get("end_time",   shift.end_time)
        s  = _dt.combine(_dt.today(), st)
        e  = _dt.combine(_dt.today(), et)
        update_data["total_hours"] = round((e - s).total_seconds() / 3600, 2)

    for k, v in update_data.items():
        setattr(shift, k, v)

    await db.commit()
    await db.refresh(shift)
    return shift


# ─────────────────────────────────────────────────────────────────────────────
# Helper: get employee's effective shift
# ─────────────────────────────────────────────────────────────────────────────

async def _get_employee_shift(
    employee: Employee, tenant_id: str, db: AsyncSession
) -> tuple[dtime, dtime, int, float, Optional[str]]:
    """Return (start_time, end_time, grace_minutes, total_hours, shift_id)."""
    if employee.shift_id:
        row = await db.execute(
            select(Shift).where(
                Shift.id        == employee.shift_id,
                Shift.tenant_id == tenant_id,
                Shift.is_active.is_(True),
            )
        )
        shift = row.scalar_one_or_none()
        if shift:
            return (
                shift.start_time,
                shift.end_time,
                shift.grace_period_minutes,
                shift.total_hours,
                str(shift.id),
            )
    return (_DEFAULT_SHIFT_START, _DEFAULT_SHIFT_END, _DEFAULT_GRACE, _DEFAULT_HOURS, None)


# ─────────────────────────────────────────────────────────────────────────────
# Check-in / Check-out
# ─────────────────────────────────────────────────────────────────────────────

async def check_in(
    tenant_id:   str,
    employee_id: str,
    data:        AttendanceCheckInRequest,
    db:          AsyncSession,
) -> AttendanceRecord:
    today = date.today()

    # Idempotency: no duplicate check-in on same day
    existing = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.tenant_id   == tenant_id,
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date        == today,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You are already checked in today. Please check out first.",
        )

    # Load employee + shift
    emp_row = await db.execute(
        select(Employee).where(
            Employee.id        == employee_id,
            Employee.tenant_id == tenant_id,
        )
    )
    emp = emp_row.scalar_one_or_none()
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found.")

    shift_start, shift_end, grace, total_shift_hours, shift_id = \
        await _get_employee_shift(emp, tenant_id, db)

    now = datetime.utcnow()

    # Determine status: late if check-in is > grace period after shift start
    deadline = datetime.combine(today, shift_start) + timedelta(minutes=grace)
    att_status = AttendanceStatus.late if now > deadline else AttendanceStatus.present

    record = AttendanceRecord(
        tenant_id         = tenant_id,
        employee_id       = employee_id,
        date              = today,
        check_in          = now,
        status            = att_status,
        source            = data.source,
        location_lat      = data.location.lat      if data.location else None,
        location_lng      = data.location.lng      if data.location else None,
        location_address  = data.location.address  if data.location else None,
        notes             = data.notes,
        is_manual         = (data.source == CheckInSource.manual),
        shift_id          = shift_id,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    # Eager-load employee relation for broadcast
    await db.refresh(emp)
    record.employee = emp  # type: ignore[attr-defined]

    await db.commit()

    # Broadcast to WebSocket
    await _broadcast_attendance_event(record, "check_in", tenant_id)

    # Late arrival notification
    if att_status == AttendanceStatus.late:
        minutes_late = int((now - deadline).total_seconds() / 60)
        from app.tasks.attendance_tasks import send_late_arrival_alert
        send_late_arrival_alert.delay(employee_id, minutes_late)

    return record


async def check_out(
    tenant_id:   str,
    employee_id: str,
    data:        AttendanceCheckOutRequest,
    db:          AsyncSession,
) -> AttendanceRecord:
    today = date.today()

    # Find today's open record
    row = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.tenant_id   == tenant_id,
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date        == today,
            AttendanceRecord.check_in.isnot(None),
            AttendanceRecord.check_out.is_(None),
        ).options(selectinload(AttendanceRecord.employee))
    )
    record = row.scalar_one_or_none()
    if not record:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No active check-in found for today. Please check in first.",
        )

    now = datetime.utcnow()
    record.check_out = now

    # Calculate working hours (subtract 1h break if > 6 hours)
    elapsed_hours = (now - record.check_in).total_seconds() / 3600
    break_hours   = 1.0 if elapsed_hours > 6 else 0.0
    working_hours = max(elapsed_hours - break_hours, 0.0)
    record.working_hours = round(working_hours, 2)

    # Get shift to calculate overtime
    emp_row = await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )
    emp = emp_row.scalar_one_or_none()
    _, _, _, total_shift_hours, _ = await _get_employee_shift(
        emp, tenant_id, db
    ) if emp else (None, None, None, _DEFAULT_HOURS, None)

    overtime = max(working_hours - total_shift_hours, 0.0)
    record.overtime_hours = round(overtime, 2)

    # Downgrade to half_day if working < half shift
    if working_hours < (total_shift_hours / 2):
        record.status = AttendanceStatus.half_day

    if data.notes:
        record.notes = (record.notes or "") + f" | Checkout note: {data.notes}"

    await db.commit()
    await db.refresh(record)

    # Broadcast
    await _broadcast_attendance_event(record, "check_out", tenant_id)

    return record


# ─────────────────────────────────────────────────────────────────────────────
# Manual entry & adjustments
# ─────────────────────────────────────────────────────────────────────────────

async def manual_entry(
    tenant_id:  str,
    data:       AttendanceManualEntryRequest,
    created_by: str,
    db:         AsyncSession,
) -> AttendanceRecord:
    # Check for existing record on same date
    existing = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.tenant_id   == tenant_id,
            AttendanceRecord.employee_id == data.employee_id,
            AttendanceRecord.date        == data.date,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"An attendance record already exists for {data.date}.",
        )

    # Calculate hours
    working_hours = None
    overtime_hours = None
    if data.check_out:
        elapsed = (data.check_out - data.check_in).total_seconds() / 3600
        break_h = 1.0 if elapsed > 6 else 0.0
        working_hours = round(max(elapsed - break_h, 0.0), 2)

        emp_row = await db.execute(select(Employee).where(Employee.id == data.employee_id))
        emp = emp_row.scalar_one_or_none()
        if emp:
            _, _, _, shift_hours, _ = await _get_employee_shift(emp, tenant_id, db)
        else:
            shift_hours = _DEFAULT_HOURS
        overtime_hours = round(max(working_hours - shift_hours, 0.0), 2)

    # Determine check-in shift for status
    emp_row2 = await db.execute(select(Employee).where(Employee.id == data.employee_id))
    emp2 = emp_row2.scalar_one_or_none()
    if emp2:
        shift_start, _, grace, _, shift_id = await _get_employee_shift(emp2, tenant_id, db)
        deadline = datetime.combine(data.date, shift_start) + timedelta(minutes=grace)
        att_status = AttendanceStatus.late if data.check_in > deadline else AttendanceStatus.present
    else:
        att_status, shift_id = AttendanceStatus.present, None

    record = AttendanceRecord(
        tenant_id      = tenant_id,
        employee_id    = data.employee_id,
        date           = data.date,
        check_in       = data.check_in,
        check_out      = data.check_out,
        working_hours  = working_hours,
        overtime_hours = overtime_hours,
        status         = att_status,
        source         = CheckInSource.manual,
        is_manual      = True,
        notes          = f"Manual entry reason: {data.reason}",
        shift_id       = shift_id,
        created_by     = created_by,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    await db.commit()
    return record


async def request_adjustment(
    tenant_id:   str,
    employee_id: str,
    data:        AttendanceAdjustmentRequest,
    db:          AsyncSession,
) -> AttendanceAdjustment:
    # Load the original record
    rec_row = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.id        == data.attendance_id,
            AttendanceRecord.tenant_id == tenant_id,
        )
    )
    rec = rec_row.scalar_one_or_none()
    if not rec:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Attendance record not found.")

    if str(rec.employee_id) != employee_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only adjust your own records.")

    adj = AttendanceAdjustment(
        tenant_id           = tenant_id,
        attendance_id       = data.attendance_id,
        employee_id         = employee_id,
        original_check_in   = rec.check_in,
        original_check_out  = rec.check_out,
        requested_check_in  = data.new_check_in,
        requested_check_out = data.new_check_out,
        reason              = data.reason,
        status              = AdjustmentStatus.pending,
    )
    db.add(adj)
    await db.flush()
    await db.refresh(adj)
    await db.commit()
    return adj


async def review_adjustment(
    tenant_id:     str,
    adjustment_id: str,
    reviewed_by:   str,
    payload:       AdjustmentReviewRequest,
    db:            AsyncSession,
) -> AttendanceAdjustment:
    row = await db.execute(
        select(AttendanceAdjustment).where(
            AttendanceAdjustment.id        == adjustment_id,
            AttendanceAdjustment.tenant_id == tenant_id,
        )
    )
    adj = row.scalar_one_or_none()
    if not adj:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Adjustment not found.")

    if adj.status != AdjustmentStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Adjustment already reviewed.")

    adj.status      = AdjustmentStatus.approved if payload.action == "approve" else AdjustmentStatus.rejected
    adj.reviewed_by = reviewed_by
    adj.review_note = payload.review_note
    adj.reviewed_at = datetime.utcnow()

    if payload.action == "approve":
        # Update the attendance record
        rec_row = await db.execute(
            select(AttendanceRecord).where(AttendanceRecord.id == adj.attendance_id)
        )
        rec = rec_row.scalar_one_or_none()
        if rec:
            rec.check_in  = adj.requested_check_in
            rec.check_out = adj.requested_check_out

            if rec.check_in and rec.check_out:
                elapsed = (rec.check_out - rec.check_in).total_seconds() / 3600
                break_h = 1.0 if elapsed > 6 else 0.0
                rec.working_hours  = round(max(elapsed - break_h, 0.0), 2)

                emp_row = await db.execute(select(Employee).where(Employee.id == rec.employee_id))
                emp = emp_row.scalar_one_or_none()
                _, _, _, shift_hours, _ = (
                    await _get_employee_shift(emp, tenant_id, db)
                    if emp else (None, None, None, _DEFAULT_HOURS, None)
                )
                rec.overtime_hours = round(max(rec.working_hours - shift_hours, 0.0), 2)

    await db.commit()
    await db.refresh(adj)
    return adj


# ─────────────────────────────────────────────────────────────────────────────
# Queries
# ─────────────────────────────────────────────────────────────────────────────

async def get_attendance_records(
    tenant_id: str,
    filters:   AttendanceFilterParams,
    db:        AsyncSession,
) -> dict:
    q = (
        select(AttendanceRecord)
        .join(Employee, Employee.id == AttendanceRecord.employee_id)
        .where(AttendanceRecord.tenant_id == tenant_id)
        .options(selectinload(AttendanceRecord.employee))
    )

    if filters.employee_id:
        q = q.where(AttendanceRecord.employee_id == filters.employee_id)
    if filters.department_id:
        q = q.where(Employee.department_id == filters.department_id)
    if filters.date:
        q = q.where(AttendanceRecord.date == filters.date)
    if filters.date_from:
        q = q.where(AttendanceRecord.date >= filters.date_from)
    if filters.date_to:
        q = q.where(AttendanceRecord.date <= filters.date_to)
    if filters.status:
        q = q.where(AttendanceRecord.status == filters.status)
    if filters.source:
        q = q.where(AttendanceRecord.source == filters.source)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    offset = (filters.page - 1) * filters.page_size
    rows   = await db.execute(
        q.order_by(AttendanceRecord.date.desc(), AttendanceRecord.check_in.desc())
        .offset(offset).limit(filters.page_size)
    )
    records = rows.scalars().all()

    items = [
        AttendanceRecordListItem(
            id             = str(r.id),
            employee_id    = str(r.employee_id),
            employee_name  = f"{r.employee.first_name} {r.employee.last_name}",
            employee_code  = r.employee.employee_code,
            department_name = None,
            date           = r.date,
            check_in       = r.check_in,
            check_out      = r.check_out,
            working_hours  = r.working_hours,
            overtime_hours = r.overtime_hours,
            status         = r.status,
            source         = r.source,
            is_manual      = r.is_manual,
        )
        for r in records
    ]
    return {"count": total, "results": items}


async def get_today_attendance(
    tenant_id: str, db: AsyncSession
) -> list[LiveAttendanceEntry]:
    today = date.today()
    rows  = await db.execute(
        select(AttendanceRecord)
        .join(Employee, Employee.id == AttendanceRecord.employee_id)
        .where(
            AttendanceRecord.tenant_id == tenant_id,
            AttendanceRecord.date      == today,
            AttendanceRecord.check_in.isnot(None),
        )
        .options(selectinload(AttendanceRecord.employee))
        .order_by(AttendanceRecord.check_in.desc())
    )
    records = rows.scalars().all()

    return [
        LiveAttendanceEntry(
            employee_id     = str(r.employee_id),
            employee_name   = f"{r.employee.first_name} {r.employee.last_name}",
            photo_url       = r.employee.photo_url,
            department_name = None,
            action          = "check_out" if r.check_out else "check_in",
            time            = r.check_in,
            check_in_time   = r.check_in,
            status          = r.status,
        )
        for r in records
    ]


async def get_today_record(
    tenant_id: str, employee_id: str, db: AsyncSession
) -> Optional[AttendanceRecord]:
    row = await db.execute(
        select(AttendanceRecord)
        .where(
            AttendanceRecord.tenant_id   == tenant_id,
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date        == date.today(),
        )
        .options(selectinload(AttendanceRecord.employee))
    )
    return row.scalar_one_or_none()


async def get_pending_adjustments(
    tenant_id: str, db: AsyncSession
) -> list[AttendanceAdjustment]:
    rows = await db.execute(
        select(AttendanceAdjustment).where(
            AttendanceAdjustment.tenant_id == tenant_id,
            AttendanceAdjustment.status    == AdjustmentStatus.pending,
        ).order_by(AttendanceAdjustment.created_at.desc())
    )
    return rows.scalars().all()


async def get_my_adjustments(
    tenant_id: str, employee_id: str, db: AsyncSession
) -> list[AttendanceAdjustment]:
    rows = await db.execute(
        select(AttendanceAdjustment).where(
            AttendanceAdjustment.tenant_id   == tenant_id,
            AttendanceAdjustment.employee_id == employee_id,
        ).order_by(AttendanceAdjustment.created_at.desc())
    )
    return rows.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# Summary & Timesheet
# ─────────────────────────────────────────────────────────────────────────────

async def get_attendance_summary(
    tenant_id:   str,
    employee_id: str,
    month:       int,
    year:        int,
    db:          AsyncSession,
) -> AttendanceSummary:
    from calendar import monthrange

    emp_row = await db.execute(
        select(Employee).where(
            Employee.id == employee_id, Employee.tenant_id == tenant_id
        )
    )
    emp = emp_row.scalar_one_or_none()
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found.")

    first_day = date(year, month, 1)
    last_day  = date(year, month, monthrange(year, month)[1])

    # Total working days (weekdays in month)
    total_wd = sum(
        1 for d in range(1, last_day.day + 1)
        if date(year, month, d).weekday() < 5
    )

    # Query records
    rows = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.tenant_id   == tenant_id,
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date.between(first_day, last_day),
        )
    )
    records = rows.scalars().all()

    counts = {s: 0 for s in AttendanceStatus}
    for r in records:
        counts[r.status] = counts.get(r.status, 0) + 1

    total_hours = sum(r.working_hours or 0 for r in records)
    overtime    = sum(r.overtime_hours or 0 for r in records)
    present_total = counts[AttendanceStatus.present] + counts[AttendanceStatus.late] + counts[AttendanceStatus.half_day]
    pct = round((present_total / total_wd * 100) if total_wd else 0, 1)

    return AttendanceSummary(
        employee_id           = employee_id,
        employee_name         = f"{emp.first_name} {emp.last_name}",
        month                 = month,
        year                  = year,
        total_working_days    = total_wd,
        present_days          = counts[AttendanceStatus.present],
        absent_days           = counts[AttendanceStatus.absent],
        late_days             = counts[AttendanceStatus.late],
        half_days             = counts[AttendanceStatus.half_day],
        leave_days            = counts[AttendanceStatus.on_leave],
        holiday_days          = counts[AttendanceStatus.holiday],
        total_working_hours   = round(total_hours, 2),
        total_overtime_hours  = round(overtime, 2),
        attendance_percentage = pct,
    )


async def get_monthly_timesheet(
    tenant_id:   str,
    employee_id: str,
    month:       int,
    year:        int,
    db:          AsyncSession,
) -> TimesheetResponse:
    from calendar import monthrange, day_name

    emp_row = await db.execute(
        select(Employee).where(
            Employee.id == employee_id, Employee.tenant_id == tenant_id
        )
    )
    emp = emp_row.scalar_one_or_none()
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found.")

    last_day_num = monthrange(year, month)[1]
    first_day    = date(year, month, 1)
    last_day     = date(year, month, last_day_num)

    # Fetch attendance records
    rec_rows = await db.execute(
        select(AttendanceRecord).where(
            AttendanceRecord.tenant_id   == tenant_id,
            AttendanceRecord.employee_id == employee_id,
            AttendanceRecord.date.between(first_day, last_day),
        )
    )
    records_by_date: dict[date, AttendanceRecord] = {
        r.date: r for r in rec_rows.scalars().all()
    }

    # Fetch public holidays in month
    ph_rows = await db.execute(
        select(PublicHoliday).where(
            PublicHoliday.tenant_id == tenant_id,
            or_(
                PublicHoliday.date.between(first_day, last_day),
                PublicHoliday.is_recurring.is_(True),
            ),
        )
    )
    holidays_map: dict[date, str] = {}
    for h in ph_rows.scalars().all():
        h_date = h.date.replace(year=year) if h.is_recurring else h.date
        if first_day <= h_date <= last_day:
            holidays_map[h_date] = h.name

    rows: list[TimesheetRow] = []
    total_hours   = 0.0
    total_ot      = 0.0
    present_count = 0

    for day_num in range(1, last_day_num + 1):
        d        = date(year, month, day_num)
        is_wknd  = d.weekday() >= 5
        is_hol   = d in holidays_map
        rec      = records_by_date.get(d)

        if rec:
            status_val = rec.status
            w_hrs      = rec.working_hours
            ot_hrs     = rec.overtime_hours
            att_id     = str(rec.id)
            total_hours += w_hrs or 0
            total_ot    += ot_hrs or 0
            if status_val in (AttendanceStatus.present, AttendanceStatus.late, AttendanceStatus.half_day):
                present_count += 1
        elif is_wknd:
            status_val = AttendanceStatus.weekend
            w_hrs = ot_hrs = None
            att_id = None
        elif is_hol:
            status_val = AttendanceStatus.holiday
            w_hrs = ot_hrs = None
            att_id = None
        else:
            status_val = AttendanceStatus.absent
            w_hrs = ot_hrs = None
            att_id = None

        rows.append(TimesheetRow(
            date           = d,
            day_name       = day_name[d.weekday()],
            check_in       = rec.check_in       if rec else None,
            check_out      = rec.check_out      if rec else None,
            working_hours  = w_hrs,
            overtime_hours = ot_hrs,
            status         = status_val,
            is_weekend     = is_wknd,
            is_holiday     = is_hol,
            holiday_name   = holidays_map.get(d),
            notes          = rec.notes          if rec else None,
            attendance_id  = att_id,
        ))

    return TimesheetResponse(
        employee_id          = employee_id,
        employee_name        = f"{emp.first_name} {emp.last_name}",
        month                = month,
        year                 = year,
        rows                 = rows,
        total_working_hours  = round(total_hours, 2),
        total_overtime_hours = round(total_ot, 2),
        total_present_days   = present_count,
    )


# ─────────────────────────────────────────────────────────────────────────────
# WebSocket broadcast helper
# ─────────────────────────────────────────────────────────────────────────────

async def _broadcast_attendance_event(
    record: AttendanceRecord, action: str, tenant_id: str
) -> None:
    try:
        from app.core.websocket_manager import manager
        emp = getattr(record, "employee", None)
        await manager.broadcast_to_tenant(tenant_id, {
            "type":            "attendance",
            "employee_id":     str(record.employee_id),
            "employee_name":   f"{emp.first_name} {emp.last_name}" if emp else "Unknown",
            "photo_url":       emp.photo_url if emp else None,
            "department_name": None,
            "action":          action,
            "time":            record.check_in.isoformat() if action == "check_in" else record.check_out.isoformat(),
            "check_in_time":   record.check_in.isoformat() if record.check_in else None,
            "status":          record.status,
        })
    except Exception as exc:
        logger.warning("WS broadcast failed (non-critical): %s", exc)

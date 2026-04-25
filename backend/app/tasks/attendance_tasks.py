"""
AI-HRMS — Attendance module Celery tasks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime

from celery import shared_task

logger = logging.getLogger(__name__)


# ─── Mark daily absences (Celery beat: 11:59 PM daily) ───────────────────────

@shared_task(name="attendance.mark_daily_absences")
def mark_daily_absences(tenant_id: str, target_date: str | None = None) -> dict:
    """
    For all active employees who have no attendance record today and no
    approved leave, create an ABSENT record.
    Runs at 23:59 each day via Celery beat.
    """

    async def _run() -> dict:
        from sqlalchemy import select as _select, and_ as _and
        from app.core.database import AsyncSessionLocal
        from app.models import AttendanceRecord, Employee, LeaveRequest

        check_date = (
            date.fromisoformat(target_date) if target_date else date.today()
        )
        # Skip weekends
        if check_date.weekday() >= 5:
            return {"skipped": "weekend", "date": str(check_date)}

        marked = 0
        async with AsyncSessionLocal() as db:
            # Active employees for this tenant
            emp_rows = await db.execute(
                _select(Employee).where(
                    Employee.tenant_id        == tenant_id,
                    Employee.employment_status == "active",
                )
            )
            employees = emp_rows.scalars().all()

            for emp in employees:
                # Already have a record?
                existing = await db.execute(
                    _select(AttendanceRecord).where(
                        _and(
                            AttendanceRecord.tenant_id   == tenant_id,
                            AttendanceRecord.employee_id == emp.id,
                            AttendanceRecord.date        == check_date,
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Has approved leave?
                on_leave = await db.execute(
                    _select(LeaveRequest).where(
                        _and(
                            LeaveRequest.tenant_id   == tenant_id,
                            LeaveRequest.employee_id == emp.id,
                            LeaveRequest.status      == "approved",
                            LeaveRequest.start_date  <= check_date,
                            LeaveRequest.end_date    >= check_date,
                        )
                    )
                )
                if on_leave.scalar_one_or_none():
                    # Mark as on_leave instead
                    db.add(AttendanceRecord(
                        tenant_id   = tenant_id,
                        employee_id = str(emp.id),
                        date        = check_date,
                        status      = "on_leave",
                        source      = "manual",
                        is_manual   = True,
                    ))
                else:
                    db.add(AttendanceRecord(
                        tenant_id   = tenant_id,
                        employee_id = str(emp.id),
                        date        = check_date,
                        status      = "absent",
                        source      = "manual",
                        is_manual   = True,
                    ))
                marked += 1

            await db.commit()

        logger.info("mark_daily_absences: tenant=%s date=%s marked=%d", tenant_id, check_date, marked)
        return {"marked": marked, "date": str(check_date)}

    return asyncio.run(_run())


# ─── Late arrival alert ───────────────────────────────────────────────────────

@shared_task(name="attendance.send_late_arrival_alert", bind=True, max_retries=2)
def send_late_arrival_alert(self, employee_id: str, minutes_late: int) -> None:
    """Notify the employee's manager about a late arrival."""

    async def _run() -> None:
        from sqlalchemy import select as _select
        from app.core.database import AsyncSessionLocal
        from app.models import Employee, Notification
        from app.core.config import settings

        async with AsyncSessionLocal() as db:
            emp_row = await db.execute(
                _select(Employee).where(Employee.id == employee_id)
            )
            emp = emp_row.scalar_one_or_none()
            if not emp or not emp.manager_id:
                return

            # Get manager employee
            mgr_row = await db.execute(
                _select(Employee).where(Employee.id == emp.manager_id)
            )
            mgr = mgr_row.scalar_one_or_none()
            if not mgr or not mgr.user_id:
                return

            db.add(Notification(
                tenant_id = emp.tenant_id,
                user_id   = str(mgr.user_id),
                title     = "Late Arrival Alert",
                message   = (
                    f"{emp.first_name} {emp.last_name} arrived "
                    f"{minutes_late} minute(s) late today."
                ),
                category      = "attendance",
                reference_id  = str(emp.id),
                reference_type = "employee",
            ))
            await db.commit()
            logger.info("Late alert sent for employee %s (%d min late)", employee_id, minutes_late)

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.exception("send_late_arrival_alert failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


# ─── Monthly attendance report (on-demand / Celery beat) ─────────────────────

@shared_task(name="attendance.generate_monthly_attendance_report")
def generate_monthly_attendance_report(
    tenant_id: str, month: int, year: int
) -> dict:
    """
    Aggregate monthly attendance stats per department and save/email as report.
    Returns a summary dict; in production, this would email the HR team.
    """

    async def _run() -> dict:
        from sqlalchemy import select as _select, func as _func
        from app.core.database import AsyncSessionLocal
        from app.models import AttendanceRecord, Employee, Department
        from datetime import date as _date, timedelta as _td

        # Date range
        first_day = _date(year, month, 1)
        if month == 12:
            last_day = _date(year + 1, 1, 1) - _td(days=1)
        else:
            last_day = _date(year, month + 1, 1) - _td(days=1)

        async with AsyncSessionLocal() as db:
            # Count by status grouped by dept
            rows = await db.execute(
                _select(
                    Department.name,
                    AttendanceRecord.status,
                    _func.count(AttendanceRecord.id).label("cnt"),
                )
                .join(Employee,     Employee.id            == AttendanceRecord.employee_id)
                .join(Department,   Department.id          == Employee.department_id)
                .where(
                    AttendanceRecord.tenant_id == tenant_id,
                    AttendanceRecord.date.between(first_day, last_day),
                )
                .group_by(Department.name, AttendanceRecord.status)
            )

            summary: dict[str, dict] = {}
            for dept_name, status, cnt in rows:
                if dept_name not in summary:
                    summary[dept_name] = {}
                summary[dept_name][status] = cnt

        logger.info(
            "Monthly report generated: tenant=%s %d/%d", tenant_id, month, year
        )
        return {"month": month, "year": year, "departments": summary}

    return asyncio.run(_run())

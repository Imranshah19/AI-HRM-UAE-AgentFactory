"""
AI-HRMS — Reports & Analytics service layer.
All queries are tenant-scoped.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, timedelta, timezone
from typing   import Any, Optional
from uuid     import UUID

from sqlalchemy           import and_, case, cast, extract, func, or_, select, text
from sqlalchemy.types     import Integer as SAInt
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.employee    import Department, Designation, Employee
from app.models.attendance  import AttendanceRecord
from app.models.leave       import LeaveRequest, LeaveType
from app.models.payroll     import PayrollRun, PayrollRecord
from app.models.recruitment import JobPosting, JobApplication
from app.api.v1.reports.schemas import (
    AttendanceReport,
    DashboardStats,
    DeptAttendance,
    DeptHeadcount,
    HeadcountReport,
    LeaveByType,
    LeaveDeptRow,
    LeaveReport,
    PayrollMonth,
    PayrollReport,
    RecruitmentReport,
    TurnoverMonth,
    TurnoverReport,
    UpcomingBirthday,
)

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

async def get_dashboard_stats(tenant_id: UUID, db: AsyncSession) -> DashboardStats:
    today = date.today()

    # Total active employees
    total_employees = (await db.execute(
        select(func.count(Employee.id)).where(
            Employee.tenant_id         == tenant_id,
            Employee.employment_status == "active",
        )
    )).scalar_one()

    # Present today
    present_today = (await db.execute(
        select(func.count(AttendanceRecord.id)).where(
            AttendanceRecord.date      == today,
            AttendanceRecord.status.in_(["present", "late", "half_day"]),
            AttendanceRecord.employee_id.in_(
                select(Employee.id).where(
                    Employee.tenant_id         == tenant_id,
                    Employee.employment_status == "active",
                )
            ),
        )
    )).scalar_one()

    # Pending leave requests
    pending_leaves = (await db.execute(
        select(func.count(LeaveRequest.id)).where(
            LeaveRequest.tenant_id == tenant_id,
            LeaveRequest.status    == "pending",
        )
    )).scalar_one()

    # Open job positions
    open_positions = (await db.execute(
        select(func.count(JobPosting.id)).where(
            JobPosting.tenant_id == tenant_id,
            JobPosting.status    == "open",
        )
    )).scalar_one()

    # Payroll due this month? (no completed run for current month)
    current_run = (await db.execute(
        select(PayrollRun.id).where(
            PayrollRun.tenant_id == tenant_id,
            PayrollRun.month     == today.month,
            PayrollRun.year      == today.year,
            PayrollRun.status.in_(["approved", "paid"]),
        ).limit(1)
    )).scalar_one_or_none()
    payroll_due = current_run is None

    # Upcoming birthdays (next 30 days)
    upcoming_birthdays: list[UpcomingBirthday] = []
    try:
        employees = (await db.execute(
            select(Employee)
            .where(
                Employee.tenant_id         == tenant_id,
                Employee.employment_status == "active",
                Employee.date_of_birth     != None,
            )
            .limit(200)
        )).scalars().all()

        for emp in employees:
            if not emp.date_of_birth:
                continue
            dob = emp.date_of_birth
            # Birthday this year
            try:
                birthday_this_year = date(today.year, dob.month, dob.day)
            except ValueError:
                continue  # Feb 29 edge case

            days_until = (birthday_this_year - today).days
            if days_until < 0:
                # Birthday already passed → check next year
                try:
                    birthday_this_year = date(today.year + 1, dob.month, dob.day)
                except ValueError:
                    continue
                days_until = (birthday_this_year - today).days

            if 0 <= days_until <= 30:
                upcoming_birthdays.append(UpcomingBirthday(
                    employee_id = str(emp.id),
                    full_name   = f"{emp.first_name} {emp.last_name}",
                    birthday    = dob.strftime("%m-%d"),
                    days_until  = days_until,
                    department  = None,
                ))
        upcoming_birthdays.sort(key=lambda x: x.days_until)
    except Exception:
        pass

    return DashboardStats(
        total_employees    = total_employees,
        present_today      = present_today,
        pending_leaves     = pending_leaves,
        open_positions     = open_positions,
        payroll_due        = payroll_due,
        upcoming_birthdays = upcoming_birthdays[:10],
    )


# ─── Headcount Report ─────────────────────────────────────────────────────────

async def get_headcount_report(tenant_id: UUID, db: AsyncSession) -> HeadcountReport:
    total = (await db.execute(
        select(func.count(Employee.id)).where(
            Employee.tenant_id         == tenant_id,
            Employee.employment_status == "active",
        )
    )).scalar_one()

    # By department
    dept_rows = (await db.execute(
        select(Department.name, func.count(Employee.id).label("count"))
        .join(Employee, Employee.department_id == Department.id, isouter=True)
        .where(
            Department.tenant_id       == tenant_id,
            Employee.employment_status == "active",
        )
        .group_by(Department.name)
        .order_by(func.count(Employee.id).desc())
    )).all()

    by_department = [
        DeptHeadcount(
            department = row.name,
            count      = row.count,
            percentage = round(row.count / total * 100, 1) if total else 0,
        )
        for row in dept_rows
    ]

    # By contract type
    contract_rows = (await db.execute(
        select(Employee.contract_type, func.count(Employee.id).label("count"))
        .where(
            Employee.tenant_id         == tenant_id,
            Employee.employment_status == "active",
        )
        .group_by(Employee.contract_type)
    )).all()
    by_contract_type = [
        {"contract_type": r.contract_type or "unknown", "count": r.count}
        for r in contract_rows
    ]

    # By gender
    gender_rows = (await db.execute(
        select(Employee.gender, func.count(Employee.id).label("count"))
        .where(
            Employee.tenant_id         == tenant_id,
            Employee.employment_status == "active",
        )
        .group_by(Employee.gender)
    )).all()
    by_gender = [
        {"gender": r.gender or "not_specified", "count": r.count}
        for r in gender_rows
    ]

    # By employment status
    status_rows = (await db.execute(
        select(Employee.employment_status, func.count(Employee.id).label("count"))
        .where(Employee.tenant_id == tenant_id)
        .group_by(Employee.employment_status)
    )).all()
    by_status = [{"status": r.employment_status, "count": r.count} for r in status_rows]

    return HeadcountReport(
        total            = total,
        by_department    = by_department,
        by_contract_type = by_contract_type,
        by_gender        = by_gender,
        by_status        = by_status,
    )


# ─── Turnover Report ──────────────────────────────────────────────────────────

async def get_turnover_report(tenant_id: UUID, year: int, db: AsyncSession) -> TurnoverReport:
    months_data: list[TurnoverMonth] = []

    for month_num in range(1, 13):
        _, last_day = calendar.monthrange(year, month_num)
        month_start = date(year, month_num, 1)
        month_end   = date(year, month_num, last_day)

        resignations = (await db.execute(
            select(func.count(Employee.id)).where(
                Employee.tenant_id             == tenant_id,
                Employee.separation_type       == "resignation",
                Employee.separation_date       >= month_start,
                Employee.separation_date       <= month_end,
            )
        )).scalar_one()

        terminations = (await db.execute(
            select(func.count(Employee.id)).where(
                Employee.tenant_id             == tenant_id,
                Employee.separation_type       == "termination",
                Employee.separation_date       >= month_start,
                Employee.separation_date       <= month_end,
            )
        )).scalar_one()

        # Headcount at month end
        headcount = (await db.execute(
            select(func.count(Employee.id)).where(
                Employee.tenant_id         == tenant_id,
                Employee.date_of_joining   <= month_end,
                or_(
                    Employee.separation_date == None,
                    Employee.separation_date > month_end,
                ),
            )
        )).scalar_one()

        total_exits  = resignations + terminations
        turnover_rate = round(total_exits / headcount * 100, 1) if headcount > 0 else 0.0

        months_data.append(TurnoverMonth(
            month         = MONTH_NAMES[month_num],
            month_num     = month_num,
            resignations  = resignations,
            terminations  = terminations,
            total_exits   = total_exits,
            headcount     = headcount,
            turnover_rate = turnover_rate,
        ))

    total_exits = sum(m.total_exits for m in months_data)
    valid_rates = [m.turnover_rate for m in months_data if m.headcount > 0]
    avg_rate    = round(sum(valid_rates) / len(valid_rates), 1) if valid_rates else 0.0

    return TurnoverReport(
        year        = year,
        months      = months_data,
        total_exits = total_exits,
        avg_rate    = avg_rate,
    )


# ─── Attendance Report ────────────────────────────────────────────────────────

async def get_attendance_report(
    tenant_id: UUID,
    month:     int,
    year:      int,
    db:        AsyncSession,
) -> AttendanceReport:
    _, last_day = calendar.monthrange(year, month)
    start = date(year, month, 1)
    end   = date(year, month, last_day)

    # Department-wise summary
    dept_rows = (await db.execute(
        select(
            Department.name,
            func.count(AttendanceRecord.id).label("total"),
            func.sum(
                case((AttendanceRecord.status.in_(["present", "late", "half_day"]), 1), else_=0)
            ).label("present"),
            func.sum(
                case((AttendanceRecord.status == "absent", 1), else_=0)
            ).label("absent"),
            func.sum(
                case((AttendanceRecord.status == "late", 1), else_=0)
            ).label("late"),
        )
        .join(Employee, AttendanceRecord.employee_id == Employee.id)
        .join(Department, Employee.department_id == Department.id, isouter=True)
        .where(
            Employee.tenant_id     == tenant_id,
            AttendanceRecord.date  >= start,
            AttendanceRecord.date  <= end,
        )
        .group_by(Department.name)
        .order_by(Department.name)
    )).all()

    by_dept = []
    for row in dept_rows:
        total   = row.total or 0
        present = int(row.present or 0)
        absent  = int(row.absent  or 0)
        late    = int(row.late    or 0)
        by_dept.append(DeptAttendance(
            department     = row.name or "Unassigned",
            total_expected = total,
            present        = present,
            absent         = absent,
            late           = late,
            present_pct    = round(present / total * 100, 1) if total else 0,
            absent_pct     = round(absent  / total * 100, 1) if total else 0,
            late_pct       = round(late    / total * 100, 1) if total else 0,
        ))

    # Daily trend for the month
    daily_rows = (await db.execute(
        select(
            AttendanceRecord.date,
            func.count(AttendanceRecord.id).label("total"),
            func.sum(case((AttendanceRecord.status.in_(["present","late","half_day"]), 1), else_=0)).label("present"),
            func.sum(case((AttendanceRecord.status == "absent", 1), else_=0)).label("absent"),
            func.sum(case((AttendanceRecord.status == "late",   1), else_=0)).label("late"),
        )
        .join(Employee, AttendanceRecord.employee_id == Employee.id)
        .where(
            Employee.tenant_id     == tenant_id,
            AttendanceRecord.date  >= start,
            AttendanceRecord.date  <= end,
        )
        .group_by(AttendanceRecord.date)
        .order_by(AttendanceRecord.date)
    )).all()

    daily_trend = [
        {
            "date":    row.date.isoformat(),
            "present": int(row.present or 0),
            "absent":  int(row.absent  or 0),
            "late":    int(row.late    or 0),
        }
        for row in daily_rows
    ]

    return AttendanceReport(
        month       = month,
        year        = year,
        by_dept     = by_dept,
        daily_trend = daily_trend,
    )


# ─── Payroll Report ───────────────────────────────────────────────────────────

async def get_payroll_report(tenant_id: UUID, year: int, db: AsyncSession) -> PayrollReport:
    months_data: list[PayrollMonth] = []
    totals: dict[str, float] = {"gross": 0, "net": 0, "tax": 0, "eobi": 0}

    for month_num in range(1, 13):
        # Find runs for this month
        run_ids = (await db.execute(
            select(PayrollRun.id).where(
                PayrollRun.tenant_id == tenant_id,
                PayrollRun.month     == month_num,
                PayrollRun.year      == year,
                PayrollRun.status.in_(["approved", "paid"]),
            )
        )).scalars().all()

        if not run_ids:
            months_data.append(PayrollMonth(
                month     = MONTH_NAMES[month_num],
                month_num = month_num,
                gross     = 0,
                net       = 0,
                tax       = 0,
                eobi      = 0,
                headcount = 0,
            ))
            continue

        agg = (await db.execute(
            select(
                func.sum(PayrollRecord.gross_salary).label("gross"),
                func.sum(PayrollRecord.net_salary).label("net"),
                func.sum(PayrollRecord.tax_deducted).label("tax"),
                func.sum(PayrollRecord.eobi_contribution).label("eobi"),
                func.count(PayrollRecord.id).label("headcount"),
            )
            .where(PayrollRecord.payroll_run_id.in_(run_ids))
        )).one()

        gross     = float(agg.gross     or 0)
        net       = float(agg.net       or 0)
        tax       = float(agg.tax       or 0)
        eobi      = float(agg.eobi      or 0)
        headcount = int(agg.headcount   or 0)

        totals["gross"] += gross
        totals["net"]   += net
        totals["tax"]   += tax
        totals["eobi"]  += eobi

        months_data.append(PayrollMonth(
            month     = MONTH_NAMES[month_num],
            month_num = month_num,
            gross     = round(gross, 2),
            net       = round(net,   2),
            tax       = round(tax,   2),
            eobi      = round(eobi,  2),
            headcount = headcount,
        ))

    return PayrollReport(
        year   = year,
        months = months_data,
        totals = {k: round(v, 2) for k, v in totals.items()},
    )


# ─── Leave Report ─────────────────────────────────────────────────────────────

async def get_leave_report(tenant_id: UUID, year: int, db: AsyncSession) -> LeaveReport:
    start = date(year, 1, 1)
    end   = date(year, 12, 31)

    # By leave type
    type_rows = (await db.execute(
        select(
            LeaveType.name,
            func.count(LeaveRequest.id).label("requests"),
            func.sum(LeaveRequest.total_days).label("total_days"),
        )
        .join(LeaveType, LeaveRequest.leave_type_id == LeaveType.id)
        .where(
            LeaveRequest.tenant_id   == tenant_id,
            LeaveRequest.status      == "approved",
            LeaveRequest.start_date  >= start,
            LeaveRequest.end_date    <= end,
        )
        .group_by(LeaveType.name)
        .order_by(func.sum(LeaveRequest.total_days).desc())
    )).all()

    by_type = [
        LeaveByType(
            leave_type = row.name,
            total_days = float(row.total_days or 0),
            employees  = row.requests,
        )
        for row in type_rows
    ]

    # By department
    dept_rows = (await db.execute(
        select(
            Department.name,
            func.sum(LeaveRequest.total_days).label("total_days"),
            func.count(func.distinct(LeaveRequest.employee_id)).label("emp_count"),
        )
        .join(Employee, LeaveRequest.employee_id == Employee.id)
        .join(Department, Employee.department_id == Department.id, isouter=True)
        .where(
            LeaveRequest.tenant_id   == tenant_id,
            LeaveRequest.status      == "approved",
            LeaveRequest.start_date  >= start,
            LeaveRequest.end_date    <= end,
        )
        .group_by(Department.name)
        .order_by(func.sum(LeaveRequest.total_days).desc())
    )).all()

    by_department = [
        LeaveDeptRow(
            department  = row.name or "Unassigned",
            total_days  = float(row.total_days or 0),
            avg_per_emp = round(float(row.total_days or 0) / row.emp_count, 1)
                          if row.emp_count else 0,
        )
        for row in dept_rows
    ]

    # Monthly trend
    monthly_rows = (await db.execute(
        select(
            extract("month", LeaveRequest.start_date).label("month_num"),
            func.sum(LeaveRequest.total_days).label("days"),
        )
        .where(
            LeaveRequest.tenant_id  == tenant_id,
            LeaveRequest.status     == "approved",
            LeaveRequest.start_date >= start,
            LeaveRequest.end_date   <= end,
        )
        .group_by(extract("month", LeaveRequest.start_date))
        .order_by(extract("month", LeaveRequest.start_date))
    )).all()

    monthly_map = {int(r.month_num): float(r.days or 0) for r in monthly_rows}
    monthly_trend = [
        {"month": MONTH_NAMES[m], "month_num": m, "days_taken": monthly_map.get(m, 0)}
        for m in range(1, 13)
    ]

    return LeaveReport(
        year           = year,
        by_type        = by_type,
        by_department  = by_department,
        monthly_trend  = monthly_trend,
    )


# ─── Recruitment Report ───────────────────────────────────────────────────────

async def get_recruitment_report(tenant_id: UUID, year: int, db: AsyncSession) -> RecruitmentReport:
    start = date(year, 1, 1)
    end   = date(year, 12, 31)

    total_postings = (await db.execute(
        select(func.count(JobPosting.id)).where(
            JobPosting.tenant_id   == tenant_id,
            JobPosting.created_at  >= start,
            JobPosting.created_at  <= end,
        )
    )).scalar_one()

    total_applications = (await db.execute(
        select(func.count(JobApplication.id))
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .where(
            JobPosting.tenant_id     == tenant_id,
            JobApplication.applied_at >= start,
            JobApplication.applied_at <= end,
        )
    )).scalar_one()

    total_hires = (await db.execute(
        select(func.count(JobApplication.id))
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .where(
            JobPosting.tenant_id        == tenant_id,
            JobApplication.status       == "hired",
            JobApplication.applied_at   >= start,
            JobApplication.applied_at   <= end,
        )
    )).scalar_one()

    avg_time_to_hire = 0.0
    try:
        # Average days from application to hire
        time_rows = (await db.execute(
            select(
                func.avg(
                    func.extract("epoch", JobApplication.updated_at) -
                    func.extract("epoch", JobApplication.applied_at)
                ).label("avg_seconds")
            )
            .join(JobPosting, JobApplication.job_id == JobPosting.id)
            .where(
                JobPosting.tenant_id        == tenant_id,
                JobApplication.status       == "hired",
                JobApplication.applied_at   >= start,
                JobApplication.applied_at   <= end,
            )
        )).one()
        if time_rows.avg_seconds:
            avg_time_to_hire = round(float(time_rows.avg_seconds) / 86400, 1)
    except Exception:
        pass

    # Monthly breakdown
    monthly_rows = (await db.execute(
        select(
            extract("month", JobApplication.applied_at).label("month_num"),
            func.count(JobApplication.id).label("applications"),
            func.sum(case((JobApplication.status == "hired", 1), else_=0)).label("hires"),
        )
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .where(
            JobPosting.tenant_id     == tenant_id,
            JobApplication.applied_at >= start,
            JobApplication.applied_at <= end,
        )
        .group_by(extract("month", JobApplication.applied_at))
        .order_by(extract("month", JobApplication.applied_at))
    )).all()

    monthly_map = {int(r.month_num): {"applications": r.applications, "hires": int(r.hires or 0)}
                   for r in monthly_rows}
    monthly = [
        {
            "month":        MONTH_NAMES[m],
            "month_num":    m,
            "applications": monthly_map.get(m, {}).get("applications", 0),
            "hires":        monthly_map.get(m, {}).get("hires", 0),
        }
        for m in range(1, 13)
    ]

    # By department
    dept_rows = (await db.execute(
        select(
            Department.name,
            func.count(JobApplication.id).label("applications"),
            func.sum(case((JobApplication.status == "hired", 1), else_=0)).label("hires"),
        )
        .join(JobPosting, JobApplication.job_id == JobPosting.id)
        .join(Department, JobPosting.department_id == Department.id, isouter=True)
        .where(
            JobPosting.tenant_id     == tenant_id,
            JobApplication.applied_at >= start,
            JobApplication.applied_at <= end,
        )
        .group_by(Department.name)
        .order_by(func.count(JobApplication.id).desc())
    )).all()

    by_department = [
        {"department": r.name or "Unknown", "applications": r.applications, "hires": int(r.hires or 0)}
        for r in dept_rows
    ]

    return RecruitmentReport(
        year               = year,
        total_postings     = total_postings,
        total_applications = total_applications,
        total_hires        = total_hires,
        avg_time_to_hire   = avg_time_to_hire,
        monthly            = monthly,
        by_department      = by_department,
    )

"""
AI-HRMS — Anomaly Detector.

Detects unusual patterns in HR data: attendance spikes, overtime anomalies,
leave clustering, payroll outliers, and turnover spikes.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Literal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

Severity = Literal["low", "medium", "high"]


@dataclass
class Anomaly:
    id:                  str
    type:                str
    severity:            Severity
    description:         str
    affected_entities:   list[str]
    detected_at:         str
    recommended_action:  str
    is_reviewed:         bool = False


async def detect_anomalies(
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> list[Anomaly]:
    """Run all anomaly detectors and return combined list."""
    results: list[Anomaly] = []
    now_str = datetime.now(timezone.utc).isoformat()

    results += await _detect_attendance_spike(tenant_id, db, now_str)
    results += await _detect_overtime_spike(tenant_id, db, now_str)
    results += await _detect_leave_clustering(tenant_id, db, now_str)
    results += await _detect_payroll_anomaly(tenant_id, db, now_str)
    results += await _detect_turnover_spike(tenant_id, db, now_str)

    return results


# ─── Attendance spike ─────────────────────────────────────────────────────────

async def _detect_attendance_spike(
    tenant_id: uuid.UUID,
    db: AsyncSession,
    now_str: str,
) -> list[Anomaly]:
    """Flag departments where absent rate today is 2× their 30-day average."""
    from app.models.attendance import AttendanceRecord
    from app.models.employee import Department, Employee

    anomalies: list[Anomaly] = []
    today = date.today()
    thirty_ago = today - timedelta(days=30)

    try:
        att_col = getattr(AttendanceRecord, "work_date",
                  getattr(AttendanceRecord, "date", None))
        if att_col is None:
            return []

        depts = (await db.execute(
            select(Department.id, Department.name)
            .where(Department.tenant_id == tenant_id)
        )).fetchall()

        for dept_id, dept_name in depts:
            # 30-day absent rate for this dept
            hist = (await db.execute(
                select(
                    func.count(AttendanceRecord.id).label("total"),
                    func.sum(
                        func.cast(AttendanceRecord.status == "absent", __import__("sqlalchemy").Integer)
                    ).label("absent_count"),
                )
                .join(Employee, AttendanceRecord.employee_id == Employee.id)
                .where(
                    Employee.department_id == dept_id,
                    Employee.tenant_id == tenant_id,
                    att_col >= thirty_ago,
                    att_col < today,
                    AttendanceRecord.status.notin_(["holiday", "weekly_off"]),
                )
            )).one_or_none()

            if hist is None or (hist.total or 0) == 0:
                continue

            hist_rate = (hist.absent_count or 0) / hist.total

            # Today's rate
            today_row = (await db.execute(
                select(
                    func.count(AttendanceRecord.id).label("total"),
                    func.sum(
                        func.cast(AttendanceRecord.status == "absent", __import__("sqlalchemy").Integer)
                    ).label("absent_count"),
                )
                .join(Employee, AttendanceRecord.employee_id == Employee.id)
                .where(
                    Employee.department_id == dept_id,
                    Employee.tenant_id == tenant_id,
                    att_col == today,
                    AttendanceRecord.status.notin_(["holiday", "weekly_off"]),
                )
            )).one_or_none()

            today_total  = (today_row.total if today_row else 0) or 0
            today_absent = (today_row.absent_count if today_row else 0) or 0

            if today_total == 0:
                continue

            today_rate = today_absent / today_total
            threshold  = max(hist_rate * 2, 0.30)   # at least 30% absent to flag

            if today_rate >= threshold and today_absent >= 3:
                sev: Severity = "high" if today_rate > 0.50 else "medium"
                anomalies.append(Anomaly(
                    id=f"att_spike_{dept_id}_{today.isoformat()}",
                    type="attendance_spike",
                    severity=sev,
                    description=(
                        f"{dept_name}: {today_absent}/{today_total} employees absent today "
                        f"({today_rate:.0%}), vs 30-day average of {hist_rate:.0%}"
                    ),
                    affected_entities=[str(dept_id)],
                    detected_at=now_str,
                    recommended_action=(
                        "Contact department head to identify cause; "
                        "check for team events, illness, or morale issues"
                    ),
                ))
    except Exception as e:
        logger.warning("anomaly.attendance_spike_failed", error=str(e))

    return anomalies


# ─── Overtime spike ───────────────────────────────────────────────────────────

async def _detect_overtime_spike(
    tenant_id: uuid.UUID,
    db: AsyncSession,
    now_str: str,
) -> list[Anomaly]:
    """Flag employees whose overtime this week is 3× their personal average."""
    from app.models.attendance import AttendanceRecord
    from app.models.employee import Employee

    anomalies: list[Anomaly] = []
    today = date.today()
    week_ago    = today - timedelta(days=7)
    month_ago   = today - timedelta(days=30)

    try:
        ot_col = getattr(AttendanceRecord, "overtime_minutes", None)
        att_col = getattr(AttendanceRecord, "work_date",
                  getattr(AttendanceRecord, "date", None))
        if ot_col is None or att_col is None:
            return []

        employees = (await db.execute(
            select(Employee.id, Employee.first_name, Employee.last_name)
            .where(
                Employee.tenant_id == tenant_id,
                Employee.employment_status == "active",
            )
        )).fetchall()

        for emp_id, fname, lname in employees:
            # Month avg OT (per day)
            hist = (await db.execute(
                select(
                    func.coalesce(func.avg(ot_col), 0).label("avg_ot"),
                    func.count(AttendanceRecord.id).label("days"),
                )
                .where(
                    AttendanceRecord.employee_id == emp_id,
                    att_col >= month_ago,
                    att_col < week_ago,
                )
            )).one_or_none()
            avg_ot = float(hist.avg_ot if hist else 0)

            # This week's OT
            this_week = (await db.execute(
                select(func.coalesce(func.sum(ot_col), 0))
                .where(
                    AttendanceRecord.employee_id == emp_id,
                    att_col >= week_ago,
                )
            )).scalar() or 0

            weekly_avg = avg_ot * 7
            if weekly_avg < 30:   # skip if historically minimal OT
                continue

            if float(this_week) >= weekly_avg * 3 and float(this_week) >= 300:
                anomalies.append(Anomaly(
                    id=f"ot_spike_{emp_id}_{today.isoformat()}",
                    type="overtime_spike",
                    severity="medium",
                    description=(
                        f"{fname} {lname}: {this_week:.0f} overtime minutes this week, "
                        f"3× their 30-day average of {weekly_avg:.0f} min/week"
                    ),
                    affected_entities=[str(emp_id)],
                    detected_at=now_str,
                    recommended_action=(
                        "Review workload; discuss with manager to redistribute tasks "
                        "or adjust deadlines to prevent burnout"
                    ),
                ))
    except Exception as e:
        logger.warning("anomaly.overtime_spike_failed", error=str(e))

    return anomalies


# ─── Leave clustering ─────────────────────────────────────────────────────────

async def _detect_leave_clustering(
    tenant_id: uuid.UUID,
    db: AsyncSession,
    now_str: str,
) -> list[Anomaly]:
    """Flag when 3+ employees from the same department request leave on the same dates."""
    from app.models.leave import LeaveRequest
    from app.models.employee import Employee, Department

    anomalies: list[Anomaly] = []
    today = date.today()
    next_two_weeks = today + timedelta(days=14)

    try:
        # Find approved/pending leaves in the next 2 weeks
        rows = (await db.execute(
            select(
                Employee.department_id,
                Department.name,
                LeaveRequest.from_date,
                func.count(LeaveRequest.id).label("count"),
            )
            .join(Employee, LeaveRequest.employee_id == Employee.id)
            .join(Department, Employee.department_id == Department.id)
            .where(
                Employee.tenant_id == tenant_id,
                LeaveRequest.status.in_(["pending", "approved"]),
                LeaveRequest.from_date >= today,
                LeaveRequest.from_date <= next_two_weeks,
            )
            .group_by(Employee.department_id, Department.name, LeaveRequest.from_date)
            .having(func.count(LeaveRequest.id) >= 3)
        )).fetchall()

        for dept_id, dept_name, leave_date, count in rows:
            anomalies.append(Anomaly(
                id=f"leave_cluster_{dept_id}_{leave_date.isoformat()}",
                type="leave_clustering",
                severity="medium",
                description=(
                    f"{dept_name}: {count} employees have leave on {leave_date.strftime('%d %b %Y')} — "
                    f"may impact department coverage"
                ),
                affected_entities=[str(dept_id)],
                detected_at=now_str,
                recommended_action=(
                    "Review leave calendar; consider staggering leave approvals "
                    "to ensure minimum staffing levels"
                ),
            ))
    except Exception as e:
        logger.warning("anomaly.leave_clustering_failed", error=str(e))

    return anomalies


# ─── Payroll anomaly ──────────────────────────────────────────────────────────

async def _detect_payroll_anomaly(
    tenant_id: uuid.UUID,
    db: AsyncSession,
    now_str: str,
) -> list[Anomaly]:
    """Flag when current month payroll total is >20% higher than last month."""
    from app.models.payroll import PayrollRun

    anomalies: list[Anomaly] = []
    today = date.today()

    try:
        last_two = (await db.execute(
            select(
                PayrollRun.month, PayrollRun.year,
                PayrollRun.total_gross, PayrollRun.status,
            )
            .where(
                PayrollRun.tenant_id == tenant_id,
                PayrollRun.status.in_(["approved", "paid", "processing"]),
            )
            .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
            .limit(2)
        )).fetchall()

        if len(last_two) < 2:
            return []

        current = last_two[0]
        previous = last_two[1]

        if (previous.total_gross or 0) == 0:
            return []

        change_pct = (
            (float(current.total_gross) - float(previous.total_gross))
            / float(previous.total_gross)
        )

        if change_pct > 0.20:
            anomalies.append(Anomaly(
                id=f"payroll_spike_{current.year}_{current.month}",
                type="payroll_anomaly",
                severity="high" if change_pct > 0.35 else "medium",
                description=(
                    f"Payroll for {current.month}/{current.year} is "
                    f"{change_pct:.0%} higher than previous month "
                    f"(PKR {current.total_gross:,} vs PKR {previous.total_gross:,})"
                ),
                affected_entities=[],
                detected_at=now_str,
                recommended_action=(
                    "Audit payroll run for new hires, promotions, bonuses, "
                    "or data entry errors before final approval"
                ),
            ))
    except Exception as e:
        logger.warning("anomaly.payroll_anomaly_failed", error=str(e))

    return anomalies


# ─── Turnover spike ───────────────────────────────────────────────────────────

async def _detect_turnover_spike(
    tenant_id: uuid.UUID,
    db: AsyncSession,
    now_str: str,
) -> list[Anomaly]:
    """Flag departments with 2+ resignations/terminations this month."""
    from app.models.employee import Employee, Department

    anomalies: list[Anomaly] = []
    today = date.today()
    month_start = today.replace(day=1)

    try:
        rows = (await db.execute(
            select(
                Employee.department_id,
                Department.name,
                func.count(Employee.id).label("exits"),
            )
            .join(Department, Employee.department_id == Department.id)
            .where(
                Employee.tenant_id == tenant_id,
                Employee.employment_status.in_(["resigned", "terminated"]),
                Employee.updated_at >= datetime.combine(
                    month_start, datetime.min.time()
                ).replace(tzinfo=timezone.utc),
            )
            .group_by(Employee.department_id, Department.name)
            .having(func.count(Employee.id) >= 2)
        )).fetchall()

        for dept_id, dept_name, exits in rows:
            anomalies.append(Anomaly(
                id=f"turnover_spike_{dept_id}_{today.year}_{today.month}",
                type="turnover_spike",
                severity="high" if exits >= 3 else "medium",
                description=(
                    f"{dept_name}: {exits} employee(s) resigned/terminated this month — "
                    f"above normal turnover threshold"
                ),
                affected_entities=[str(dept_id)],
                detected_at=now_str,
                recommended_action=(
                    "Conduct exit interviews to understand root cause; "
                    "schedule stay interviews with remaining team members"
                ),
            ))
    except Exception as e:
        logger.warning("anomaly.turnover_spike_failed", error=str(e))

    return anomalies

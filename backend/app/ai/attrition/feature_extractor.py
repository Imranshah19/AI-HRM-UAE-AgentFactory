"""
AI-HRMS — Attrition Feature Extractor.

Extracts and normalizes features for a single employee from the database.
All features are in [0, 1] range where 1.0 = maximum risk contribution.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# ─── Feature names (ordered, matches model input vector) ──────────────────────

FEATURE_NAMES = [
    "tenure_short",          # short tenure → higher risk
    "salary_growth_low",     # low/no salary growth → higher risk
    "absent_rate_30d",       # high absence → higher risk
    "late_rate_30d",         # high lateness → higher risk
    "leave_utilization",     # high leave use → moderate risk signal
    "days_since_promotion",  # long without promotion → higher risk
    "perf_rating_low",       # low last rating → higher risk
    "perf_trend_negative",   # declining ratings → higher risk
    "manager_changes",       # frequent manager changes → higher risk
    "training_incomplete",   # low training completion → higher risk
    "pending_leaves",        # many pending leave requests → higher risk
    "overtime_high",         # chronic overtime → burnout risk
    "salary_below_avg",      # below dept average → higher risk
    "dept_turnover",         # high dept turnover → contagion risk
]


async def extract_employee_features(
    employee_id: uuid.UUID,
    tenant_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, float]:
    """
    Extract all attrition risk features for one employee.
    Returns a dict keyed by FEATURE_NAMES, values in [0, 1].
    On any DB error, falls back to a neutral value for that feature.
    """
    from app.models.employee import Employee
    from app.models.attendance import AttendanceRecord
    from app.models.leave import LeaveBalance, LeaveRequest
    from app.models.performance import Appraisal
    from app.models.training import TrainingEnrollment
    from app.models.compensation import SalaryStructure

    today = date.today()
    thirty_ago = today - timedelta(days=30)
    two_years_ago = today - timedelta(days=730)
    one_year_ago = today - timedelta(days=365)

    features: dict[str, float] = {k: 0.5 for k in FEATURE_NAMES}

    # ── Load employee ──────────────────────────────────────────────────────────
    try:
        emp_result = await db.execute(
            select(Employee).where(
                Employee.id == employee_id,
                Employee.tenant_id == tenant_id,
            )
        )
        employee = emp_result.scalar_one_or_none()
        if employee is None:
            return features
    except Exception as e:
        logger.warning("feature_extractor.employee_load_failed", error=str(e))
        return features

    # ── 1. Tenure (short = higher risk) ───────────────────────────────────────
    try:
        join = getattr(employee, "date_of_joining", None) or getattr(employee, "join_date", None)
        if join:
            tenure_months = (today - join).days / 30.44
        else:
            tenure_months = 24.0
        # 0–6 months → near 1.0, 60+ months → near 0
        features["tenure_short"] = max(0.0, min(1.0, 1.0 - (min(tenure_months, 60) / 60.0)))
    except Exception:
        features["tenure_short"] = 0.3

    # ── 2. Salary growth rate ──────────────────────────────────────────────────
    try:
        sal_rows = (await db.execute(
            select(SalaryStructure.basic_pay, SalaryStructure.effective_from)
            .where(SalaryStructure.employee_id == employee_id)
            .order_by(SalaryStructure.effective_from)
        )).fetchall()

        if len(sal_rows) >= 2:
            old_pay = float(sal_rows[0][0] or 1)
            new_pay = float(sal_rows[-1][0] or 1)
            growth = (new_pay - old_pay) / max(old_pay, 1)
        else:
            growth = 0.05  # assume modest growth if only one record

        # growth <0 → risk 1.0; growth >25% → risk 0
        features["salary_growth_low"] = max(0.0, min(1.0, 1.0 - ((growth + 0.05) / 0.30)))
    except Exception:
        features["salary_growth_low"] = 0.4

    # ── 3–4. Attendance rates (last 30 days) ──────────────────────────────────
    try:
        att_col = None
        # Try work_date first, then date
        for col_name in ("work_date", "date"):
            try:
                col = getattr(AttendanceRecord, col_name)
                att_col = col
                break
            except AttributeError:
                continue

        if att_col is not None:
            rows = (await db.execute(
                select(AttendanceRecord.status)
                .where(
                    AttendanceRecord.employee_id == employee_id,
                    att_col >= thirty_ago,
                    att_col <= today,
                )
            )).scalars().all()

            workdays = [s for s in rows if s not in ("holiday", "weekly_off")] or ["present"]
            wn = len(workdays)
            absent = sum(1 for s in workdays if s == "absent")
            late   = sum(1 for s in workdays if s == "late")

            features["absent_rate_30d"] = min(1.0, absent / wn / 0.20)
            features["late_rate_30d"]   = min(1.0, late   / wn / 0.25)
    except Exception:
        features["absent_rate_30d"] = 0.1
        features["late_rate_30d"]   = 0.1

    # ── 5. Leave utilization ──────────────────────────────────────────────────
    try:
        row = (await db.execute(
            select(
                func.coalesce(func.sum(LeaveBalance.used_days), 0).label("used"),
                func.coalesce(func.sum(LeaveBalance.total_days), 1).label("total"),
            )
            .where(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == today.year,
            )
        )).one_or_none()
        used  = float(row.used  if row else 0)
        total = float(row.total if row else 1) or 1
        features["leave_utilization"] = min(1.0, used / total)
    except Exception:
        features["leave_utilization"] = 0.5

    # ── 6. Days since last promotion ──────────────────────────────────────────
    try:
        join_date = getattr(employee, "date_of_joining", None) or getattr(employee, "join_date", today)
        months_since = (today - join_date).days / 30.44 if join_date else 24
        # 0 months → 0 risk; 36+ months no promo → higher risk
        features["days_since_promotion"] = max(0.0, min(1.0, months_since / 36.0))
    except Exception:
        features["days_since_promotion"] = 0.5

    # ── 7–8. Performance ratings ──────────────────────────────────────────────
    try:
        appraisals = (await db.execute(
            select(Appraisal.final_rating, Appraisal.created_at)
            .where(Appraisal.employee_id == employee_id)
            .order_by(Appraisal.created_at.desc())
            .limit(3)
        )).fetchall()

        if appraisals:
            last = float(appraisals[0][0] or 3.0)
            # 1 → risk 1.0; 5 → risk 0.0
            features["perf_rating_low"] = max(0.0, min(1.0, 1.0 - ((last - 1.0) / 4.0)))
            if len(appraisals) >= 2:
                prev  = float(appraisals[1][0] or 3.0)
                trend = last - prev   # negative = declining
                features["perf_trend_negative"] = max(0.0, min(1.0, 0.5 - (trend / 4.0)))
            else:
                features["perf_trend_negative"] = 0.3
        else:
            features["perf_rating_low"]      = 0.4
            features["perf_trend_negative"]  = 0.3
    except Exception:
        features["perf_rating_low"]     = 0.4
        features["perf_trend_negative"] = 0.3

    # ── 9. Manager changes ────────────────────────────────────────────────────
    # Proxy: if manager_id is None, score slightly higher (un-managed = higher risk)
    try:
        has_manager = bool(getattr(employee, "manager_id", None))
        features["manager_changes"] = 0.1 if has_manager else 0.4
    except Exception:
        features["manager_changes"] = 0.2

    # ── 10. Training completion ───────────────────────────────────────────────
    try:
        train_statuses = (await db.execute(
            select(TrainingEnrollment.status)
            .where(TrainingEnrollment.employee_id == employee_id)
        )).scalars().all()
        if train_statuses:
            n_done = sum(1 for s in train_statuses if s == "completed")
            features["training_incomplete"] = 1.0 - (n_done / len(train_statuses))
        else:
            features["training_incomplete"] = 0.4
    except Exception:
        features["training_incomplete"] = 0.4

    # ── 11. Pending leave requests ────────────────────────────────────────────
    try:
        pending = (await db.execute(
            select(func.count(LeaveRequest.id))
            .where(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.status == "pending",
            )
        )).scalar() or 0
        features["pending_leaves"] = min(1.0, pending / 3.0)
    except Exception:
        features["pending_leaves"] = 0.0

    # ── 12. Overtime (burnout risk) ───────────────────────────────────────────
    try:
        ot_col = getattr(AttendanceRecord, "overtime_minutes", None)
        if ot_col is not None:
            att_col_date = getattr(AttendanceRecord, "work_date",
                          getattr(AttendanceRecord, "date", None))
            if att_col_date is not None:
                ot_total = (await db.execute(
                    select(func.coalesce(func.sum(ot_col), 0))
                    .where(
                        AttendanceRecord.employee_id == employee_id,
                        att_col_date >= thirty_ago,
                    )
                )).scalar() or 0
                # 30d * 8hr = 14400 min. OT > 20% of work time = high risk
                features["overtime_high"] = min(1.0, float(ot_total) / 2880.0)
    except Exception:
        features["overtime_high"] = 0.1

    # ── 13. Salary vs department average ─────────────────────────────────────
    try:
        dept_avg = (await db.execute(
            select(func.avg(SalaryStructure.basic_pay))
            .join(
                __import__("app.models.employee", fromlist=["Employee"]).Employee,
                SalaryStructure.employee_id ==
                __import__("app.models.employee", fromlist=["Employee"]).Employee.id,
            )
            .where(
                __import__("app.models.employee", fromlist=["Employee"]).Employee.department_id
                == employee.department_id,
                __import__("app.models.employee", fromlist=["Employee"]).Employee.tenant_id
                == tenant_id,
                SalaryStructure.is_active.is_(True),
            )
        )).scalar() or 0

        emp_sal = (await db.execute(
            select(SalaryStructure.basic_pay)
            .where(
                SalaryStructure.employee_id == employee_id,
                SalaryStructure.is_active.is_(True),
            )
            .limit(1)
        )).scalar() or 0

        ratio = float(emp_sal) / max(float(dept_avg), 1)
        # ratio < 0.85 → risky; ratio ≥ 1.15 → safe
        features["salary_below_avg"] = max(0.0, min(1.0, (0.85 - ratio + 0.15) / 0.30))
    except Exception:
        features["salary_below_avg"] = 0.3

    # ── 14. Department turnover rate ──────────────────────────────────────────
    try:
        dept_total = (await db.execute(
            select(func.count(Employee.id))
            .where(
                Employee.department_id == employee.department_id,
                Employee.tenant_id == tenant_id,
            )
        )).scalar() or 1

        dept_resigned = (await db.execute(
            select(func.count(Employee.id))
            .where(
                Employee.department_id == employee.department_id,
                Employee.tenant_id == tenant_id,
                Employee.employment_status.in_(["resigned", "terminated"]),
            )
        )).scalar() or 0

        turnover = dept_resigned / max(float(dept_total), 1)
        features["dept_turnover"] = min(1.0, turnover / 0.25)
    except Exception:
        features["dept_turnover"] = 0.2

    return features

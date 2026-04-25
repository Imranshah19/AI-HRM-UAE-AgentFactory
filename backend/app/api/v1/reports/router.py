"""
AI-HRMS — Reports & Analytics router.

GET /reports/dashboard-stats
GET /reports/headcount
GET /reports/turnover?year=
GET /reports/attendance?month=&year=
GET /reports/payroll?year=
GET /reports/leave?year=
GET /reports/recruitment?year=

All support ?export=excel for Excel download.
All require reports:read permission.
"""

from __future__ import annotations

import io
from datetime import date
from typing   import Annotated, Optional

from fastapi           import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.models.tenant import User

from app.api.v1.reports import service
from app.api.v1.reports.schemas import (
    AttendanceReport,
    DashboardStats,
    HeadcountReport,
    LeaveReport,
    PayrollReport,
    RecruitmentReport,
    TurnoverReport,
)

router = APIRouter(prefix="/reports", tags=["Reports"])

_perm = require_permission("reports", "read")


def _excel_response(data: list[dict], sheet_name: str, filename: str) -> StreamingResponse:
    """Convert list-of-dicts to an Excel file and return as StreamingResponse."""
    try:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name

        if data:
            headers = list(data[0].keys())
            ws.append(headers)
            for row in data:
                ws.append([row.get(h) for h in headers])

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ImportError:
        # Fallback to CSV if openpyxl not installed
        import csv
        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename.replace(".xlsx", ".csv")}"'},
        )


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

@router.get(
    "/dashboard-stats",
    response_model=DashboardStats,
    summary="Aggregate stats for the dashboard",
)
async def dashboard_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.get_dashboard_stats(current_user.tenant_id, db)


# ─── Headcount ────────────────────────────────────────────────────────────────

@router.get(
    "/headcount",
    summary="Headcount breakdown by department, contract type, gender",
)
async def headcount_report(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    export:       Optional[str] = Query(None),
    _p = _perm,
):
    report = await service.get_headcount_report(current_user.tenant_id, db)
    if export == "excel":
        rows = [
            {"Department": d.department, "Count": d.count, "Percentage": f"{d.percentage}%"}
            for d in report.by_department
        ]
        return _excel_response(rows, "Headcount", "headcount_report.xlsx")
    return report


# ─── Turnover ─────────────────────────────────────────────────────────────────

@router.get(
    "/turnover",
    response_model=TurnoverReport,
    summary="Employee turnover by month for a given year",
)
async def turnover_report(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    year:         int = Query(default_factory=lambda: date.today().year, ge=2020),
    export:       Optional[str] = Query(None),
    _p = _perm,
):
    report = await service.get_turnover_report(current_user.tenant_id, year, db)
    if export == "excel":
        rows = [
            {
                "Month": m.month, "Resignations": m.resignations,
                "Terminations": m.terminations, "Total Exits": m.total_exits,
                "Headcount": m.headcount, "Turnover Rate %": m.turnover_rate,
            }
            for m in report.months
        ]
        return _excel_response(rows, "Turnover", f"turnover_{year}.xlsx")
    return report


# ─── Attendance ───────────────────────────────────────────────────────────────

@router.get(
    "/attendance",
    response_model=AttendanceReport,
    summary="Attendance summary by department for a given month/year",
)
async def attendance_report(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    month:        int = Query(default_factory=lambda: date.today().month, ge=1, le=12),
    year:         int = Query(default_factory=lambda: date.today().year, ge=2020),
    export:       Optional[str] = Query(None),
    _p = _perm,
):
    report = await service.get_attendance_report(current_user.tenant_id, month, year, db)
    if export == "excel":
        rows = [
            {
                "Department": d.department, "Expected": d.total_expected,
                "Present": d.present, "Absent": d.absent, "Late": d.late,
                "Present %": d.present_pct, "Absent %": d.absent_pct,
            }
            for d in report.by_dept
        ]
        return _excel_response(rows, "Attendance", f"attendance_{year}_{month:02d}.xlsx")
    return report


# ─── Payroll ──────────────────────────────────────────────────────────────────

@router.get(
    "/payroll",
    response_model=PayrollReport,
    summary="Monthly payroll totals for a given year",
)
async def payroll_report(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    year:         int = Query(default_factory=lambda: date.today().year, ge=2020),
    export:       Optional[str] = Query(None),
    _p = _perm,
):
    report = await service.get_payroll_report(current_user.tenant_id, year, db)
    if export == "excel":
        rows = [
            {
                "Month": m.month, "Gross": m.gross, "Net": m.net,
                "Tax": m.tax, "EOBI": m.eobi, "Headcount": m.headcount,
            }
            for m in report.months
        ]
        return _excel_response(rows, "Payroll", f"payroll_{year}.xlsx")
    return report


# ─── Leave ────────────────────────────────────────────────────────────────────

@router.get(
    "/leave",
    response_model=LeaveReport,
    summary="Leave utilization by type and department for a given year",
)
async def leave_report(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    year:         int = Query(default_factory=lambda: date.today().year, ge=2020),
    export:       Optional[str] = Query(None),
    _p = _perm,
):
    report = await service.get_leave_report(current_user.tenant_id, year, db)
    if export == "excel":
        rows = [
            {"Leave Type": t.leave_type, "Total Days": t.total_days, "Employees": t.employees}
            for t in report.by_type
        ]
        return _excel_response(rows, "Leave", f"leave_{year}.xlsx")
    return report


# ─── Recruitment ──────────────────────────────────────────────────────────────

@router.get(
    "/recruitment",
    response_model=RecruitmentReport,
    summary="Recruitment funnel metrics for a given year",
)
async def recruitment_report(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    year:         int = Query(default_factory=lambda: date.today().year, ge=2020),
    export:       Optional[str] = Query(None),
    _p = _perm,
):
    report = await service.get_recruitment_report(current_user.tenant_id, year, db)
    if export == "excel":
        rows = [
            {"Month": m["month"], "Applications": m["applications"], "Hires": m["hires"]}
            for m in report.monthly
        ]
        return _excel_response(rows, "Recruitment", f"recruitment_{year}.xlsx")
    return report

"""
AI-HRMS — Reports & Analytics Pydantic v2 schemas.
"""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel


# ─── Dashboard Stats ──────────────────────────────────────────────────────────

class UpcomingBirthday(BaseModel):
    employee_id:   str
    full_name:     str
    birthday:      str   # MM-DD format
    days_until:    int
    department:    Optional[str] = None


class DashboardStats(BaseModel):
    total_employees:   int
    present_today:     int
    pending_leaves:    int
    open_positions:    int
    payroll_due:       bool   # True if current month payroll not yet run
    upcoming_birthdays: list[UpcomingBirthday]


# ─── Headcount Report ─────────────────────────────────────────────────────────

class DeptHeadcount(BaseModel):
    department: str
    count:      int
    percentage: float


class HeadcountReport(BaseModel):
    total:              int
    by_department:      list[DeptHeadcount]
    by_contract_type:   list[dict[str, Any]]
    by_gender:          list[dict[str, Any]]
    by_status:          list[dict[str, Any]]


# ─── Turnover Report ──────────────────────────────────────────────────────────

class TurnoverMonth(BaseModel):
    month:         str   # "Jan", "Feb", …
    month_num:     int
    resignations:  int
    terminations:  int
    total_exits:   int
    headcount:     int
    turnover_rate: float  # pct


class TurnoverReport(BaseModel):
    year:        int
    months:      list[TurnoverMonth]
    total_exits: int
    avg_rate:    float


# ─── Attendance Report ────────────────────────────────────────────────────────

class DeptAttendance(BaseModel):
    department:       str
    total_expected:   int
    present:          int
    absent:           int
    late:             int
    present_pct:      float
    absent_pct:       float
    late_pct:         float


class AttendanceReport(BaseModel):
    month:       int
    year:        int
    by_dept:     list[DeptAttendance]
    daily_trend: list[dict[str, Any]]   # [{date, present, absent, late}]


# ─── Payroll Report ───────────────────────────────────────────────────────────

class PayrollMonth(BaseModel):
    month:     str
    month_num: int
    gross:     float
    net:       float
    tax:       float
    eobi:      float
    headcount: int


class PayrollReport(BaseModel):
    year:   int
    months: list[PayrollMonth]
    totals: dict[str, float]


# ─── Leave Report ─────────────────────────────────────────────────────────────

class LeaveByType(BaseModel):
    leave_type:  str
    total_days:  float
    employees:   int


class LeaveDeptRow(BaseModel):
    department:    str
    total_days:    float
    avg_per_emp:   float


class LeaveReport(BaseModel):
    year:           int
    by_type:        list[LeaveByType]
    by_department:  list[LeaveDeptRow]
    monthly_trend:  list[dict[str, Any]]   # [{month, days_taken}]


# ─── Recruitment Report ───────────────────────────────────────────────────────

class RecruitmentReport(BaseModel):
    year:             int
    total_postings:   int
    total_applications: int
    total_hires:      int
    avg_time_to_hire: float   # days
    monthly:          list[dict[str, Any]]   # [{month, applications, hires}]
    by_department:    list[dict[str, Any]]

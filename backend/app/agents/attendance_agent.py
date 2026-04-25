"""
Attendance Agent — Daily attendance monitoring and alert generation.

Responsibilities:
  - Generate daily attendance summary reports
  - Flag high absence rates (> threshold)
  - Detect late arrival patterns
  - Identify employees with no check-in records
  - Provide AI-generated insights for HR dashboard

Triggered daily by Celery beat (see triggers/scheduler.py).
Reads DB via existing AttendanceRecord model; no existing files modified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import structlog
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.openclaw import get_openclaw

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are an HR Attendance Analytics AI agent.
You analyse daily attendance data for a Pakistani company and provide:
- Clear summary of attendance health
- Actionable recommendations for HR
- Early warning flags for problematic patterns

Always be professional, data-driven, and concise.
Respond in plain English (no JSON needed for this task)."""


# ─── Data schemas ─────────────────────────────────────────────────────────────

@dataclass
class DailyAttendanceSummary:
    report_date:        date
    total_employees:    int
    present:            int
    absent:             int
    late:               int
    on_leave:           int
    work_from_home:     int
    attendance_rate:    float        # 0.0 – 1.0
    late_rate:          float
    absent_employees:   list[dict]   = field(default_factory=list)
    late_employees:     list[dict]   = field(default_factory=list)
    ai_insights:        str          = ""
    flags:              list[str]    = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "report_date":      str(self.report_date),
            "total_employees":  self.total_employees,
            "present":          self.present,
            "absent":           self.absent,
            "late":             self.late,
            "on_leave":         self.on_leave,
            "work_from_home":   self.work_from_home,
            "attendance_rate":  round(self.attendance_rate * 100, 1),
            "late_rate":        round(self.late_rate * 100, 1),
            "ai_insights":      self.ai_insights,
            "flags":            self.flags,
        }


# ─── Attendance Agent ─────────────────────────────────────────────────────────

class AttendanceAgent:
    """
    AI agent for daily attendance monitoring and insight generation.
    """

    ABSENCE_ALERT_THRESHOLD = 0.15    # Flag if >15% absent
    LATE_ALERT_THRESHOLD    = 0.10    # Flag if >10% late

    def __init__(self):
        self.claw = get_openclaw()

    async def generate_daily_report(
        self,
        tenant_id: str,
        db: AsyncSession,
        report_date: date | None = None,
    ) -> DailyAttendanceSummary:
        """
        Build today's attendance summary and enrich it with AI insights.
        """
        target_date = report_date or date.today()
        stats = await self._fetch_daily_stats(tenant_id, target_date, db)
        summary = self._build_summary(stats, target_date)
        summary.flags = self._generate_flags(summary)

        if self.claw.api_key:
            summary.ai_insights = await self._generate_ai_insights(summary)

        logger.info(
            "attendance_agent.daily_report",
            date=str(target_date),
            attendance_rate=summary.attendance_rate,
            flags=summary.flags,
        )
        return summary

    async def detect_chronic_absentees(
        self,
        tenant_id: str,
        db: AsyncSession,
        lookback_days: int = 30,
        threshold_absences: int = 5,
    ) -> list[dict]:
        """
        Return employees with >= threshold_absences absences in the lookback window.
        """
        from app.models.attendance import AttendanceRecord
        from app.models.employee import Employee

        cutoff = date.today() - timedelta(days=lookback_days)

        result = await db.execute(
            select(
                AttendanceRecord.employee_id,
                func.count(AttendanceRecord.id).label("absence_count"),
                Employee.first_name,
                Employee.last_name,
                Employee.employee_code,
            )
            .join(Employee, Employee.id == AttendanceRecord.employee_id)
            .where(
                Employee.tenant_id == tenant_id,
                AttendanceRecord.status == "absent",
                self._date_column(AttendanceRecord) >= cutoff,
            )
            .group_by(
                AttendanceRecord.employee_id,
                Employee.first_name,
                Employee.last_name,
                Employee.employee_code,
            )
            .having(func.count(AttendanceRecord.id) >= threshold_absences)
            .order_by(func.count(AttendanceRecord.id).desc())
        )

        rows = result.fetchall()
        return [
            {
                "employee_id":   str(r.employee_id),
                "employee_code": r.employee_code,
                "name":          f"{r.first_name} {r.last_name}",
                "absence_count": r.absence_count,
                "lookback_days": lookback_days,
            }
            for r in rows
        ]

    async def get_late_arrival_trend(
        self,
        tenant_id: str,
        db: AsyncSession,
        days: int = 7,
    ) -> list[dict]:
        """Return per-day late arrival counts for the last N days."""
        from app.models.attendance import AttendanceRecord
        from app.models.employee import Employee

        trend = []
        for i in range(days - 1, -1, -1):
            target = date.today() - timedelta(days=i)
            result = await db.execute(
                select(func.count(AttendanceRecord.id))
                .join(Employee, Employee.id == AttendanceRecord.employee_id)
                .where(
                    Employee.tenant_id == tenant_id,
                    AttendanceRecord.status == "late",
                    self._date_column(AttendanceRecord) == target,
                )
            )
            count = result.scalar() or 0
            trend.append({"date": str(target), "late_count": count})

        return trend

    # ── Private helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _date_column(model):
        if hasattr(model, "work_date"):
            return model.work_date
        if hasattr(model, "date"):
            return model.date
        raise AttributeError(f"{model.__name__} has no date column")

    async def _fetch_daily_stats(
        self, tenant_id: str, target_date: date, db: AsyncSession
    ) -> dict[str, Any]:
        from app.models.attendance import AttendanceRecord
        from app.models.employee import Employee

        date_col = self._date_column(AttendanceRecord)

        status_counts = await db.execute(
            select(
                AttendanceRecord.status,
                func.count(AttendanceRecord.id).label("cnt"),
            )
            .join(Employee, Employee.id == AttendanceRecord.employee_id)
            .where(
                Employee.tenant_id == tenant_id,
                date_col == target_date,
            )
            .group_by(AttendanceRecord.status)
        )
        counts = {row.status: row.cnt for row in status_counts.fetchall()}

        total_active = await db.execute(
            select(func.count(Employee.id))
            .where(
                Employee.tenant_id == tenant_id,
                Employee.employment_status == "active",
            )
        )
        total = total_active.scalar() or 0

        absent_emps = await db.execute(
            select(
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
            )
            .join(AttendanceRecord, AttendanceRecord.employee_id == Employee.id)
            .where(
                Employee.tenant_id == tenant_id,
                date_col == target_date,
                AttendanceRecord.status == "absent",
            )
            .limit(20)
        )
        late_emps = await db.execute(
            select(
                Employee.employee_code,
                Employee.first_name,
                Employee.last_name,
            )
            .join(AttendanceRecord, AttendanceRecord.employee_id == Employee.id)
            .where(
                Employee.tenant_id == tenant_id,
                date_col == target_date,
                AttendanceRecord.status == "late",
            )
            .limit(20)
        )

        return {
            "counts":          counts,
            "total_employees": total,
            "absent_list":     [
                {"code": r.employee_code, "name": f"{r.first_name} {r.last_name}"}
                for r in absent_emps.fetchall()
            ],
            "late_list": [
                {"code": r.employee_code, "name": f"{r.first_name} {r.last_name}"}
                for r in late_emps.fetchall()
            ],
        }

    def _build_summary(self, stats: dict, target_date: date) -> DailyAttendanceSummary:
        counts  = stats["counts"]
        total   = stats["total_employees"]
        present = counts.get("present", 0)
        absent  = counts.get("absent", 0)
        late    = counts.get("late", 0)
        on_leave = counts.get("on_leave", 0)
        wfh     = counts.get("work_from_home", 0)

        present_equiv = present + late + on_leave + wfh

        return DailyAttendanceSummary(
            report_date=target_date,
            total_employees=total,
            present=present,
            absent=absent,
            late=late,
            on_leave=on_leave,
            work_from_home=wfh,
            attendance_rate=present_equiv / total if total else 0.0,
            late_rate=late / total if total else 0.0,
            absent_employees=stats["absent_list"],
            late_employees=stats["late_list"],
        )

    def _generate_flags(self, summary: DailyAttendanceSummary) -> list[str]:
        flags = []
        if summary.attendance_rate < (1 - self.ABSENCE_ALERT_THRESHOLD):
            flags.append(
                f"HIGH_ABSENCE: {summary.absent} employees absent "
                f"({100 * summary.absent / summary.total_employees:.1f}%)"
            )
        if summary.late_rate > self.LATE_ALERT_THRESHOLD:
            flags.append(
                f"HIGH_LATE_RATE: {summary.late} employees late "
                f"({summary.late_rate * 100:.1f}%)"
            )
        return flags

    async def _generate_ai_insights(self, summary: DailyAttendanceSummary) -> str:
        prompt = (
            f"Daily attendance report for {summary.report_date}:\n"
            f"- Total employees: {summary.total_employees}\n"
            f"- Present: {summary.present} | Absent: {summary.absent} | "
            f"Late: {summary.late} | On Leave: {summary.on_leave} | WFH: {summary.work_from_home}\n"
            f"- Attendance rate: {summary.attendance_rate * 100:.1f}%\n"
            f"- Flags: {summary.flags}\n\n"
            "Write 2-3 sentences of HR insights and recommendations."
        )
        return await self.claw.simple_chat(prompt, system=SYSTEM_PROMPT)


# ─── Singleton ────────────────────────────────────────────────────────────────

_attendance_agent: AttendanceAgent | None = None


def get_attendance_agent() -> AttendanceAgent:
    global _attendance_agent
    if _attendance_agent is None:
        _attendance_agent = AttendanceAgent()
    return _attendance_agent

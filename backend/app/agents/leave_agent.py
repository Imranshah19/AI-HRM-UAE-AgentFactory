"""
Leave Agent — AI-powered leave lifecycle automation.

Responsibilities:
  - Analyse leave requests and recommend approve/reject decisions
  - Check leave balance, team coverage, and policy compliance
  - Draft manager notification messages
  - Surface anomalies (excessive leaves, pattern abuse)

Uses OpenClaw (Claude API) for reasoning; reads DB via existing models.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.openclaw import get_openclaw

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are an expert HR Leave Management AI agent for a Pakistani company.
You analyse leave requests and provide data-driven recommendations following:
- Company leave policy (casual, annual, sick, unpaid)
- FBR / Labour law compliance
- Team coverage and workload considerations
- Employee attendance history and previous leave patterns

Always respond with a JSON object:
{
  "recommendation": "approve" | "reject" | "review",
  "reason": "<short explanation>",
  "flags": ["<list of concerns if any>"],
  "manager_message": "<draft message to send to the manager>"
}"""


# ─── Data schemas ─────────────────────────────────────────────────────────────

@dataclass
class LeaveAnalysis:
    recommendation:  str          # "approve" | "reject" | "review"
    reason:          str
    flags:           list[str]    = field(default_factory=list)
    manager_message: str          = ""
    raw_response:    str          = ""
    confidence:      float        = 0.8


# ─── Leave Agent ──────────────────────────────────────────────────────────────

class LeaveAgent:
    """
    AI agent for leave request analysis and automation.
    Plugs into the existing leave model without modifying any existing file.
    """

    def __init__(self):
        self.claw = get_openclaw()

    async def analyse_leave_request(
        self,
        leave_request_id: str,
        db: AsyncSession,
    ) -> LeaveAnalysis:
        """
        Load a leave request from DB, gather context, ask Claude to analyse it.
        Returns a LeaveAnalysis with recommendation and reasoning.
        """
        context = await self._gather_context(leave_request_id, db)
        if context is None:
            return LeaveAnalysis(
                recommendation="review",
                reason="Leave request not found — manual review required.",
            )

        prompt = self._build_prompt(context)
        response = await self.claw.think(
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._parse_response(response.content, context)

    async def detect_anomalies(
        self,
        tenant_id: str,
        db: AsyncSession,
        lookback_days: int = 90,
    ) -> list[dict]:
        """
        Scan recent leave applications for patterns worth flagging.
        E.g. repeated Monday/Friday absences, excessive sick leave, etc.
        """
        from app.models.leave import LeaveApplication

        cutoff = date.today() - timedelta(days=lookback_days)

        rows = await db.execute(
            select(
                LeaveApplication.employee_id,
                func.count(LeaveApplication.id).label("total_applications"),
            )
            .where(
                LeaveApplication.tenant_id == tenant_id,
                LeaveApplication.applied_at >= cutoff,
            )
            .group_by(LeaveApplication.employee_id)
            .having(func.count(LeaveApplication.id) >= 5)
        )
        high_frequency = rows.fetchall()

        anomalies = []
        for row in high_frequency:
            anomalies.append({
                "employee_id":      str(row.employee_id),
                "flag":             "high_leave_frequency",
                "applications":     row.total_applications,
                "lookback_days":    lookback_days,
            })

        if anomalies and self.claw.api_key:
            summary_prompt = (
                f"The following employees had {len(anomalies)} or more leave applications "
                f"in the last {lookback_days} days: {anomalies}. "
                "Summarise the risk and suggest HR actions in 2-3 sentences."
            )
            resp = await self.claw.simple_chat(
                summary_prompt,
                system="You are an HR analytics AI. Be concise.",
            )
            for a in anomalies:
                a["ai_summary"] = resp

        return anomalies

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _gather_context(
        self, leave_request_id: str, db: AsyncSession
    ) -> dict | None:
        from app.models.leave import LeaveApplication, LeaveBalance, LeaveType
        from app.models.employee import Employee

        try:
            req_id = uuid.UUID(leave_request_id)
        except ValueError:
            return None

        result = await db.execute(
            select(LeaveApplication).where(LeaveApplication.id == req_id)
        )
        leave_req = result.scalar_one_or_none()
        if leave_req is None:
            return None

        emp_result = await db.execute(
            select(Employee).where(Employee.id == leave_req.employee_id)
        )
        employee = emp_result.scalar_one_or_none()

        balance_result = await db.execute(
            select(LeaveBalance, LeaveType.name.label("type_name"))
            .join(LeaveType, LeaveBalance.leave_type_id == LeaveType.id)
            .where(
                LeaveBalance.employee_id == leave_req.employee_id,
                LeaveBalance.leave_type_id == leave_req.leave_type_id,
                LeaveBalance.year == date.today().year,
            )
        )
        balance_row = balance_result.one_or_none()

        recent_leaves = await db.execute(
            select(func.count(LeaveApplication.id))
            .where(
                LeaveApplication.employee_id == leave_req.employee_id,
                LeaveApplication.applied_at >= date.today() - timedelta(days=90),
                LeaveApplication.status != "rejected",
            )
        )
        recent_count = recent_leaves.scalar() or 0

        context: dict[str, Any] = {
            "leave_request_id": leave_request_id,
            "employee_name":    f"{employee.first_name} {employee.last_name}" if employee else "Unknown",
            "employee_code":    employee.employee_code if employee else "N/A",
            "leave_type":       balance_row.type_name if balance_row else "Unknown",
            "start_date":       str(leave_req.start_date),
            "end_date":         str(leave_req.end_date),
            "days_requested":   leave_req.total_days,
            "reason":           leave_req.reason or "No reason provided",
            "leave_balance_remaining": (
                (balance_row.LeaveBalance.total_days - balance_row.LeaveBalance.used_days)
                if balance_row else None
            ),
            "recent_leave_count_90d": recent_count,
        }
        return context

    def _build_prompt(self, context: dict) -> str:
        return (
            f"Analyse this leave request and provide your recommendation:\n\n"
            f"Employee: {context['employee_name']} ({context['employee_code']})\n"
            f"Leave Type: {context['leave_type']}\n"
            f"Dates: {context['start_date']} to {context['end_date']} "
            f"({context['days_requested']} days)\n"
            f"Reason: {context['reason']}\n"
            f"Remaining Balance: {context['leave_balance_remaining']} days\n"
            f"Leave applications in last 90 days: {context['recent_leave_count_90d']}\n\n"
            f"Return JSON only."
        )

    def _parse_response(self, raw: str, context: dict) -> LeaveAnalysis:
        import json, re

        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return LeaveAnalysis(
                    recommendation=data.get("recommendation", "review"),
                    reason=data.get("reason", ""),
                    flags=data.get("flags", []),
                    manager_message=data.get("manager_message", ""),
                    raw_response=raw,
                    confidence=0.9,
                )
            except json.JSONDecodeError:
                pass

        recommendation = "review"
        if "approve" in raw.lower():
            recommendation = "approve"
        elif "reject" in raw.lower():
            recommendation = "reject"

        return LeaveAnalysis(
            recommendation=recommendation,
            reason=raw[:300],
            raw_response=raw,
            confidence=0.5,
        )


# ─── Singleton ────────────────────────────────────────────────────────────────

_leave_agent: LeaveAgent | None = None


def get_leave_agent() -> LeaveAgent:
    global _leave_agent
    if _leave_agent is None:
        _leave_agent = LeaveAgent()
    return _leave_agent

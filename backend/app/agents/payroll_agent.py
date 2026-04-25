"""
Payroll Agent — AI-powered payroll validation and approval intelligence.

Responsibilities:
  - Pre-process validation before a payroll run is approved
  - Flag anomalies: unusually high/low salaries, missing deductions, EOBI gaps
  - Generate natural-language payroll summaries for HR managers
  - Recommend approve / hold on a payroll run
  - Support the monthly auto-trigger (25th of every month)

Reads DB via existing PayrollRun / PayrollRecord models; no existing files modified.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

import structlog
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.openclaw import get_openclaw

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are an expert Pakistan HR Payroll Compliance AI agent.
You review payroll runs for a Pakistani company and detect:
- Salary anomalies (sudden spikes or dips > 20%)
- Missing or incorrect FBR income tax deductions
- EOBI contribution errors (employer 5%, employee 1% of min wage)
- Employees with zero net salary (potential errors)
- Total payroll budget overruns

Always respond with a valid JSON object:
{
  "recommendation": "approve" | "hold" | "reject",
  "summary": "<2-3 sentence plain-English summary for the HR manager>",
  "anomalies": [{"employee_code": "...", "issue": "...", "severity": "low|medium|high"}],
  "compliance_flags": ["<FBR/EOBI/labour law issues>"],
  "total_risk_score": 0-100
}"""


# ─── Data schemas ─────────────────────────────────────────────────────────────

@dataclass
class PayrollValidation:
    recommendation:   str          # "approve" | "hold" | "reject"
    summary:          str
    anomalies:        list[dict]   = field(default_factory=list)
    compliance_flags: list[str]    = field(default_factory=list)
    total_risk_score: int          = 0
    raw_response:     str          = ""


# ─── Payroll Agent ────────────────────────────────────────────────────────────

class PayrollAgent:
    """
    AI agent that validates payroll runs before HR approves them.
    """

    # EOBI minimum wage (FY 2024-25)
    EOBI_MIN_WAGE = 37_000

    def __init__(self):
        self.claw = get_openclaw()

    async def validate_payroll_run(
        self,
        run_id: str,
        db: AsyncSession,
    ) -> PayrollValidation:
        """
        Load a payroll run from DB, check for anomalies, ask Claude for a review.
        """
        context = await self._gather_run_context(run_id, db)
        if context is None:
            return PayrollValidation(
                recommendation="hold",
                summary="Payroll run not found — manual review required.",
            )

        rule_anomalies = self._rule_based_checks(context)

        prompt = self._build_prompt(context, rule_anomalies)
        response = await self.claw.think(
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )

        result = self._parse_response(response.content)
        result.anomalies = rule_anomalies + result.anomalies
        return result

    async def generate_payroll_summary(
        self,
        run_id: str,
        db: AsyncSession,
    ) -> str:
        """
        Generate a plain-English payroll summary for the HR manager dashboard.
        """
        context = await self._gather_run_context(run_id, db)
        if context is None:
            return "Payroll run data not available."

        prompt = (
            f"Write a 3-sentence payroll summary for the HR manager based on this data:\n"
            f"Month: {context['month']}/{context['year']}\n"
            f"Employees: {context['total_employees']}\n"
            f"Total Gross: PKR {context['total_gross']:,}\n"
            f"Total Net: PKR {context['total_net']:,}\n"
            f"Total Tax: PKR {context['total_income_tax']:,}\n"
            f"Total EOBI (employer): PKR {context['total_eobi_employer']:,}\n"
            f"Department breakdown: {context['departments']}\n"
            "Be professional and concise."
        )

        return await self.claw.simple_chat(
            prompt,
            system="You are an HR payroll summary writer. Write factual, concise summaries.",
        )

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _gather_run_context(
        self, run_id: str, db: AsyncSession
    ) -> dict | None:
        from app.models.payroll import PayrollRun, PayrollRecord
        from app.models.employee import Employee
        from app.models.employee import Department

        try:
            run_uuid = uuid.UUID(run_id)
        except ValueError:
            return None

        run_result = await db.execute(
            select(PayrollRun).where(PayrollRun.id == run_uuid)
        )
        run = run_result.scalar_one_or_none()
        if run is None:
            return None

        records_result = await db.execute(
            select(PayrollRecord).where(PayrollRecord.payroll_run_id == run_uuid)
        )
        records = records_result.scalars().all()

        dept_result = await db.execute(
            select(
                Department.name,
                func.count(PayrollRecord.id).label("emp_count"),
                func.sum(PayrollRecord.gross_salary).label("dept_gross"),
            )
            .join(Employee, Employee.id == PayrollRecord.employee_id)
            .join(Department, Department.id == Employee.department_id)
            .where(PayrollRecord.payroll_run_id == run_uuid)
            .group_by(Department.name)
        )
        dept_rows = dept_result.fetchall()

        context: dict[str, Any] = {
            "run_id":              run_id,
            "month":               run.month,
            "year":                run.year,
            "status":              run.status,
            "total_employees":     run.total_employees or len(records),
            "total_gross":         int(run.total_gross or 0),
            "total_net":           int(run.total_net or 0),
            "total_deductions":    int(run.total_deductions or 0),
            "total_income_tax":    int(run.total_income_tax or 0),
            "total_eobi_employer": int(run.total_eobi_employer or 0) if hasattr(run, "total_eobi_employer") else 0,
            "departments":         [
                {"name": r.name, "employees": r.emp_count, "gross": int(r.dept_gross or 0)}
                for r in dept_rows
            ],
            "records_sample": [
                {
                    "employee_id":   str(r.employee_id),
                    "gross_salary":  int(r.gross_salary or 0),
                    "net_salary":    int(r.net_salary or 0),
                    "income_tax":    int(r.income_tax or 0),
                    "eobi_employer": int(r.eobi_employer or 0),
                }
                for r in records[:50]
            ],
        }
        return context

    def _rule_based_checks(self, context: dict) -> list[dict]:
        anomalies = []

        for rec in context.get("records_sample", []):
            gross = rec["gross_salary"]
            net   = rec["net_salary"]
            tax   = rec["income_tax"]

            if gross > 0 and net == 0:
                anomalies.append({
                    "employee_id": rec["employee_id"],
                    "issue": "Net salary is zero — possible deduction error",
                    "severity": "high",
                })

            if gross > 600_000 and tax == 0:
                anomalies.append({
                    "employee_id": rec["employee_id"],
                    "issue": "No income tax deducted but gross exceeds PKR 600K annual threshold",
                    "severity": "medium",
                })

            expected_eobi = round(min(self.EOBI_MIN_WAGE, gross) * 0.05, 0)
            actual_eobi   = rec.get("eobi_employer", 0)
            if gross > 0 and abs(actual_eobi - expected_eobi) > 500:
                anomalies.append({
                    "employee_id": rec["employee_id"],
                    "issue": f"EOBI employer contribution mismatch: expected ~{expected_eobi}, got {actual_eobi}",
                    "severity": "low",
                })

        return anomalies

    def _build_prompt(self, context: dict, rule_anomalies: list[dict]) -> str:
        return (
            f"Review this payroll run and provide your analysis:\n\n"
            f"Run ID: {context['run_id']}\n"
            f"Period: {context['month']}/{context['year']}\n"
            f"Employees: {context['total_employees']}\n"
            f"Total Gross: PKR {context['total_gross']:,}\n"
            f"Total Net: PKR {context['total_net']:,}\n"
            f"Total Tax: PKR {context['total_income_tax']:,}\n"
            f"Department breakdown: {context['departments']}\n\n"
            f"Rule-based anomalies already detected: {rule_anomalies}\n\n"
            f"Sample records (first 10): {context['records_sample'][:10]}\n\n"
            "Return JSON only."
        )

    def _parse_response(self, raw: str) -> PayrollValidation:
        import json, re

        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                return PayrollValidation(
                    recommendation=data.get("recommendation", "hold"),
                    summary=data.get("summary", ""),
                    anomalies=data.get("anomalies", []),
                    compliance_flags=data.get("compliance_flags", []),
                    total_risk_score=int(data.get("total_risk_score", 0)),
                    raw_response=raw,
                )
            except json.JSONDecodeError:
                pass

        return PayrollValidation(
            recommendation="hold",
            summary=raw[:300],
            raw_response=raw,
        )


# ─── Singleton ────────────────────────────────────────────────────────────────

_payroll_agent: PayrollAgent | None = None


def get_payroll_agent() -> PayrollAgent:
    global _payroll_agent
    if _payroll_agent is None:
        _payroll_agent = PayrollAgent()
    return _payroll_agent

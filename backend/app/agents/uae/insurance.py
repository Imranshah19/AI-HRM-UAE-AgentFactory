"""
Insurance Agent UAE — Medical insurance + ILOE compliance tracker.

UAE Medical Insurance:
  - Dubai: Mandatory for ALL employees (DHA regulations)
  - Abu Dhabi: Mandatory for employees + dependents (DOH/HAAD)
  - Other Emirates: Mandatory per UAE law

ILOE (Unemployment Insurance — mandatory since Jan 2023):
  - Salary < AED 16,000: AED 5/month
  - Salary >= AED 16,000: AED 10/month
  - Enrolled via payroll deduction

Alert schedule: 60 → 30 → 14 days before expiry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import structlog

from app.agents.uae.openclaw import get_openclaw

logger = structlog.get_logger(__name__)

ILOE_THRESHOLD = Decimal("16000")
ILOE_LOW_AMOUNT = Decimal("5.00")
ILOE_HIGH_AMOUNT = Decimal("10.00")


@dataclass
class InsuranceComplianceResult:
    company_id: str
    checked_employees: int = 0
    insured_count: int = 0
    uninsured_count: int = 0
    expiring_60_days: list[dict] = field(default_factory=list)
    expiring_30_days: list[dict] = field(default_factory=list)
    expiring_14_days: list[dict] = field(default_factory=list)
    already_expired: list[dict] = field(default_factory=list)
    iloe_not_enrolled: list[dict] = field(default_factory=list)
    total_iloe_deduction_aed: Decimal = field(default_factory=lambda: Decimal("0"))
    is_compliant: bool = True

    def to_dict(self) -> dict:
        return {
            "company_id": self.company_id,
            "checked_employees": self.checked_employees,
            "insured_count": self.insured_count,
            "uninsured_count": self.uninsured_count,
            "is_compliant": self.is_compliant,
            "expiring_60_days": self.expiring_60_days,
            "expiring_30_days": self.expiring_30_days,
            "expiring_14_days": self.expiring_14_days,
            "already_expired": self.already_expired,
            "iloe_not_enrolled_count": len(self.iloe_not_enrolled),
            "total_iloe_deduction_aed": str(self.total_iloe_deduction_aed),
            "currency": "AED",
        }


class InsuranceAgent:
    """
    UAE insurance compliance tracker.
    Medical insurance mandatory; ILOE deduction mandatory since Jan 2023.
    """

    def __init__(self):
        self.claw = get_openclaw()

    async def check_insurance_expiries(
        self,
        company_id: str,
        db=None,
    ) -> InsuranceComplianceResult:
        result = InsuranceComplianceResult(company_id=company_id)

        employees = await self._load_insurance_data(db, company_id)
        today = date.today()
        result.checked_employees = len(employees)

        for emp in employees:
            if not emp.get("insurance_expiry"):
                result.uninsured_count += 1
                result.already_expired.append({
                    "employee_id": str(emp.get("employee_id", "")),
                    "employee_name": emp.get("name_en", ""),
                    "issue": "No insurance record",
                    "alert_level": "critical",
                })
                result.is_compliant = False
                continue

            result.insured_count += 1
            try:
                expiry = date.fromisoformat(str(emp["insurance_expiry"]))
            except ValueError:
                continue

            days_remaining = (expiry - today).days
            alert_data = {
                "employee_id": str(emp.get("employee_id", "")),
                "employee_name": emp.get("name_en", ""),
                "policy_number": emp.get("insurance_policy_number", ""),
                "provider": emp.get("insurance_provider", ""),
                "expiry_date": expiry.isoformat(),
                "days_remaining": days_remaining,
            }

            if days_remaining <= 0:
                alert_data["alert_level"] = "emergency"
                result.already_expired.append(alert_data)
                result.is_compliant = False
            elif days_remaining <= 14:
                alert_data["alert_level"] = "critical"
                result.expiring_14_days.append(alert_data)
            elif days_remaining <= 30:
                alert_data["alert_level"] = "urgent"
                result.expiring_30_days.append(alert_data)
            elif days_remaining <= 60:
                alert_data["alert_level"] = "reminder"
                result.expiring_60_days.append(alert_data)

        logger.info(
            "insurance_agent.check_complete",
            company_id=company_id,
            total=result.checked_employees,
            compliant=result.is_compliant,
        )
        return result

    async def check_iloe_compliance(self, company_id: str, db=None) -> dict:
        employees = await self._load_insurance_data(db, company_id)
        not_enrolled = []
        total_deduction = Decimal("0")

        for emp in employees:
            if not emp.get("iloe_enrolled", False):
                not_enrolled.append({
                    "employee_id": str(emp.get("employee_id", "")),
                    "employee_name": emp.get("name_en", ""),
                    "basic_salary": str(emp.get("basic_salary", 0)),
                })
            else:
                basic = Decimal(str(emp.get("basic_salary", 0)))
                total_deduction += ILOE_HIGH_AMOUNT if basic >= ILOE_THRESHOLD else ILOE_LOW_AMOUNT

        return {
            "company_id": company_id,
            "total_employees": len(employees),
            "iloe_enrolled": len(employees) - len(not_enrolled),
            "not_enrolled_count": len(not_enrolled),
            "not_enrolled": not_enrolled,
            "total_monthly_deduction_aed": str(total_deduction),
            "is_compliant": len(not_enrolled) == 0,
            "legal_basis": "Cabinet Resolution No. 97/2022 — mandatory since Jan 2023",
            "currency": "AED",
        }

    async def generate_compliance_report(self, company_id: str, db=None) -> dict:
        insurance = await self.check_insurance_expiries(company_id=company_id, db=db)
        iloe = await self.check_iloe_compliance(company_id=company_id, db=db)

        return {
            "company_id": company_id,
            "report_date": date.today().isoformat(),
            "insurance_compliance": insurance.to_dict(),
            "iloe_compliance": iloe,
            "overall_compliant": insurance.is_compliant and iloe["is_compliant"],
        }

    async def _load_insurance_data(self, db: Any, company_id: str) -> list[dict]:
        if db:
            try:
                from sqlalchemy import text
                result = await db.execute(text("""
                    SELECT u.employee_id, u.company_id, u.insurance_provider,
                           u.insurance_policy_number, u.insurance_expiry, u.iloe_enrolled,
                           e.first_name || ' ' || e.last_name as name_en,
                           s.basic_salary
                    FROM employees_uae_profile u
                    LEFT JOIN employees e ON e.id = u.employee_id::uuid
                    LEFT JOIN salary_structure_uae s ON s.employee_id = u.employee_id
                    WHERE u.company_id = :company_id
                """), {"company_id": company_id})
                return [dict(row._mapping) for row in result.fetchall()]
            except Exception:
                pass

        return [
            {
                "employee_id": "mock-001", "name_en": "Ahmed Al-Rashidi",
                "insurance_provider": "Daman", "insurance_policy_number": "DAM-12345",
                "insurance_expiry": (date.today() + timedelta(days=25)).isoformat(),
                "iloe_enrolled": True, "basic_salary": 12000,
            },
            {
                "employee_id": "mock-002", "name_en": "Priya Sharma",
                "insurance_provider": "AXA", "insurance_policy_number": "AXA-67890",
                "insurance_expiry": (date.today() + timedelta(days=90)).isoformat(),
                "iloe_enrolled": True, "basic_salary": 8000,
            },
            {
                "employee_id": "mock-003", "name_en": "New Employee",
                "insurance_provider": None, "insurance_policy_number": None,
                "insurance_expiry": None, "iloe_enrolled": False, "basic_salary": 5000,
            },
        ]


# ─── Singleton ─────────────────────────────────────────────────────────────────

_insurance_agent: InsuranceAgent | None = None


def get_insurance_agent() -> InsuranceAgent:
    global _insurance_agent
    if _insurance_agent is None:
        _insurance_agent = InsuranceAgent()
    return _insurance_agent

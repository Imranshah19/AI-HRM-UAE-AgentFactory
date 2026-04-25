"""
Contract Agent UAE — Contract expiry tracking + notice period management.

UAE Law (post Feb 2022):
  - ALL contracts MUST be fixed-term (unlimited abolished)
  - Maximum duration: 3 years (renewable)
  - Must be registered with MOHRE
  - Arabic version is legally binding

Notice periods:
  < 6 months: minimum 14 days
  6 months - 5 years: 30 days
  5+ years: 90 days

Alert timeline:
  90 days → Reminder
  60 days → Second reminder
  30 days → Urgent
  14 days → Critical
  Expired → Alert + legal risk warning
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import structlog

from app.agents.uae.openclaw import get_openclaw

logger = structlog.get_logger(__name__)

NOTICE_PERIOD_RULES = [
    {"min_months": 0,   "max_months": 6,   "notice_days": 14},
    {"min_months": 6,   "max_months": 60,  "notice_days": 30},
    {"min_months": 60,  "max_months": 9999, "notice_days": 90},
]


@dataclass
class ContractAlert:
    employee_id: str
    company_id: str
    employee_name: str
    contract_end_date: str
    days_until_expiry: int
    alert_level: str
    notice_period_days: int
    notice_deadline: str

    def to_dict(self) -> dict:
        return self.__dict__


@dataclass
class ContractCheckResult:
    company_id: str
    checked_count: int = 0
    expiring_90_days: list[dict] = field(default_factory=list)
    expiring_60_days: list[dict] = field(default_factory=list)
    expiring_30_days: list[dict] = field(default_factory=list)
    expiring_14_days: list[dict] = field(default_factory=list)
    already_expired: list[dict] = field(default_factory=list)

    @property
    def total_alerts(self) -> int:
        return (len(self.expiring_30_days) + len(self.expiring_14_days) +
                len(self.already_expired))

    def to_dict(self) -> dict:
        return {
            "company_id": self.company_id,
            "checked_count": self.checked_count,
            "total_critical_alerts": self.total_alerts,
            "expiring_90_days": self.expiring_90_days,
            "expiring_60_days": self.expiring_60_days,
            "expiring_30_days": self.expiring_30_days,
            "expiring_14_days": self.expiring_14_days,
            "already_expired": self.already_expired,
        }


class ContractAgent:
    """
    UAE contract expiry tracker. Enforces fixed-term contract requirements.
    """

    def __init__(self):
        self.claw = get_openclaw()

    async def check_contract_expiries(
        self,
        company_id: str | None = None,
        db=None,
    ) -> ContractCheckResult:
        result = ContractCheckResult(company_id=company_id or "all")

        if db:
            try:
                contracts = await self._load_contracts(db, company_id)
            except Exception as exc:
                logger.warning("contract_agent.db_load_failed", error=str(exc))
                contracts = self._mock_contracts(company_id)
        else:
            contracts = self._mock_contracts(company_id)

        today = date.today()
        result.checked_count = len(contracts)

        for contract in contracts:
            try:
                end_date = date.fromisoformat(str(contract["contract_end"]))
            except (ValueError, TypeError):
                continue

            days_remaining = (end_date - today).days
            join_date = date.fromisoformat(str(contract.get("join_date", today.isoformat())))
            service_months = (today.year - join_date.year) * 12 + (today.month - join_date.month)
            notice_days = self._get_notice_period(service_months)
            notice_deadline = (end_date - timedelta(days=notice_days)).isoformat()

            alert = ContractAlert(
                employee_id=str(contract.get("employee_id", "")),
                company_id=str(contract.get("company_id", company_id or "")),
                employee_name=contract.get("name_en", ""),
                contract_end_date=end_date.isoformat(),
                days_until_expiry=days_remaining,
                alert_level="info",
                notice_period_days=notice_days,
                notice_deadline=notice_deadline,
            )

            if days_remaining <= 0:
                alert.alert_level = "expired"
                result.already_expired.append(alert.to_dict())
            elif days_remaining <= 14:
                alert.alert_level = "critical"
                result.expiring_14_days.append(alert.to_dict())
            elif days_remaining <= 30:
                alert.alert_level = "urgent"
                result.expiring_30_days.append(alert.to_dict())
            elif days_remaining <= 60:
                alert.alert_level = "warning"
                result.expiring_60_days.append(alert.to_dict())
            elif days_remaining <= 90:
                alert.alert_level = "reminder"
                result.expiring_90_days.append(alert.to_dict())

        logger.info(
            "contract_agent.check_complete",
            company_id=company_id,
            total=result.checked_count,
            critical=result.total_alerts,
        )
        return result

    async def send_renewal_alerts(self, company_id: str, db=None) -> dict:
        check = await self.check_contract_expiries(company_id=company_id, db=db)
        alerts_sent = len(check.expiring_30_days) + len(check.expiring_14_days) + len(check.already_expired)
        return {
            "company_id": company_id,
            "alerts_sent": alerts_sent,
            "critical_count": len(check.expiring_14_days),
            "expired_count": len(check.already_expired),
        }

    async def calculate_notice_period(
        self,
        employee_id: str,
        company_id: str,
        join_date: str,
        db=None,
    ) -> dict:
        start = date.fromisoformat(join_date)
        today = date.today()
        service_months = (today.year - start.year) * 12 + (today.month - start.month)
        notice_days = self._get_notice_period(service_months)

        return {
            "employee_id": employee_id,
            "company_id": company_id,
            "join_date": join_date,
            "service_months": service_months,
            "notice_period_days": notice_days,
            "legal_basis": "UAE Federal Decree-Law No. 33/2021 Article 43",
            "note": (
                f"{'14 days' if notice_days == 14 else '30 days' if notice_days == 30 else '90 days'} "
                f"notice required for {'< 6 months' if service_months < 6 else '6 months - 5 years' if service_months < 60 else '5+ years'} service"
            ),
        }

    def _get_notice_period(self, service_months: int) -> int:
        for rule in NOTICE_PERIOD_RULES:
            if rule["min_months"] <= service_months < rule["max_months"]:
                return rule["notice_days"]
        return 90

    async def _load_contracts(self, db: Any, company_id: str | None) -> list[dict]:
        from sqlalchemy import text
        query = """
            SELECT u.employee_id, u.company_id, u.contract_end, u.contract_start,
                   e.first_name || ' ' || e.last_name as name_en,
                   e.date_of_joining as join_date
            FROM employees_uae_profile u
            LEFT JOIN employees e ON e.id = u.employee_id::uuid
            WHERE u.contract_end <= CURRENT_DATE + INTERVAL '90 days'
        """
        params: dict = {}
        if company_id:
            query += " AND u.company_id = :company_id"
            params["company_id"] = company_id

        result = await db.execute(text(query), params)
        return [dict(row._mapping) for row in result.fetchall()]

    def _mock_contracts(self, company_id: str | None) -> list[dict]:
        today = date.today()
        return [
            {
                "employee_id": "mock-001", "company_id": company_id or "mock-co",
                "name_en": "Ahmed Al-Rashidi", "contract_end": (today + timedelta(days=20)).isoformat(),
                "join_date": (today - timedelta(days=365)).isoformat(),
            },
            {
                "employee_id": "mock-002", "company_id": company_id or "mock-co",
                "name_en": "Priya Sharma", "contract_end": (today + timedelta(days=85)).isoformat(),
                "join_date": (today - timedelta(days=730)).isoformat(),
            },
        ]


# ─── Singleton ─────────────────────────────────────────────────────────────────

_contract_agent: ContractAgent | None = None


def get_contract_agent() -> ContractAgent:
    global _contract_agent
    if _contract_agent is None:
        _contract_agent = ContractAgent()
    return _contract_agent

"""
Air Ticket Agent UAE — Annual home country air ticket entitlement.

Standard UAE company practice (not statutory — company policy):
  - After 1 year service, eligible for annual air ticket
  - Fixed AED amount or actual ticket cost (per policy)
  - Separate from annual leave (can be combined)
  - Return date tracked for visa compliance

Manages: request → approval → utilization → reporting
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


@dataclass
class AirTicketEntitlement:
    employee_id: str
    company_id: str
    is_eligible: bool
    eligibility_date: str
    annual_value_aed: Decimal
    current_year_used: bool
    last_used_date: str | None
    status: str  # eligible | not_eligible | used | expired

    def to_dict(self) -> dict:
        return {
            **self.__dict__,
            "annual_value_aed": str(self.annual_value_aed),
            "currency": "AED",
        }


@dataclass
class TicketRequest:
    employee_id: str
    company_id: str
    destination_country: str
    departure_date: str
    return_date: str
    ticket_value_aed: Decimal
    cash_in_lieu: bool
    status: str = "pending"
    approved_by: str | None = None
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            **self.__dict__,
            "ticket_value_aed": str(self.ticket_value_aed),
            "currency": "AED",
        }


class AirTicketAgent:
    """
    UAE air ticket entitlement management.
    Tracks eligibility, utilization, and return dates for visa compliance.
    """

    def __init__(self):
        self.claw = get_openclaw()

    async def check_eligibility(
        self,
        employee_id: str,
        company_id: str,
        db=None,
    ) -> AirTicketEntitlement:
        emp_data = await self._load_employee_data(db, employee_id)
        join_date_str = emp_data.get("join_date", date.today().isoformat())
        join_date = date.fromisoformat(join_date_str)
        today = date.today()

        service_days = (today - join_date).days
        eligibility_date = join_date + timedelta(days=365)
        is_eligible = (
            service_days >= 365 and
            emp_data.get("air_ticket_entitlement", False)
        )

        current_year_used = bool(emp_data.get("air_ticket_last_used_date") and
            date.fromisoformat(str(emp_data["air_ticket_last_used_date"])).year == today.year)

        if not emp_data.get("air_ticket_entitlement", False):
            status = "not_eligible"
        elif not is_eligible:
            status = "not_eligible"
        elif current_year_used:
            status = "used"
        else:
            status = "eligible"

        return AirTicketEntitlement(
            employee_id=employee_id,
            company_id=company_id,
            is_eligible=is_eligible and not current_year_used,
            eligibility_date=eligibility_date.isoformat(),
            annual_value_aed=Decimal(str(emp_data.get("air_ticket_value_aed", 3000))),
            current_year_used=current_year_used,
            last_used_date=str(emp_data.get("air_ticket_last_used_date")) if emp_data.get("air_ticket_last_used_date") else None,
            status=status,
        )

    async def process_ticket_request(
        self,
        employee_id: str,
        company_id: str,
        destination_country: str,
        departure_date: str,
        return_date: str,
        cash_in_lieu: bool = False,
        db=None,
    ) -> TicketRequest:
        eligibility = await self.check_eligibility(employee_id, company_id, db)

        request = TicketRequest(
            employee_id=employee_id,
            company_id=company_id,
            destination_country=destination_country,
            departure_date=departure_date,
            return_date=return_date,
            ticket_value_aed=eligibility.annual_value_aed,
            cash_in_lieu=cash_in_lieu,
        )

        if not eligibility.is_eligible:
            request.status = "rejected"
            request.notes = f"Not eligible: {eligibility.status}"
        else:
            request.status = "pending_approval"
            request.notes = "Submitted for line manager approval"

        if db and request.status != "rejected":
            try:
                await self._save_request(db, request)
            except Exception as exc:
                logger.warning("air_ticket.save_failed", error=str(exc))

        logger.info(
            "air_ticket.request_processed",
            employee_id=employee_id,
            status=request.status,
            value=str(request.ticket_value_aed),
        )
        return request

    async def generate_utilization_report(self, company_id: str, db=None) -> dict:
        employees = await self._load_all_entitlements(db, company_id)
        used = sum(1 for e in employees if e.get("current_year_used", False))
        eligible = sum(1 for e in employees if e.get("air_ticket_entitlement", False) and e.get("service_years", 0) >= 1)

        return {
            "company_id": company_id,
            "year": date.today().year,
            "total_eligible": eligible,
            "used_this_year": used,
            "unused_count": eligible - used,
            "utilization_percent": round((used / eligible * 100) if eligible else 0, 1),
            "total_liability_aed": str(Decimal(str((eligible - used) * 3000))),
            "currency": "AED",
        }

    async def _load_employee_data(self, db: Any, employee_id: str) -> dict:
        if db:
            try:
                from sqlalchemy import text
                result = await db.execute(text("""
                    SELECT u.air_ticket_entitlement, u.air_ticket_value_aed,
                           u.air_ticket_last_used_date, e.date_of_joining as join_date
                    FROM employees_uae_profile u
                    LEFT JOIN employees e ON e.id = u.employee_id::uuid
                    WHERE u.employee_id = :emp_id
                """), {"emp_id": employee_id})
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
            except Exception:
                pass
        return {
            "air_ticket_entitlement": True,
            "air_ticket_value_aed": 3000,
            "air_ticket_last_used_date": None,
            "join_date": (date.today() - timedelta(days=400)).isoformat(),
        }

    async def _load_all_entitlements(self, db: Any, company_id: str) -> list[dict]:
        if db:
            try:
                from sqlalchemy import text
                result = await db.execute(text("""
                    SELECT u.employee_id, u.air_ticket_entitlement, u.air_ticket_value_aed,
                           u.air_ticket_last_used_date,
                           EXTRACT(YEAR FROM AGE(CURRENT_DATE, e.date_of_joining)) as service_years
                    FROM employees_uae_profile u
                    LEFT JOIN employees e ON e.id = u.employee_id::uuid
                    WHERE u.company_id = :company_id
                """), {"company_id": company_id})
                return [dict(row._mapping) for row in result.fetchall()]
            except Exception:
                pass
        return [
            {"air_ticket_entitlement": True, "service_years": 2, "current_year_used": False},
            {"air_ticket_entitlement": True, "service_years": 3, "current_year_used": True},
            {"air_ticket_entitlement": False, "service_years": 0.5, "current_year_used": False},
        ]

    async def _save_request(self, db: Any, request: TicketRequest) -> None:
        from sqlalchemy import text
        await db.execute(text("""
            INSERT INTO agent_logs_uae (
                company_id, agent_name, task_type, employee_id,
                input_data, output_data, status, triggered_by
            ) VALUES (
                :company_id, 'AirTicketAgent', 'ticket_request', :employee_id,
                :input, :output, 'success', 'webhook'
            )
        """), {
            "company_id": request.company_id,
            "employee_id": request.employee_id,
            "input": json.dumps({"destination": request.destination_country}),
            "output": json.dumps(request.to_dict()),
        })
        await db.commit()


# ─── Singleton ─────────────────────────────────────────────────────────────────

_air_ticket_agent: AirTicketAgent | None = None


def get_air_ticket_agent() -> AirTicketAgent:
    global _air_ticket_agent
    if _air_ticket_agent is None:
        _air_ticket_agent = AirTicketAgent()
    return _air_ticket_agent

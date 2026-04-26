"""
Insurance Agent UAE — LangGraph StateGraph for medical insurance + ILOE compliance.

UAE mandatory: All employees must have valid medical insurance (Dubai Health Authority /
Abu Dhabi Health Authority). ILOE (Involuntary Loss of Employment) mandatory since Oct 2023.

Nodes:
  fetch_insurance → check_expiry → check_iloe → send_alerts → generate_report

Alert tiers: CRITICAL (≤7 days), URGENT (≤30 days), WARNING (≤60 days).
Claude flags regulatory non-compliance risks.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    from langgraph.graph import StateGraph, START, END
    from typing_extensions import TypedDict
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from app.agents.uae.graph import claude_invoke, is_live_mode

ILOE_THRESHOLD = Decimal("16000")
ILOE_LOW = Decimal("5.00")
ILOE_HIGH = Decimal("10.00")

if LANGGRAPH_AVAILABLE:
    class InsuranceState(TypedDict):
        company_id: str
        employees: list
        insurance_records: list
        critical_expirations: list
        urgent_expirations: list
        warning_expirations: list
        iloe_non_compliant: list
        alerts_sent: bool
        report: dict
        api_mode: str


def _fetch_insurance(state: dict) -> dict:
    today = date.today()
    mock_records = [
        {"employee_id": "emp-001", "name": "Ahmed Al-Rashidi",
         "policy_number": "DHA-2024-001", "provider": "Daman",
         "expiry_date": (today + timedelta(days=5)).isoformat(),
         "basic_salary": "12000", "iloe_enrolled": True},
        {"employee_id": "emp-002", "name": "Priya Sharma",
         "policy_number": "DHA-2024-002", "provider": "AXA",
         "expiry_date": (today + timedelta(days=45)).isoformat(),
         "basic_salary": "8000", "iloe_enrolled": False},
        {"employee_id": "emp-003", "name": "Juan Santos",
         "policy_number": "DHA-2024-003", "provider": "Oman Insurance",
         "expiry_date": (today + timedelta(days=200)).isoformat(),
         "basic_salary": "5000", "iloe_enrolled": True},
    ]
    return {"insurance_records": state.get("insurance_records") or mock_records}


def _check_expiry(state: dict) -> dict:
    today = date.today()
    critical, urgent, warning = [], [], []

    for rec in state.get("insurance_records", []):
        try:
            expiry = date.fromisoformat(rec["expiry_date"])
            days = (expiry - today).days
        except (KeyError, ValueError):
            days = 999

        rec = {**rec, "days_to_expiry": days}
        if days <= 7:
            critical.append(rec)
        elif days <= 30:
            urgent.append(rec)
        elif days <= 60:
            warning.append(rec)

    return {
        "critical_expirations": critical,
        "urgent_expirations": urgent,
        "warning_expirations": warning,
    }


def _check_iloe(state: dict) -> dict:
    non_compliant = []
    for rec in state.get("insurance_records", []):
        if not rec.get("iloe_enrolled"):
            basic = Decimal(str(rec.get("basic_salary", "0")))
            monthly_premium = ILOE_HIGH if basic >= ILOE_THRESHOLD else ILOE_LOW
            non_compliant.append({
                **rec,
                "required_monthly_iloe": str(monthly_premium),
                "reason": "ILOE not enrolled — mandatory since Oct 2023",
            })
    return {"iloe_non_compliant": non_compliant}


def _send_alerts(state: dict) -> dict:
    for rec in state.get("critical_expirations", []):
        logger.error(
            "insurance.critical_expiry",
            employee=rec.get("name"),
            provider=rec.get("provider"),
            days=rec.get("days_to_expiry"),
        )
    for rec in state.get("iloe_non_compliant", []):
        logger.warning("insurance.iloe_missing", employee=rec.get("name"))
    return {"alerts_sent": True}


def _generate_report(state: dict) -> dict:
    critical = state.get("critical_expirations", [])
    iloe_nc = state.get("iloe_non_compliant", [])
    ai_note = ""

    if is_live_mode() and (critical or iloe_nc):
        prompt = (
            f"UAE insurance compliance issues for company {state.get('company_id')}: "
            f"Critical expirations: {len(critical)}, ILOE non-compliant: {len(iloe_nc)}. "
            "Advise on DHA/HAAD requirements, penalties, and remediation steps."
        )
        ai_note = claude_invoke(
            system="You are a UAE healthcare insurance compliance specialist.",
            user_message=prompt,
            max_tokens=512,
        )

    report = {
        "date": date.today().isoformat(),
        "company_id": state.get("company_id"),
        "total_records": len(state.get("insurance_records", [])),
        "critical_count": len(critical),
        "urgent_count": len(state.get("urgent_expirations", [])),
        "warning_count": len(state.get("warning_expirations", [])),
        "iloe_non_compliant_count": len(iloe_nc),
        "critical_expirations": critical,
        "iloe_non_compliant": iloe_nc,
        "ai_recommendation": ai_note,
        "api_mode": state.get("api_mode"),
    }
    return {"report": report}


_insurance_graph = None


def create_insurance_graph():
    global _insurance_graph
    if _insurance_graph is not None or not LANGGRAPH_AVAILABLE:
        return _insurance_graph

    g: StateGraph = StateGraph(InsuranceState)
    for name, fn in [
        ("fetch_insurance", _fetch_insurance),
        ("check_expiry", _check_expiry),
        ("check_iloe", _check_iloe),
        ("send_alerts", _send_alerts),
        ("generate_report", _generate_report),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "fetch_insurance")
    g.add_edge("fetch_insurance", "check_expiry")
    g.add_edge("check_expiry", "check_iloe")
    g.add_edge("check_iloe", "send_alerts")
    g.add_edge("send_alerts", "generate_report")
    g.add_edge("generate_report", END)

    _insurance_graph = g.compile()
    return _insurance_graph


async def run_agent(
    company_id: str,
    employee_id: Optional[str] = None,
    payload: dict | None = None,
    api_mode: str = "mock",
) -> dict:
    p = payload or {}
    initial: dict = {
        "company_id": company_id,
        "employees": p.get("employees", []),
        "insurance_records": p.get("insurance_records", []),
        "critical_expirations": [],
        "urgent_expirations": [],
        "warning_expirations": [],
        "iloe_non_compliant": [],
        "alerts_sent": False,
        "report": {},
        "api_mode": api_mode,
    }

    graph = create_insurance_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return final.get("report", {"company_id": company_id, "api_mode": api_mode})
        except Exception as exc:
            logger.exception("insurance_agent.error", error=str(exc))

    return {"company_id": company_id, "error": "LangGraph unavailable", "api_mode": api_mode}

"""
Gratuity Agent UAE — LangGraph StateGraph for end-of-service gratuity.

Federal Decree-Law No. 33/2021:
  - <1 yr service: no gratuity
  - 1–5 yr: 21 days basic per year
  - >5 yr: 30 days basic per year (capped at 2 years' salary)
  - Resignation <1yr: nil; 1–3yr: 1/3; 3–5yr: 2/3; >5yr: full

Nodes:
  fetch_service → determine_scenario → calculate_gratuity
  → calculate_settlement → generate_report

Claude validates complex edge cases.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
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

if LANGGRAPH_AVAILABLE:
    class GratuityState(TypedDict):
        company_id: str
        employee_id: str
        basic_salary: str
        join_date: str
        exit_date: str
        exit_reason: str          # "resignation" | "termination" | "completion"
        years_of_service: float
        gratuity_days: float
        gratuity_amount: str
        unpaid_salary: str
        leave_encashment: str
        total_settlement: str
        currency: str
        capped: bool
        notes: str
        api_mode: str


def _fetch_service(state: dict) -> dict:
    try:
        join = date.fromisoformat(state["join_date"])
        exit_ = date.fromisoformat(state.get("exit_date") or date.today().isoformat())
        delta = exit_ - join
        years = delta.days / 365.25
    except (KeyError, ValueError):
        years = 0.0
    return {"years_of_service": round(years, 4)}


def _determine_scenario(state: dict) -> dict:
    years = state.get("years_of_service", 0)
    reason = state.get("exit_reason", "resignation").lower()
    notes = ""

    if years < 1:
        notes = "Less than 1 year — no gratuity entitlement under UAE law."
    elif reason == "resignation":
        if 1 <= years < 3:
            notes = "Resignation 1–3yr: 1/3 of full gratuity."
        elif 3 <= years < 5:
            notes = "Resignation 3–5yr: 2/3 of full gratuity."
        else:
            notes = "Resignation >5yr: full gratuity."
    else:
        notes = f"Termination/completion — full gratuity entitlement ({round(years, 1)} years)."

    return {"notes": notes}


def _calculate_gratuity(state: dict) -> dict:
    years = state.get("years_of_service", 0)
    basic = Decimal(str(state.get("basic_salary", "0")))
    reason = state.get("exit_reason", "resignation").lower()
    daily_rate = basic / Decimal("30")

    if years < 1:
        return {"gratuity_days": 0.0, "gratuity_amount": "0.00", "capped": False}

    if years <= 5:
        days = Decimal(str(min(years, 5))) * Decimal("21")
    else:
        days = Decimal("5") * Decimal("21") + (Decimal(str(years)) - Decimal("5")) * Decimal("30")

    # Resignation reduction
    if reason == "resignation":
        if years < 3:
            days = days * Decimal("0.3333")
        elif years < 5:
            days = days * Decimal("0.6667")

    amount = (daily_rate * days).quantize(Decimal("0.01"), ROUND_HALF_UP)

    # Cap at 2 years' salary (Art. 51 §3: max = 24 months × basic)
    cap = (basic * Decimal("24")).quantize(Decimal("0.01"), ROUND_HALF_UP)
    capped = amount > cap
    if capped:
        amount = cap

    return {
        "gratuity_days": float(days.quantize(Decimal("0.01"))),
        "gratuity_amount": str(amount),
        "capped": capped,
    }


def _calculate_settlement(state: dict) -> dict:
    gratuity = Decimal(str(state.get("gratuity_amount", "0")))
    unpaid = Decimal(str(state.get("unpaid_salary", "0")))
    leave_enc = Decimal(str(state.get("leave_encashment", "0")))
    total = (gratuity + unpaid + leave_enc).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return {"total_settlement": str(total), "currency": "AED"}


def _generate_report(state: dict) -> dict:
    ai_note = ""
    if is_live_mode() and state.get("capped"):
        prompt = (
            f"UAE gratuity capped at 2 years salary for employee {state.get('employee_id')}. "
            f"Years: {state.get('years_of_service')}, basic: AED {state.get('basic_salary')}, "
            f"exit: {state.get('exit_reason')}. Confirm calculation and advise."
        )
        ai_note = claude_invoke(
            system="You are a UAE end-of-service gratuity specialist.",
            user_message=prompt,
            max_tokens=256,
        )

    logger.info(
        "gratuity.calculated",
        employee_id=state.get("employee_id"),
        years=state.get("years_of_service"),
        total=state.get("total_settlement"),
    )
    return {"notes": state.get("notes", "") + (" | " + ai_note if ai_note else "")}


_gratuity_graph = None


def create_gratuity_graph():
    global _gratuity_graph
    if _gratuity_graph is not None or not LANGGRAPH_AVAILABLE:
        return _gratuity_graph

    g: StateGraph = StateGraph(GratuityState)
    for name, fn in [
        ("fetch_service", _fetch_service),
        ("determine_scenario", _determine_scenario),
        ("calculate_gratuity", _calculate_gratuity),
        ("calculate_settlement", _calculate_settlement),
        ("generate_report", _generate_report),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "fetch_service")
    g.add_edge("fetch_service", "determine_scenario")
    g.add_edge("determine_scenario", "calculate_gratuity")
    g.add_edge("calculate_gratuity", "calculate_settlement")
    g.add_edge("calculate_settlement", "generate_report")
    g.add_edge("generate_report", END)

    _gratuity_graph = g.compile()
    return _gratuity_graph


async def run_agent(
    company_id: str,
    employee_id: Optional[str] = None,
    payload: dict | None = None,
    api_mode: str = "mock",
) -> dict:
    p = payload or {}
    initial: dict = {
        "company_id": company_id,
        "employee_id": employee_id or p.get("employee_id", ""),
        "basic_salary": str(p.get("basic_salary", "10000")),
        "join_date": p.get("join_date", "2020-01-01"),
        "exit_date": p.get("exit_date", date.today().isoformat()),
        "exit_reason": p.get("exit_reason", "resignation"),
        "years_of_service": 0.0,
        "gratuity_days": 0.0,
        "gratuity_amount": "0",
        "unpaid_salary": str(p.get("unpaid_salary", "0")),
        "leave_encashment": str(p.get("leave_encashment", "0")),
        "total_settlement": "0",
        "currency": "AED",
        "capped": False,
        "notes": "",
        "api_mode": api_mode,
    }

    graph = create_gratuity_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return {
                "employee_id": final.get("employee_id"),
                "company_id": company_id,
                "years_of_service": final.get("years_of_service"),
                "gratuity_days": final.get("gratuity_days"),
                "gratuity_amount": final.get("gratuity_amount"),
                "unpaid_salary": final.get("unpaid_salary"),
                "leave_encashment": final.get("leave_encashment"),
                "total_settlement": final.get("total_settlement"),
                "currency": "AED",
                "capped": final.get("capped"),
                "notes": final.get("notes"),
                "api_mode": api_mode,
            }
        except Exception as exc:
            logger.exception("gratuity_agent.error", error=str(exc))

    return {"company_id": company_id, "error": "LangGraph unavailable", "api_mode": api_mode}

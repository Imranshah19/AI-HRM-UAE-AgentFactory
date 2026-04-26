"""
Air Ticket Agent UAE — LangGraph StateGraph for annual home-country air ticket.

UAE Practice: Most expatriate contracts include one annual air ticket to home country.
Entitlement typically after completing 1 year of service.

Nodes:
  fetch_entitlement → check_eligibility → process_request → calculate_value
  → send_approval → track_return → generate_report → log_done

Claude validates complex multi-leg / family ticket requests.
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

# Average ticket value by region (AED)
REGION_TICKET_VALUE: dict[str, Decimal] = {
    "south_asia": Decimal("1500"),
    "southeast_asia": Decimal("2200"),
    "middle_east": Decimal("800"),
    "africa": Decimal("2500"),
    "europe": Decimal("3500"),
    "north_america": Decimal("5000"),
    "other": Decimal("2000"),
}

if LANGGRAPH_AVAILABLE:
    class AirTicketState(TypedDict):
        company_id: str
        employee_id: str
        employee_name: str
        nationality: str
        home_country: str
        join_date: str
        ticket_type: str        # "economy" | "business"
        includes_family: bool
        family_members: int
        years_of_service: float
        eligible: bool
        eligibility_reason: str
        ticket_value_aed: str
        approved: bool
        return_date: str
        report: dict
        api_mode: str


def _fetch_entitlement(state: dict) -> dict:
    try:
        join = date.fromisoformat(state.get("join_date", "2020-01-01"))
        years = (date.today() - join).days / 365.25
    except ValueError:
        years = 0.0
    return {"years_of_service": round(years, 2)}


def _check_eligibility(state: dict) -> dict:
    years = state.get("years_of_service", 0)
    if years < 1:
        return {
            "eligible": False,
            "eligibility_reason": f"Less than 1 year of service ({round(years, 1)} years)",
        }
    return {
        "eligible": True,
        "eligibility_reason": f"Eligible — {round(years, 1)} years of service",
    }


def _process_request(state: dict) -> dict:
    if not state.get("eligible"):
        return {}
    logger.info(
        "air_ticket.request_processed",
        employee_id=state.get("employee_id"),
        home_country=state.get("home_country"),
    )
    return {}


def _calculate_value(state: dict) -> dict:
    if not state.get("eligible"):
        return {"ticket_value_aed": "0.00"}

    home = (state.get("home_country") or "").lower()
    region = "other"
    if any(c in home for c in ["india", "pakistan", "bangladesh", "sri lanka", "nepal"]):
        region = "south_asia"
    elif any(c in home for c in ["philippines", "indonesia", "malaysia", "thailand"]):
        region = "southeast_asia"
    elif any(c in home for c in ["egypt", "jordan", "lebanon", "syria"]):
        region = "middle_east"
    elif any(c in home for c in ["uk", "germany", "france", "italy", "spain"]):
        region = "europe"
    elif any(c in home for c in ["usa", "canada", "united states"]):
        region = "north_america"

    base = REGION_TICKET_VALUE.get(region, REGION_TICKET_VALUE["other"])

    if state.get("ticket_type") == "business":
        base = base * Decimal("2.5")

    if state.get("includes_family"):
        members = max(1, int(state.get("family_members", 1)))
        base = base * Decimal(str(members))

    return {"ticket_value_aed": str(base.quantize(Decimal("0.01"), ROUND_HALF_UP))}


def _send_approval(state: dict) -> dict:
    if not state.get("eligible"):
        return {"approved": False}
    logger.info(
        "air_ticket.approved",
        employee_id=state.get("employee_id"),
        value=state.get("ticket_value_aed"),
    )
    return {"approved": True}


def _track_return(state: dict) -> dict:
    logger.info(
        "air_ticket.return_tracked",
        employee_id=state.get("employee_id"),
        return_date=state.get("return_date"),
    )
    return {}


def _generate_report(state: dict) -> dict:
    ai_note = ""
    if is_live_mode() and state.get("includes_family") and int(state.get("family_members", 0)) > 3:
        prompt = (
            f"Large family air ticket request: employee {state.get('employee_name')}, "
            f"{state.get('family_members')} members, value AED {state.get('ticket_value_aed')}. "
            "Verify entitlement and advise on approval conditions."
        )
        ai_note = claude_invoke(
            system="You are a UAE HR air ticket entitlement specialist.",
            user_message=prompt,
            max_tokens=256,
        )

    report = {
        "date": date.today().isoformat(),
        "company_id": state.get("company_id"),
        "employee_id": state.get("employee_id"),
        "employee_name": state.get("employee_name"),
        "eligible": state.get("eligible"),
        "eligibility_reason": state.get("eligibility_reason"),
        "ticket_value_aed": state.get("ticket_value_aed"),
        "approved": state.get("approved"),
        "ticket_type": state.get("ticket_type"),
        "includes_family": state.get("includes_family"),
        "family_members": state.get("family_members"),
        "ai_notes": ai_note,
        "currency": "AED",
        "api_mode": state.get("api_mode"),
    }
    return {"report": report}


def _log_done(state: dict) -> dict:
    logger.info(
        "air_ticket.completed",
        employee_id=state.get("employee_id"),
        approved=state.get("approved"),
        value=state.get("ticket_value_aed"),
    )
    return {}


_air_ticket_graph = None


def create_air_ticket_graph():
    global _air_ticket_graph
    if _air_ticket_graph is not None or not LANGGRAPH_AVAILABLE:
        return _air_ticket_graph

    g: StateGraph = StateGraph(AirTicketState)
    for name, fn in [
        ("fetch_entitlement", _fetch_entitlement),
        ("check_eligibility", _check_eligibility),
        ("process_request", _process_request),
        ("calculate_value", _calculate_value),
        ("send_approval", _send_approval),
        ("track_return", _track_return),
        ("generate_report", _generate_report),
        ("log_done", _log_done),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "fetch_entitlement")
    g.add_edge("fetch_entitlement", "check_eligibility")
    g.add_edge("check_eligibility", "process_request")
    g.add_edge("process_request", "calculate_value")
    g.add_edge("calculate_value", "send_approval")
    g.add_edge("send_approval", "track_return")
    g.add_edge("track_return", "generate_report")
    g.add_edge("generate_report", "log_done")
    g.add_edge("log_done", END)

    _air_ticket_graph = g.compile()
    return _air_ticket_graph


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
        "employee_name": p.get("employee_name", ""),
        "nationality": p.get("nationality", ""),
        "home_country": p.get("home_country", "india"),
        "join_date": p.get("join_date", "2020-01-01"),
        "ticket_type": p.get("ticket_type", "economy"),
        "includes_family": p.get("includes_family", False),
        "family_members": int(p.get("family_members", 1)),
        "years_of_service": 0.0,
        "eligible": False,
        "eligibility_reason": "",
        "ticket_value_aed": "0.00",
        "approved": False,
        "return_date": p.get("return_date", ""),
        "report": {},
        "api_mode": api_mode,
    }

    graph = create_air_ticket_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return final.get("report", {"company_id": company_id, "api_mode": api_mode})
        except Exception as exc:
            logger.exception("air_ticket_agent.error", error=str(exc))

    return {"company_id": company_id, "error": "LangGraph unavailable", "api_mode": api_mode}

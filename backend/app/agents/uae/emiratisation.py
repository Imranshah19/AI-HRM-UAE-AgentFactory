"""
Emiratisation Agent UAE — LangGraph StateGraph for Nafis quota compliance.

MOHRE Emiratisation Targets (2024+):
  Private sector companies ≥50 employees: 2% Emirati quota per year
  Banking/finance sector: stricter targets apply
  NAFIS program: government subsidy for Emirati private-sector hires

Nodes:
  fetch_headcount → calculate_pct → calculate_fine → send_alert
  → identify_nafis → generate_report → log_done

Fine: AED 96,000/year per unfilled Emirati slot.
Claude recommends NAFIS-eligible roles.
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

ANNUAL_FINE_PER_SLOT = Decimal("96000")
MONTHLY_FINE_PER_SLOT = ANNUAL_FINE_PER_SLOT / Decimal("12")
QUOTA_THRESHOLD_EMPLOYEES = 50
ANNUAL_QUOTA_PCT = Decimal("0.02")  # 2% per year

if LANGGRAPH_AVAILABLE:
    class EmiratisationState(TypedDict):
        company_id: str
        total_employees: int
        emirati_employees: int
        sector: str
        year: int
        current_pct: float
        required_pct: float
        required_emiratis: int
        shortfall: int
        monthly_fine_aed: str
        annual_fine_aed: str
        compliant: bool
        nafis_eligible_roles: list
        alert_sent: bool
        report: dict
        ai_recommendation: str
        api_mode: str


def _fetch_headcount(state: dict) -> dict:
    mock_total = state.get("total_employees") or 120
    mock_emiratis = state.get("emirati_employees") or 2
    return {
        "total_employees": mock_total,
        "emirati_employees": mock_emiratis,
    }


def _calculate_pct(state: dict) -> dict:
    total = state.get("total_employees", 0)
    emiratis = state.get("emirati_employees", 0)
    sector = (state.get("sector") or "general").lower()

    if total == 0:
        return {"current_pct": 0.0, "required_pct": 0.0, "required_emiratis": 0, "shortfall": 0, "compliant": True}

    current_pct = (emiratis / total) * 100

    # Required % depends on sector
    if sector in ("banking", "finance", "financial_services"):
        required_pct = 5.0
    else:
        required_pct = float(ANNUAL_QUOTA_PCT * 100)  # 2%

    required_emiratis = max(0, int((required_pct / 100) * total))
    shortfall = max(0, required_emiratis - emiratis)
    compliant = shortfall == 0 or total < QUOTA_THRESHOLD_EMPLOYEES

    return {
        "current_pct": round(current_pct, 2),
        "required_pct": required_pct,
        "required_emiratis": required_emiratis,
        "shortfall": shortfall,
        "compliant": compliant,
    }


def _calculate_fine(state: dict) -> dict:
    shortfall = state.get("shortfall", 0)
    if state.get("compliant") or shortfall == 0:
        return {"monthly_fine_aed": "0.00", "annual_fine_aed": "0.00"}

    monthly = (MONTHLY_FINE_PER_SLOT * Decimal(str(shortfall))).quantize(Decimal("0.01"), ROUND_HALF_UP)
    annual = (ANNUAL_FINE_PER_SLOT * Decimal(str(shortfall))).quantize(Decimal("0.01"), ROUND_HALF_UP)
    return {"monthly_fine_aed": str(monthly), "annual_fine_aed": str(annual)}


def _send_alert(state: dict) -> dict:
    if not state.get("compliant"):
        logger.warning(
            "emiratisation.non_compliant",
            company_id=state.get("company_id"),
            shortfall=state.get("shortfall"),
            annual_fine=state.get("annual_fine_aed"),
        )
    return {"alert_sent": True}


def _identify_nafis(state: dict) -> dict:
    shortfall = state.get("shortfall", 0)
    if shortfall == 0:
        return {"nafis_eligible_roles": []}

    # Typical NAFIS-eligible roles (MOHRE-approved)
    nafis_roles = [
        {"role": "HR Coordinator", "grade": "mid", "nafis_subsidy_aed": "8000/month"},
        {"role": "Finance Analyst", "grade": "mid", "nafis_subsidy_aed": "8000/month"},
        {"role": "Customer Service Rep", "grade": "junior", "nafis_subsidy_aed": "5000/month"},
        {"role": "IT Support Specialist", "grade": "mid", "nafis_subsidy_aed": "8000/month"},
        {"role": "Admin Officer", "grade": "junior", "nafis_subsidy_aed": "5000/month"},
    ]
    return {"nafis_eligible_roles": nafis_roles[:shortfall]}


def _generate_report(state: dict) -> dict:
    ai_recommendation = ""
    if is_live_mode() and not state.get("compliant"):
        prompt = (
            f"UAE Emiratisation non-compliance: company {state.get('company_id')}, "
            f"sector={state.get('sector')}, total={state.get('total_employees')}, "
            f"Emirati={state.get('emirati_employees')}, required={state.get('required_emiratis')}, "
            f"shortfall={state.get('shortfall')}, fine=AED {state.get('annual_fine_aed')}/yr. "
            "Recommend hiring strategy and NAFIS utilization to achieve compliance."
        )
        ai_recommendation = claude_invoke(
            system="You are a UAE Emiratisation (Nafis) compliance specialist.",
            user_message=prompt,
            max_tokens=512,
        )

    report = {
        "date": date.today().isoformat(),
        "company_id": state.get("company_id"),
        "year": state.get("year", date.today().year),
        "total_employees": state.get("total_employees"),
        "emirati_employees": state.get("emirati_employees"),
        "current_pct": state.get("current_pct"),
        "required_pct": state.get("required_pct"),
        "required_emiratis": state.get("required_emiratis"),
        "shortfall": state.get("shortfall"),
        "compliant": state.get("compliant"),
        "monthly_fine_aed": state.get("monthly_fine_aed"),
        "annual_fine_aed": state.get("annual_fine_aed"),
        "nafis_eligible_roles": state.get("nafis_eligible_roles", []),
        "currency": "AED",
        "api_mode": state.get("api_mode"),
    }
    return {"report": report, "ai_recommendation": ai_recommendation}


def _log_done(state: dict) -> dict:
    logger.info(
        "emiratisation.completed",
        company_id=state.get("company_id"),
        compliant=state.get("compliant"),
        shortfall=state.get("shortfall"),
    )
    return {}


_emiratisation_graph = None


def create_emiratisation_graph():
    global _emiratisation_graph
    if _emiratisation_graph is not None or not LANGGRAPH_AVAILABLE:
        return _emiratisation_graph

    g: StateGraph = StateGraph(EmiratisationState)
    for name, fn in [
        ("fetch_headcount", _fetch_headcount),
        ("calculate_pct", _calculate_pct),
        ("calculate_fine", _calculate_fine),
        ("send_alert", _send_alert),
        ("identify_nafis", _identify_nafis),
        ("generate_report", _generate_report),
        ("log_done", _log_done),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "fetch_headcount")
    g.add_edge("fetch_headcount", "calculate_pct")
    g.add_edge("calculate_pct", "calculate_fine")
    g.add_edge("calculate_fine", "send_alert")
    g.add_edge("send_alert", "identify_nafis")
    g.add_edge("identify_nafis", "generate_report")
    g.add_edge("generate_report", "log_done")
    g.add_edge("log_done", END)

    _emiratisation_graph = g.compile()
    return _emiratisation_graph


async def run_agent(
    company_id: str,
    employee_id: Optional[str] = None,
    payload: dict | None = None,
    api_mode: str = "mock",
) -> dict:
    p = payload or {}
    initial: dict = {
        "company_id": company_id,
        "total_employees": int(p.get("total_employees", 0)),
        "emirati_employees": int(p.get("emirati_employees", 0)),
        "sector": p.get("sector", "general"),
        "year": int(p.get("year", date.today().year)),
        "current_pct": 0.0,
        "required_pct": 0.0,
        "required_emiratis": 0,
        "shortfall": 0,
        "monthly_fine_aed": "0.00",
        "annual_fine_aed": "0.00",
        "compliant": True,
        "nafis_eligible_roles": [],
        "alert_sent": False,
        "report": {},
        "ai_recommendation": "",
        "api_mode": api_mode,
    }

    graph = create_emiratisation_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return {
                **final.get("report", {}),
                "ai_recommendation": final.get("ai_recommendation", ""),
            }
        except Exception as exc:
            logger.exception("emiratisation_agent.error", error=str(exc))

    return {"company_id": company_id, "error": "LangGraph unavailable", "api_mode": api_mode}

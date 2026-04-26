"""
Contract Agent UAE — LangGraph StateGraph for contract lifecycle management.

UAE Labour contracts: Limited (fixed-term, max 2yr, renewable) per
Federal Decree-Law No. 33/2021.

Nodes:
  fetch_contracts → calculate_timelines → send_renewal_alerts → generate_report

Alert tiers: CRITICAL (≤30 days), URGENT (≤60 days), WARNING (≤90 days).
Claude drafts renewal recommendations for at-risk contracts.
"""

from __future__ import annotations

from datetime import date, timedelta
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
    class ContractState(TypedDict):
        company_id: str
        contracts: list
        enriched_contracts: list
        critical_contracts: list
        urgent_contracts: list
        warning_contracts: list
        alerts_sent: bool
        report: dict
        api_mode: str


def _fetch_contracts(state: dict) -> dict:
    today = date.today()
    mock_contracts = [
        {"employee_id": "emp-001", "name": "Ahmed Al-Rashidi",
         "contract_type": "limited", "expiry_date": (today + timedelta(days=20)).isoformat(),
         "notice_period_days": 30, "department": "Engineering"},
        {"employee_id": "emp-002", "name": "Priya Sharma",
         "contract_type": "limited", "expiry_date": (today + timedelta(days=55)).isoformat(),
         "notice_period_days": 30, "department": "Finance"},
        {"employee_id": "emp-003", "name": "Juan Santos",
         "contract_type": "unlimited", "expiry_date": None,
         "notice_period_days": 30, "department": "Operations"},
    ]
    return {"contracts": state.get("contracts") or mock_contracts}


def _calculate_timelines(state: dict) -> dict:
    today = date.today()
    critical, urgent, warning, enriched = [], [], [], []

    for c in state.get("contracts", []):
        expiry_str = c.get("expiry_date")
        if not expiry_str:
            enriched.append({**c, "days_to_expiry": None, "status": "unlimited"})
            continue
        try:
            expiry = date.fromisoformat(expiry_str)
            days = (expiry - today).days
        except ValueError:
            enriched.append({**c, "days_to_expiry": None, "status": "unknown"})
            continue

        notice = c.get("notice_period_days", 30)
        action_by = days - notice

        enriched_c = {**c, "days_to_expiry": days, "action_required_by_days": action_by}

        if days <= 0:
            enriched_c["status"] = "expired"
            critical.append(enriched_c)
        elif days <= 30:
            enriched_c["status"] = "critical"
            critical.append(enriched_c)
        elif days <= 60:
            enriched_c["status"] = "urgent"
            urgent.append(enriched_c)
        elif days <= 90:
            enriched_c["status"] = "warning"
            warning.append(enriched_c)
        else:
            enriched_c["status"] = "ok"

        enriched.append(enriched_c)

    return {
        "enriched_contracts": enriched,
        "critical_contracts": critical,
        "urgent_contracts": urgent,
        "warning_contracts": warning,
    }


def _send_renewal_alerts(state: dict) -> dict:
    for c in state.get("critical_contracts", []):
        logger.warning(
            "contract.critical_expiry",
            employee=c.get("name"),
            days=c.get("days_to_expiry"),
            company_id=state.get("company_id"),
        )
    for c in state.get("urgent_contracts", []):
        logger.info(
            "contract.urgent_expiry",
            employee=c.get("name"),
            days=c.get("days_to_expiry"),
        )
    return {"alerts_sent": True}


def _generate_report(state: dict) -> dict:
    critical = state.get("critical_contracts", [])
    ai_recommendation = ""

    if is_live_mode() and critical:
        prompt = (
            f"UAE labour contracts expiring critically for company {state.get('company_id')}: "
            f"{[{'name': c['name'], 'days': c.get('days_to_expiry'), 'dept': c.get('department')} for c in critical]}. "
            "Recommend: renew, terminate, or convert to unlimited. Include MOHRE notice requirements."
        )
        ai_recommendation = claude_invoke(
            system="You are a UAE Federal Decree-Law No. 33/2021 labour contract specialist.",
            user_message=prompt,
            max_tokens=512,
        )

    report = {
        "date": date.today().isoformat(),
        "company_id": state.get("company_id"),
        "total_contracts": len(state.get("enriched_contracts", [])),
        "critical_count": len(state.get("critical_contracts", [])),
        "urgent_count": len(state.get("urgent_contracts", [])),
        "warning_count": len(state.get("warning_contracts", [])),
        "critical_contracts": critical,
        "urgent_contracts": state.get("urgent_contracts", []),
        "ai_recommendation": ai_recommendation,
        "api_mode": state.get("api_mode"),
    }
    return {"report": report}


_contract_graph = None


def create_contract_graph():
    global _contract_graph
    if _contract_graph is not None or not LANGGRAPH_AVAILABLE:
        return _contract_graph

    g: StateGraph = StateGraph(ContractState)
    for name, fn in [
        ("fetch_contracts", _fetch_contracts),
        ("calculate_timelines", _calculate_timelines),
        ("send_renewal_alerts", _send_renewal_alerts),
        ("generate_report", _generate_report),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "fetch_contracts")
    g.add_edge("fetch_contracts", "calculate_timelines")
    g.add_edge("calculate_timelines", "send_renewal_alerts")
    g.add_edge("send_renewal_alerts", "generate_report")
    g.add_edge("generate_report", END)

    _contract_graph = g.compile()
    return _contract_graph


async def run_agent(
    company_id: str,
    employee_id: Optional[str] = None,
    payload: dict | None = None,
    api_mode: str = "mock",
) -> dict:
    p = payload or {}
    initial: dict = {
        "company_id": company_id,
        "contracts": p.get("contracts", []),
        "enriched_contracts": [],
        "critical_contracts": [],
        "urgent_contracts": [],
        "warning_contracts": [],
        "alerts_sent": False,
        "report": {},
        "api_mode": api_mode,
    }

    graph = create_contract_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return final.get("report", {"company_id": company_id, "api_mode": api_mode})
        except Exception as exc:
            logger.exception("contract_agent.error", error=str(exc))

    return {"company_id": company_id, "error": "LangGraph unavailable", "api_mode": api_mode}

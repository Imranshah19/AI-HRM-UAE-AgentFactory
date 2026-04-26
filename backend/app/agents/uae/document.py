"""
Document Agent UAE — LangGraph StateGraph for document expiry tracking.

Tracks: Emirates ID, Visa, Labour Card, Passport, Medical Fitness,
        Trade License, Establishment Card, Insurance certificates.

Nodes:
  fetch_docs → calculate_expiry → categorize_urgency
  → send_alerts → generate_report

Alert tiers: CRITICAL (≤7 days), URGENT (≤30 days), WARNING (≤90 days).
Claude generates prioritised action plan for CRITICAL documents.
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

ALERT_TIERS = {
    "critical": 7,
    "urgent": 30,
    "warning": 90,
}

if LANGGRAPH_AVAILABLE:
    class DocumentState(TypedDict):
        company_id: str
        employee_id: str
        documents: list
        enriched_docs: list
        critical_docs: list
        urgent_docs: list
        warning_docs: list
        alerts_sent: bool
        report: dict
        ai_action_plan: str
        api_mode: str


def _fetch_docs(state: dict) -> dict:
    today = date.today()
    mock_docs = [
        {"type": "Emirates ID", "employee_id": "emp-001", "name": "Ahmed Al-Rashidi",
         "expiry_date": (today + timedelta(days=5)).isoformat()},
        {"type": "Visa", "employee_id": "emp-002", "name": "Priya Sharma",
         "expiry_date": (today + timedelta(days=25)).isoformat()},
        {"type": "Labour Card", "employee_id": "emp-003", "name": "Juan Santos",
         "expiry_date": (today + timedelta(days=80)).isoformat()},
        {"type": "Passport", "employee_id": "emp-001", "name": "Ahmed Al-Rashidi",
         "expiry_date": (today + timedelta(days=200)).isoformat()},
        {"type": "Trade License", "employee_id": None, "name": "Company",
         "expiry_date": (today + timedelta(days=3)).isoformat()},
    ]
    docs = state.get("documents") or mock_docs
    return {"documents": docs}


def _calculate_expiry(state: dict) -> dict:
    today = date.today()
    enriched = []
    for doc in state.get("documents", []):
        try:
            expiry = date.fromisoformat(doc["expiry_date"])
            days_left = (expiry - today).days
        except (KeyError, ValueError):
            days_left = 999
        enriched.append({**doc, "days_left": days_left, "expired": days_left < 0})
    return {"enriched_docs": enriched}


def _categorize_urgency(state: dict) -> dict:
    critical, urgent, warning = [], [], []
    for doc in state.get("enriched_docs", []):
        d = doc["days_left"]
        if doc.get("expired") or d <= ALERT_TIERS["critical"]:
            critical.append(doc)
        elif d <= ALERT_TIERS["urgent"]:
            urgent.append(doc)
        elif d <= ALERT_TIERS["warning"]:
            warning.append(doc)
    return {"critical_docs": critical, "urgent_docs": urgent, "warning_docs": warning}


def _send_alerts(state: dict) -> dict:
    for doc in state.get("critical_docs", []):
        logger.warning(
            "document.critical_alert",
            doc_type=doc["type"],
            employee=doc.get("name"),
            days_left=doc["days_left"],
        )
    for doc in state.get("urgent_docs", []):
        logger.info(
            "document.urgent_alert",
            doc_type=doc["type"],
            employee=doc.get("name"),
            days_left=doc["days_left"],
        )
    return {"alerts_sent": True}


def _generate_report(state: dict) -> dict:
    ai_action_plan = ""
    critical = state.get("critical_docs", [])

    if is_live_mode() and critical:
        prompt = (
            f"UAE document compliance — CRITICAL expirations: {critical}. "
            f"Company: {state.get('company_id')}. "
            "Create a prioritised action plan with MOHRE/ICP steps and deadlines."
        )
        ai_action_plan = claude_invoke(
            system="You are a UAE PRO (Public Relations Officer) compliance expert.",
            user_message=prompt,
            max_tokens=512,
        )

    report = {
        "date": date.today().isoformat(),
        "company_id": state.get("company_id"),
        "total_documents": len(state.get("enriched_docs", [])),
        "critical_count": len(state.get("critical_docs", [])),
        "urgent_count": len(state.get("urgent_docs", [])),
        "warning_count": len(state.get("warning_docs", [])),
        "critical_docs": state.get("critical_docs", []),
        "urgent_docs": state.get("urgent_docs", []),
        "warning_docs": state.get("warning_docs", []),
        "api_mode": state.get("api_mode"),
    }
    return {"report": report, "ai_action_plan": ai_action_plan}


_document_graph = None


def create_document_graph():
    global _document_graph
    if _document_graph is not None or not LANGGRAPH_AVAILABLE:
        return _document_graph

    g: StateGraph = StateGraph(DocumentState)
    for name, fn in [
        ("fetch_docs", _fetch_docs),
        ("calculate_expiry", _calculate_expiry),
        ("categorize_urgency", _categorize_urgency),
        ("send_alerts", _send_alerts),
        ("generate_report", _generate_report),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "fetch_docs")
    g.add_edge("fetch_docs", "calculate_expiry")
    g.add_edge("calculate_expiry", "categorize_urgency")
    g.add_edge("categorize_urgency", "send_alerts")
    g.add_edge("send_alerts", "generate_report")
    g.add_edge("generate_report", END)

    _document_graph = g.compile()
    return _document_graph


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
        "documents": p.get("documents", []),
        "enriched_docs": [],
        "critical_docs": [],
        "urgent_docs": [],
        "warning_docs": [],
        "alerts_sent": False,
        "report": {},
        "ai_action_plan": "",
        "api_mode": api_mode,
    }

    graph = create_document_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return {**final.get("report", {}), "ai_action_plan": final.get("ai_action_plan", "")}
        except Exception as exc:
            logger.exception("document_agent.error", error=str(exc))

    return {"company_id": company_id, "error": "LangGraph unavailable", "api_mode": api_mode}

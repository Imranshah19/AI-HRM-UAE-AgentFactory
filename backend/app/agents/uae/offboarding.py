"""
Offboarding Agent UAE — LangGraph StateGraph for employee exit + final settlement.

UAE requirements:
  - Final settlement within 14 days of last working day
  - Gratuity calculation (see gratuity.py)
  - Visa cancellation (30-day grace after labour card cancellation)
  - Labour card cancellation via MOHRE
  - Emirates ID deactivation notification

Nodes:
  receive_exit → calculate_settlement → generate_documents
  → create_checklist → send_deadline_alerts → log_done

Claude reviews high-value settlement packages.
"""

from __future__ import annotations

from datetime import date, timedelta
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

SETTLEMENT_DEADLINE_DAYS = 14

if LANGGRAPH_AVAILABLE:
    class OffboardingState(TypedDict):
        company_id: str
        employee_id: str
        employee_name: str
        exit_date: str
        exit_reason: str
        basic_salary: str
        years_of_service: float
        gratuity_amount: str
        unpaid_salary: str
        leave_encashment: str
        other_deductions: str
        total_settlement: str
        settlement_deadline: str
        days_to_deadline: int
        checklist: list
        documents: list
        alerts_sent: bool
        completed: bool
        api_mode: str


def _receive_exit(state: dict) -> dict:
    try:
        exit_dt = date.fromisoformat(state.get("exit_date") or date.today().isoformat())
        deadline = exit_dt + timedelta(days=SETTLEMENT_DEADLINE_DAYS)
        days_left = (deadline - date.today()).days
    except ValueError:
        deadline = date.today() + timedelta(days=SETTLEMENT_DEADLINE_DAYS)
        days_left = SETTLEMENT_DEADLINE_DAYS

    try:
        join_date = date.fromisoformat(state.get("join_date", "2020-01-01"))
        exit_dt2 = date.fromisoformat(state.get("exit_date") or date.today().isoformat())
        years = (exit_dt2 - join_date).days / 365.25
    except (ValueError, KeyError):
        years = state.get("years_of_service", 0.0)

    return {
        "settlement_deadline": deadline.isoformat(),
        "days_to_deadline": days_left,
        "years_of_service": round(years, 4),
    }


def _calculate_settlement(state: dict) -> dict:
    basic = Decimal(str(state.get("basic_salary", "0")))
    years = Decimal(str(state.get("years_of_service", 0)))
    reason = (state.get("exit_reason") or "resignation").lower()
    daily_rate = basic / Decimal("30")

    # Gratuity (simplified — full calculation in gratuity.py)
    if years < 1:
        gratuity = Decimal("0")
    elif years <= 5:
        days = min(years, Decimal("5")) * Decimal("21")
    else:
        days = Decimal("5") * Decimal("21") + (years - Decimal("5")) * Decimal("30")
        gratuity = (daily_rate * days).quantize(Decimal("0.01"), ROUND_HALF_UP)
        cap = basic * Decimal("24")
        gratuity = min(gratuity, cap)

    if years < 1:
        gratuity = Decimal("0")
    elif years <= 5:
        g_days = min(years, Decimal("5")) * Decimal("21")
        gratuity = (daily_rate * g_days).quantize(Decimal("0.01"), ROUND_HALF_UP)
        if reason == "resignation":
            if years < 3:
                gratuity = (gratuity * Decimal("0.3333")).quantize(Decimal("0.01"))
            elif years < 5:
                gratuity = (gratuity * Decimal("0.6667")).quantize(Decimal("0.01"))
    else:
        g_days = Decimal("5") * Decimal("21") + (years - Decimal("5")) * Decimal("30")
        gratuity = (daily_rate * g_days).quantize(Decimal("0.01"), ROUND_HALF_UP)
        gratuity = min(gratuity, basic * Decimal("24"))

    unpaid = Decimal(str(state.get("unpaid_salary", "0")))
    leave_enc = Decimal(str(state.get("leave_encashment", "0")))
    deductions = Decimal(str(state.get("other_deductions", "0")))
    total = (gratuity + unpaid + leave_enc - deductions).quantize(Decimal("0.01"), ROUND_HALF_UP)

    return {
        "gratuity_amount": str(gratuity),
        "total_settlement": str(total),
    }


def _generate_documents(state: dict) -> dict:
    docs = [
        {"type": "Experience Certificate", "status": "pending"},
        {"type": "Visa Cancellation Letter", "status": "pending"},
        {"type": "Labour Card Cancellation (MOHRE)", "status": "pending"},
        {"type": "Final Salary Statement", "status": "pending"},
        {"type": "Gratuity Calculation Sheet", "status": "pending"},
        {"type": "NOC (No Objection Certificate)", "status": "pending"},
    ]
    return {"documents": docs}


def _create_checklist(state: dict) -> dict:
    checklist = [
        {"task": "Return company assets (laptop, access card, phone)", "done": False},
        {"task": "Revoke system access (IT)", "done": False},
        {"task": "Cancel company credit card", "done": False},
        {"task": "Submit labour card to PRO for cancellation", "done": False},
        {"task": "Process visa cancellation within 30 days", "done": False},
        {"task": "Clear outstanding loans / advances", "done": False},
        {"task": "Transfer knowledge / handover", "done": False},
        {"task": "Conduct exit interview", "done": False},
        {"task": "Transfer gratuity + final pay via WPS", "done": False},
    ]
    return {"checklist": checklist}


def _send_deadline_alerts(state: dict) -> dict:
    days = state.get("days_to_deadline", 14)
    if days <= 3:
        logger.error(
            "offboarding.deadline_critical",
            employee_id=state.get("employee_id"),
            days=days,
            total=state.get("total_settlement"),
        )
    elif days <= 7:
        logger.warning(
            "offboarding.deadline_approaching",
            employee_id=state.get("employee_id"),
            days=days,
        )
    return {"alerts_sent": True}


def _log_done(state: dict) -> dict:
    ai_note = ""
    total = Decimal(str(state.get("total_settlement", "0")))

    if is_live_mode() and total > Decimal("50000"):
        prompt = (
            f"High-value UAE offboarding: employee {state.get('employee_name')}, "
            f"exit={state.get('exit_reason')}, years={round(state.get('years_of_service', 0), 1)}, "
            f"total settlement AED {state.get('total_settlement')}. "
            "Review for accuracy and advise on payment timeline and tax/legal considerations."
        )
        ai_note = claude_invoke(
            system="You are a UAE end-of-service settlement specialist.",
            user_message=prompt,
            max_tokens=512,
        )

    logger.info(
        "offboarding.completed",
        employee_id=state.get("employee_id"),
        total_settlement=state.get("total_settlement"),
        deadline=state.get("settlement_deadline"),
        ai_flagged=bool(ai_note),
    )
    return {"completed": True}


_offboarding_graph = None


def create_offboarding_graph():
    global _offboarding_graph
    if _offboarding_graph is not None or not LANGGRAPH_AVAILABLE:
        return _offboarding_graph

    g: StateGraph = StateGraph(OffboardingState)
    for name, fn in [
        ("receive_exit", _receive_exit),
        ("calculate_settlement", _calculate_settlement),
        ("generate_documents", _generate_documents),
        ("create_checklist", _create_checklist),
        ("send_deadline_alerts", _send_deadline_alerts),
        ("log_done", _log_done),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "receive_exit")
    g.add_edge("receive_exit", "calculate_settlement")
    g.add_edge("calculate_settlement", "generate_documents")
    g.add_edge("generate_documents", "create_checklist")
    g.add_edge("create_checklist", "send_deadline_alerts")
    g.add_edge("send_deadline_alerts", "log_done")
    g.add_edge("log_done", END)

    _offboarding_graph = g.compile()
    return _offboarding_graph


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
        "exit_date": p.get("exit_date", date.today().isoformat()),
        "exit_reason": p.get("exit_reason", "resignation"),
        "basic_salary": str(p.get("basic_salary", "10000")),
        "years_of_service": float(p.get("years_of_service", 0)),
        "gratuity_amount": "0",
        "unpaid_salary": str(p.get("unpaid_salary", "0")),
        "leave_encashment": str(p.get("leave_encashment", "0")),
        "other_deductions": str(p.get("other_deductions", "0")),
        "total_settlement": "0",
        "settlement_deadline": "",
        "days_to_deadline": SETTLEMENT_DEADLINE_DAYS,
        "checklist": [],
        "documents": [],
        "alerts_sent": False,
        "completed": False,
        "api_mode": api_mode,
    }

    graph = create_offboarding_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return {
                "employee_id": final.get("employee_id"),
                "company_id": company_id,
                "gratuity_amount": final.get("gratuity_amount"),
                "total_settlement": final.get("total_settlement"),
                "settlement_deadline": final.get("settlement_deadline"),
                "days_to_deadline": final.get("days_to_deadline"),
                "documents": final.get("documents", []),
                "checklist": final.get("checklist", []),
                "completed": final.get("completed"),
                "currency": "AED",
                "api_mode": api_mode,
            }
        except Exception as exc:
            logger.exception("offboarding_agent.error", error=str(exc))

    return {"company_id": company_id, "error": "LangGraph unavailable", "api_mode": api_mode}

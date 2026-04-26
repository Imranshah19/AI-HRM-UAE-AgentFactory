"""
Leave Agent UAE — LangGraph StateGraph for UAE leave management.

9 UAE leave types (Federal Decree-Law No. 33/2021):
  annual, sick, maternity, paternity, bereavement, hajj, study, parental, unpaid

Nodes:
  check_balance → check_overlap → check_holidays → check_ramadan
  → make_decision (conditional) → update_balance → notify

Claude (claude-opus-4-7) powers the make_decision node with adaptive thinking.
"""

from __future__ import annotations

import json
import re
from datetime import date
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

UAE_LABOUR_LAW_SYSTEM = """You are a UAE HR expert specializing in Federal Decree-Law No. 33/2021.
Analyze leave requests and provide decisions.
Always return JSON: {"decision": "approve"|"reject"|"review", "reason": "...", "flags": [...]}"""

LEAVE_ENTITLEMENTS = {
    "annual":      {"days": 30, "paid": True},
    "sick":        {"days_full": 15, "days_half": 30, "days_unpaid": 45, "paid": "partial"},
    "maternity":   {"days_full": 45, "days_half": 15, "paid": "partial"},
    "paternity":   {"working_days": 5, "paid": True},
    "bereavement": {"spouse_days": 5, "parent_days": 3, "family_days": 1, "paid": True},
    "hajj":        {"calendar_days": 30, "paid": False, "once_only": True},
    "study":       {"working_days_per_year": 10, "paid": True},
    "parental":    {"varies": True, "paid": True},
    "unpaid":      {"paid": False},
}

RAMADAN_PERIODS = {
    2025: (date(2025, 3, 1),  date(2025, 3, 30)),
    2026: (date(2026, 2, 18), date(2026, 3, 19)),
    2027: (date(2027, 2, 7),  date(2027, 3, 8)),
}


if LANGGRAPH_AVAILABLE:
    class LeaveState(TypedDict):
        employee_id: str
        company_id: str
        leave_type: str
        start_date: str
        end_date: str
        days_requested: int
        public_holidays: int
        effective_days: int
        balance_entitled: int
        balance_used: int
        balance_remaining: int
        team_overlap: bool
        is_ramadan_period: bool
        decision: str
        decision_reason: str
        flags: list
        balance_updated: bool
        notification_sent: bool
        api_mode: str


def _check_balance(state: dict) -> dict:
    leave_type = state.get("leave_type", "annual")
    info = LEAVE_ENTITLEMENTS.get(leave_type, {})
    entitled = info.get("days", info.get("working_days_per_year", 0))
    used = 5
    return {
        "balance_entitled": entitled,
        "balance_used": used,
        "balance_remaining": max(0, entitled - used),
    }


def _check_overlap(state: dict) -> dict:
    return {"team_overlap": False}


def _check_holidays(state: dict) -> dict:
    try:
        start = date.fromisoformat(state["start_date"])
        end = date.fromisoformat(state["end_date"])
    except (KeyError, ValueError):
        return {"public_holidays": 0, "effective_days": state.get("days_requested", 1)}

    fixed = [
        date(start.year, 1, 1),
        date(start.year, 11, 30),
        date(start.year, 12, 2),
        date(start.year, 12, 3),
    ]
    ph = sum(1 for h in fixed if start <= h <= end)
    cal_days = (end - start).days + 1
    effective = max(0, cal_days - ph)
    return {"public_holidays": ph, "effective_days": effective, "days_requested": effective}


def _check_ramadan(state: dict) -> dict:
    try:
        start = date.fromisoformat(state["start_date"])
    except (KeyError, ValueError):
        return {"is_ramadan_period": False}
    period = RAMADAN_PERIODS.get(start.year)
    return {"is_ramadan_period": bool(period and period[0] <= start <= period[1])}


def _make_decision(state: dict) -> dict:
    leave_type = state.get("leave_type", "annual")
    effective = state.get("effective_days", 0)
    remaining = state.get("balance_remaining", 0)
    flags: list = list(state.get("flags", []))

    if state.get("team_overlap"):
        flags.append("team_overlap")
    if state.get("is_ramadan_period"):
        flags.append("ramadan_period")

    if leave_type == "unpaid":
        return {"decision": "approve", "decision_reason": "Unpaid leave — mutual agreement (UAE law)", "flags": flags}

    if effective == 0:
        return {"decision": "approve", "decision_reason": "No working days requested", "flags": flags}

    if remaining >= effective and not state.get("team_overlap"):
        basic, reason = "approve", f"Sufficient balance ({remaining} days, {effective} requested)"
    elif remaining < effective:
        basic, reason = "reject", f"Insufficient balance ({remaining} available, {effective} requested)"
        flags.append("insufficient_balance")
    else:
        basic, reason = "review", "Team overlap — HR review required"

    if is_live_mode() and flags:
        prompt = (
            f"UAE leave: type={leave_type}, days={effective}, balance={remaining}, "
            f"overlap={state.get('team_overlap')}, ramadan={state.get('is_ramadan_period')}, flags={flags}. "
            "Return decision JSON."
        )
        ai_text = claude_invoke(system=UAE_LABOUR_LAW_SYSTEM, user_message=prompt)
        m = re.search(r"\{.*\}", ai_text, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group())
                return {
                    "decision": data.get("decision", basic),
                    "decision_reason": data.get("reason", reason),
                    "flags": data.get("flags", flags),
                }
            except json.JSONDecodeError:
                pass

    return {"decision": basic, "decision_reason": reason, "flags": flags}


def _update_balance(state: dict) -> dict:
    logger.info("leave.balance_updated", employee_id=state.get("employee_id"))
    return {"balance_updated": True}


def _notify(state: dict) -> dict:
    logger.info("leave.notification_sent", employee_id=state.get("employee_id"), decision=state.get("decision"))
    return {"notification_sent": True}


def _route_decision(state: dict) -> str:
    return state.get("decision", "review")


_leave_graph = None


def create_leave_graph():
    global _leave_graph
    if _leave_graph is not None or not LANGGRAPH_AVAILABLE:
        return _leave_graph

    g: StateGraph = StateGraph(LeaveState)
    for name, fn in [
        ("check_balance", _check_balance), ("check_overlap", _check_overlap),
        ("check_holidays", _check_holidays), ("check_ramadan", _check_ramadan),
        ("make_decision", _make_decision), ("update_balance", _update_balance),
        ("notify", _notify),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "check_balance")
    g.add_edge("check_balance", "check_overlap")
    g.add_edge("check_overlap", "check_holidays")
    g.add_edge("check_holidays", "check_ramadan")
    g.add_edge("check_ramadan", "make_decision")
    g.add_conditional_edges(
        "make_decision", _route_decision,
        {"approve": "update_balance", "reject": "notify", "review": "notify"},
    )
    g.add_edge("update_balance", "notify")
    g.add_edge("notify", END)

    _leave_graph = g.compile()
    return _leave_graph


async def run_agent(
    company_id: str,
    employee_id: Optional[str] = None,
    payload: dict | None = None,
    api_mode: str = "mock",
) -> dict:
    p = payload or {}
    initial: dict = {
        "employee_id": employee_id or p.get("employee_id", ""),
        "company_id": company_id,
        "leave_type": p.get("leave_type", "annual"),
        "start_date": p.get("start_date", date.today().isoformat()),
        "end_date": p.get("end_date", date.today().isoformat()),
        "days_requested": p.get("days_requested", 1),
        "public_holidays": 0, "effective_days": p.get("days_requested", 1),
        "balance_entitled": 30, "balance_used": 0, "balance_remaining": 30,
        "team_overlap": False, "is_ramadan_period": False,
        "decision": "review", "decision_reason": "", "flags": [],
        "balance_updated": False, "notification_sent": False, "api_mode": api_mode,
    }

    graph = create_leave_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return {
                "decision": final.get("decision"),
                "decision_reason": final.get("decision_reason"),
                "flags": final.get("flags", []),
                "effective_days": final.get("effective_days"),
                "balance_remaining": final.get("balance_remaining"),
                "is_ramadan_period": final.get("is_ramadan_period"),
                "api_mode": api_mode,
            }
        except Exception as exc:
            logger.exception("leave_agent.error", error=str(exc))

    result = _make_decision(initial)
    return {**result, "effective_days": initial["effective_days"], "api_mode": api_mode}


async def get_leave_balance(employee_id: str, company_id: str) -> dict:
    return {
        "employee_id": employee_id,
        "company_id": company_id,
        "year": date.today().year,
        "balances": {
            lt: {"entitled": info.get("days", info.get("working_days_per_year", 0)),
                 "used": 0, "balance": info.get("days", info.get("working_days_per_year", 0))}
            for lt, info in LEAVE_ENTITLEMENTS.items()
        },
        "currency": "AED",
    }

"""
Gratuity Agent UAE — LangGraph StateGraph for end-of-service gratuity.

Federal Decree-Law No. 33/2021 (effective 02 Feb 2022):
  - <1 yr service: no gratuity
  - 1–5 yr: 21 days basic per year
  - >5 yr: 30 days basic per year (capped at 2 years' salary)
  - Resignation == termination: SAME entitlement (old-law reductions abolished)

Guards (run before calculation):
  - missing/zero basic_salary → BLOCKED
  - exit_reason=misconduct → BLOCKED (Art. 44 is a legal, not arithmetic, decision)
  - is_emirati=True → BLOCKED (GPSSA pension scheme, not MOHRE gratuity)

Nodes:
  validate_inputs → (blocked? → generate_report)
                 → fetch_service → determine_scenario → calculate_gratuity
                 → calculate_settlement → generate_report

Claude validates capped/anomalous results only — never in the arithmetic path.
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
        basic_salary: str         # empty string = missing → guard blocks
        join_date: str
        exit_date: str
        exit_reason: str          # "resignation" | "termination" | "completion" | "misconduct"
        is_emirati: bool          # True → GPSSA route, not MOHRE gratuity
        years_of_service: float
        gratuity_days: float
        gratuity_amount: str
        unpaid_salary: str
        leave_encashment: str
        total_settlement: str
        currency: str
        capped: bool
        blocked: bool             # True if a guard tripped before calculation
        blocked_reason: str
        notes: str
        api_mode: str


def _validate_inputs(state: dict) -> dict:
    """
    Run ALL guards before touching any calculation.
    Returns blocked=True + reason if any guard trips; otherwise blocked=False.

    Guards (per change list — decided, not legally pending):
      1. missing/zero basic_salary   → BLOCKED (never default)
      2. exit_reason=misconduct      → BLOCKED (Art. 44 is a legal call)
      3. is_emirati=True             → BLOCKED (GPSSA route, not MOHRE gratuity)
    """
    basic_raw   = (state.get("basic_salary") or "").strip()
    exit_reason = (state.get("exit_reason") or "").lower().strip()
    is_emirati  = bool(state.get("is_emirati", False))

    if not basic_raw or basic_raw in ("0", "0.00"):
        return {
            "blocked": True,
            "blocked_reason": (
                "basic_salary is missing or zero — cannot compute gratuity. "
                "Fix in the source system before re-running."
            ),
        }
    try:
        if Decimal(basic_raw) <= Decimal("0"):
            return {
                "blocked": True,
                "blocked_reason": f"basic_salary must be positive, got: {basic_raw!r}",
            }
    except Exception:
        return {
            "blocked": True,
            "blocked_reason": f"basic_salary is not a valid number: {basic_raw!r}",
        }

    if exit_reason == "misconduct":
        return {
            "blocked": True,
            "blocked_reason": (
                "exit_reason=misconduct — forfeiture under Art. 44 "
                "is a legal determination, not arithmetic. Route to HR/legal."
            ),
        }

    if is_emirati:
        return {
            "blocked": True,
            "blocked_reason": (
                "is_emirati=True — UAE nationals are covered by GPSSA pension scheme, "
                "not MOHRE end-of-service gratuity. Route to HR for GPSSA entitlement."
            ),
        }

    return {"blocked": False, "blocked_reason": ""}


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

    # Federal Decree-Law 33/2021: resignation == termination, no reduction.
    # The old-law 1/3 / 2/3 blocks (Federal Law 8/1980) are abolished as of 02 Feb 2022.

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
    if state.get("blocked"):
        logger.warning(
            "gratuity.blocked",
            employee_id=state.get("employee_id"),
            reason=state.get("blocked_reason"),
        )
        return {"notes": f"BLOCKED: {state.get('blocked_reason', '')}"}

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
        ("validate_inputs",   _validate_inputs),
        ("fetch_service",     _fetch_service),
        ("determine_scenario", _determine_scenario),
        ("calculate_gratuity", _calculate_gratuity),
        ("calculate_settlement", _calculate_settlement),
        ("generate_report",   _generate_report),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "validate_inputs")
    g.add_conditional_edges(
        "validate_inputs",
        lambda s: "generate_report" if s.get("blocked") else "fetch_service",
        {"generate_report": "generate_report", "fetch_service": "fetch_service"},
    )
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
    # Never default basic_salary — missing means BLOCKED (guard catches it).
    basic_raw = p.get("basic_salary")
    initial: dict = {
        "company_id": company_id,
        "employee_id": employee_id or p.get("employee_id", ""),
        "basic_salary": str(basic_raw).strip() if basic_raw is not None else "",
        "join_date": p.get("join_date", "2020-01-01"),
        "exit_date": p.get("exit_date", date.today().isoformat()),
        "exit_reason": p.get("exit_reason", "resignation"),
        "is_emirati": bool(p.get("is_emirati", False)),
        "years_of_service": 0.0,
        "gratuity_days": 0.0,
        "gratuity_amount": "0",
        "unpaid_salary": str(p.get("unpaid_salary", "0")),
        "leave_encashment": str(p.get("leave_encashment", "0")),
        "total_settlement": "0",
        "currency": "AED",
        "capped": False,
        "blocked": False,
        "blocked_reason": "",
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
                "blocked": final.get("blocked", False),
                "blocked_reason": final.get("blocked_reason", ""),
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

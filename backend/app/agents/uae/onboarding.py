"""
Onboarding Agent UAE — LangGraph StateGraph for UAE employee onboarding.

Nodes:
  validate_data → create_profile → generate_checklist → setup_salary
  → register_wps → notify_it → notify_pro → send_welcome → log_done

UAE-specific: Emirates ID, Visa/Labour Card, ILOE enrollment,
WPS bank account registration, PRO notification for visa.
Claude reviews high-risk onboarding profiles.
"""

from __future__ import annotations

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

if LANGGRAPH_AVAILABLE:
    class OnboardingState(TypedDict):
        company_id: str
        employee_id: str
        employee_name: str
        nationality: str
        job_title: str
        department: str
        basic_salary: str
        start_date: str
        validation_errors: list
        checklist: list
        salary_setup: bool
        wps_registered: bool
        it_notified: bool
        pro_notified: bool
        welcome_sent: bool
        risk_flags: list
        ai_notes: str
        completed: bool
        api_mode: str


def _validate_data(state: dict) -> dict:
    errors = []
    required = ["employee_name", "nationality", "job_title", "basic_salary", "start_date"]
    for field in required:
        if not state.get(field):
            errors.append(f"Missing required field: {field}")
    return {"validation_errors": errors}


def _create_profile(state: dict) -> dict:
    logger.info(
        "onboarding.profile_created",
        employee_id=state.get("employee_id"),
        company_id=state.get("company_id"),
    )
    return {}


def _generate_checklist(state: dict) -> dict:
    checklist = [
        {"item": "Emirates ID copy", "required": True, "status": "pending"},
        {"item": "Passport copy", "required": True, "status": "pending"},
        {"item": "Visa / Entry permit", "required": True, "status": "pending"},
        {"item": "Labour contract (MOHRE)", "required": True, "status": "pending"},
        {"item": "Medical fitness certificate", "required": True, "status": "pending"},
        {"item": "Bank account details for WPS", "required": True, "status": "pending"},
        {"item": "ILOE enrollment", "required": True, "status": "pending"},
        {"item": "Medical insurance enrollment", "required": True, "status": "pending"},
        {"item": "Emergency contact details", "required": False, "status": "pending"},
        {"item": "Educational certificates (attested)", "required": False, "status": "pending"},
    ]
    risk_flags = []
    if not state.get("nationality"):
        risk_flags.append("nationality_missing")
    return {"checklist": checklist, "risk_flags": risk_flags}


def _setup_salary(state: dict) -> dict:
    logger.info(
        "onboarding.salary_setup",
        employee_id=state.get("employee_id"),
        basic_salary=state.get("basic_salary"),
    )
    return {"salary_setup": True}


def _register_wps(state: dict) -> dict:
    logger.info("onboarding.wps_registered", employee_id=state.get("employee_id"))
    return {"wps_registered": True}


def _notify_it(state: dict) -> dict:
    logger.info("onboarding.it_notified", employee_id=state.get("employee_id"))
    return {"it_notified": True}


def _notify_pro(state: dict) -> dict:
    logger.info(
        "onboarding.pro_notified",
        employee_id=state.get("employee_id"),
        nationality=state.get("nationality"),
    )
    return {"pro_notified": True}


def _send_welcome(state: dict) -> dict:
    logger.info("onboarding.welcome_sent", employee_id=state.get("employee_id"))
    return {"welcome_sent": True}


def _log_done(state: dict) -> dict:
    ai_notes = ""
    if is_live_mode() and state.get("risk_flags"):
        prompt = (
            f"New UAE employee onboarding: {state.get('employee_name')}, "
            f"nationality={state.get('nationality')}, role={state.get('job_title')}, "
            f"risk_flags={state.get('risk_flags')}. "
            "Review for compliance risks and recommend HR actions."
        )
        ai_notes = claude_invoke(
            system="You are a UAE HR onboarding compliance expert.",
            user_message=prompt,
            max_tokens=512,
        )

    logger.info(
        "onboarding.completed",
        employee_id=state.get("employee_id"),
        company_id=state.get("company_id"),
        errors=len(state.get("validation_errors", [])),
    )
    return {"completed": True, "ai_notes": ai_notes}


_onboarding_graph = None


def create_onboarding_graph():
    global _onboarding_graph
    if _onboarding_graph is not None or not LANGGRAPH_AVAILABLE:
        return _onboarding_graph

    g: StateGraph = StateGraph(OnboardingState)
    for name, fn in [
        ("validate_data", _validate_data),
        ("create_profile", _create_profile),
        ("generate_checklist", _generate_checklist),
        ("setup_salary", _setup_salary),
        ("register_wps", _register_wps),
        ("notify_it", _notify_it),
        ("notify_pro", _notify_pro),
        ("send_welcome", _send_welcome),
        ("log_done", _log_done),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "validate_data")
    g.add_edge("validate_data", "create_profile")
    g.add_edge("create_profile", "generate_checklist")
    g.add_edge("generate_checklist", "setup_salary")
    g.add_edge("setup_salary", "register_wps")
    g.add_edge("register_wps", "notify_it")
    g.add_edge("notify_it", "notify_pro")
    g.add_edge("notify_pro", "send_welcome")
    g.add_edge("send_welcome", "log_done")
    g.add_edge("log_done", END)

    _onboarding_graph = g.compile()
    return _onboarding_graph


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
        "job_title": p.get("job_title", ""),
        "department": p.get("department", ""),
        "basic_salary": str(p.get("basic_salary", "0")),
        "start_date": p.get("start_date", date.today().isoformat()),
        "validation_errors": [],
        "checklist": [],
        "salary_setup": False,
        "wps_registered": False,
        "it_notified": False,
        "pro_notified": False,
        "welcome_sent": False,
        "risk_flags": [],
        "ai_notes": "",
        "completed": False,
        "api_mode": api_mode,
    }

    graph = create_onboarding_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return {
                "employee_id": final.get("employee_id"),
                "company_id": company_id,
                "completed": final.get("completed"),
                "validation_errors": final.get("validation_errors", []),
                "checklist": final.get("checklist", []),
                "salary_setup": final.get("salary_setup"),
                "wps_registered": final.get("wps_registered"),
                "welcome_sent": final.get("welcome_sent"),
                "risk_flags": final.get("risk_flags", []),
                "ai_notes": final.get("ai_notes", ""),
                "api_mode": api_mode,
            }
        except Exception as exc:
            logger.exception("onboarding_agent.error", error=str(exc))

    return {
        "employee_id": initial["employee_id"],
        "company_id": company_id,
        "completed": False,
        "validation_errors": ["LangGraph unavailable"],
        "api_mode": api_mode,
    }

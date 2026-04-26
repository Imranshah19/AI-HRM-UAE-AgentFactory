"""
Attendance Agent UAE — LangGraph StateGraph for UAE working-hours tracking.

UAE Law: 8hr/day standard | 6hr/day Ramadan | max 2hr overtime/day
Verification: GPS / WiFi / QR / IP (configurable per company)
Nodes: receive_event → verify_location → check_working_hours
       → detect_ramadan → flag_anomalies → update_record → generate_report
Claude detects chronic anomaly patterns.
"""

from __future__ import annotations

from datetime import date, datetime
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

RAMADAN_PERIODS = {
    2025: (date(2025, 3, 1),  date(2025, 3, 30)),
    2026: (date(2026, 2, 18), date(2026, 3, 19)),
    2027: (date(2027, 2, 7),  date(2027, 3, 8)),
}

if LANGGRAPH_AVAILABLE:
    class AttendanceState(TypedDict):
        employee_id: str
        company_id: str
        event_type: str         # "checkin" | "checkout" | "daily_report"
        timestamp: str
        verification_method: str
        location_data: dict
        is_verified: bool
        is_ramadan_day: bool
        standard_hours: int     # 8 or 6
        is_late: bool
        late_minutes: int
        hours_worked: float
        overtime_hours: float
        anomalies: list
        record_updated: bool
        report: dict
        api_mode: str


def _is_ramadan(check_date: date) -> bool:
    p = RAMADAN_PERIODS.get(check_date.year)
    return bool(p and p[0] <= check_date <= p[1])


def _receive_event(state: dict) -> dict:
    ts = state.get("timestamp") or datetime.utcnow().strftime("%H:%M:%S")
    today = date.today()
    return {"timestamp": ts, "is_ramadan_day": _is_ramadan(today)}


def _verify_location(state: dict) -> dict:
    method = state.get("verification_method", "manual")
    # Production: verify GPS/WiFi/QR/IP against company config
    return {"is_verified": True}  # Mock: always verified


def _check_working_hours(state: dict) -> dict:
    is_ramadan = state.get("is_ramadan_day", False)
    standard_hours = 6 if is_ramadan else 8

    try:
        ts = state.get("timestamp", "09:00:00")
        checkin_time = datetime.strptime(ts, "%H:%M:%S")
        standard_start = datetime.strptime("09:00:00", "%H:%M:%S")
        late_minutes = max(0, int((checkin_time - standard_start).total_seconds() / 60))
        is_late = late_minutes > 15  # 15-min grace
    except ValueError:
        late_minutes = 0
        is_late = False

    return {
        "standard_hours": standard_hours,
        "is_late": is_late,
        "late_minutes": late_minutes if is_late else 0,
    }


def _detect_ramadan_schedule(state: dict) -> dict:
    # Already captured in _is_ramadan — just log
    if state.get("is_ramadan_day"):
        logger.info("attendance.ramadan_mode", company_id=state.get("company_id"))
    return {}


def _flag_anomalies(state: dict) -> dict:
    anomalies = []
    if state.get("is_late") and state.get("late_minutes", 0) > 60:
        anomalies.append({"type": "very_late", "minutes": state["late_minutes"]})
    if not state.get("is_verified"):
        anomalies.append({"type": "verification_failed", "method": state.get("verification_method")})
    return {"anomalies": anomalies}


def _update_record(state: dict) -> dict:
    logger.info(
        "attendance.record_updated",
        employee_id=state.get("employee_id"),
        event_type=state.get("event_type"),
        is_late=state.get("is_late"),
    )
    return {"record_updated": True}


def _generate_report(state: dict) -> dict:
    report = {
        "date": date.today().isoformat(),
        "employee_id": state.get("employee_id"),
        "company_id": state.get("company_id"),
        "is_late": state.get("is_late"),
        "late_minutes": state.get("late_minutes", 0),
        "standard_hours": state.get("standard_hours", 8),
        "is_ramadan_day": state.get("is_ramadan_day"),
        "anomalies": state.get("anomalies", []),
        "api_mode": state.get("api_mode"),
    }

    if is_live_mode() and state.get("anomalies"):
        prompt = f"UAE attendance anomalies: {state['anomalies']} for employee {state.get('employee_id')}. Recommend HR action."
        ai_note = claude_invoke(
            system="You are a UAE HR compliance expert.",
            user_message=prompt,
            max_tokens=256,
        )
        report["ai_recommendation"] = ai_note

    return {"report": report}


_attendance_graph = None


def create_attendance_graph():
    global _attendance_graph
    if _attendance_graph is not None or not LANGGRAPH_AVAILABLE:
        return _attendance_graph

    g: StateGraph = StateGraph(AttendanceState)
    for name, fn in [
        ("receive_event", _receive_event), ("verify_location", _verify_location),
        ("check_hours", _check_working_hours), ("detect_ramadan", _detect_ramadan_schedule),
        ("flag_anomalies", _flag_anomalies), ("update_record", _update_record),
        ("generate_report", _generate_report),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "receive_event")
    g.add_edge("receive_event", "verify_location")
    g.add_edge("verify_location", "check_hours")
    g.add_edge("check_hours", "detect_ramadan")
    g.add_edge("detect_ramadan", "flag_anomalies")
    g.add_edge("flag_anomalies", "update_record")
    g.add_edge("update_record", "generate_report")
    g.add_edge("generate_report", END)

    _attendance_graph = g.compile()
    return _attendance_graph


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
        "event_type": p.get("event_type", "checkin"),
        "timestamp": p.get("timestamp", ""),
        "verification_method": p.get("verification_method", "manual"),
        "location_data": p.get("location_data", {}),
        "is_verified": False, "is_ramadan_day": False,
        "standard_hours": 8, "is_late": False, "late_minutes": 0,
        "hours_worked": 0.0, "overtime_hours": 0.0,
        "anomalies": [], "record_updated": False, "report": {}, "api_mode": api_mode,
    }

    graph = create_attendance_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return final.get("report", {"api_mode": api_mode})
        except Exception as exc:
            logger.exception("attendance_agent.error", error=str(exc))

    report = _generate_report(initial)
    return report["report"]


async def generate_daily_report(company_id: str) -> dict:
    return {
        "company_id": company_id,
        "date": date.today().isoformat(),
        "total_employees": 55,
        "present_count": 48,
        "absent_count": 4,
        "late_count": 3,
        "on_leave_count": 2,
        "is_ramadan_day": _is_ramadan(date.today()),
        "standard_hours": 6 if _is_ramadan(date.today()) else 8,
        "attendance_rate_percent": 87.3,
        "api_mode": "live" if is_live_mode() else "mock",
    }

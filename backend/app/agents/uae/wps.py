"""
WPS Agent UAE — LangGraph StateGraph for Wage Protection System compliance.

MOHRE SIF (Salary Information File) XML generator + validator.
Deadline: salaries must be paid by the last day of each month.

Nodes:
  fetch_payroll → validate_banks → check_coverage → generate_sif
  → validate_sif → check_deadline → send_alerts

WPS SIF XML format: MOHRE-specified schema.
Claude flags high-risk WPS violations.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
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
    class WPSState(TypedDict):
        company_id: str
        payroll_month: int
        payroll_year: int
        employer_id: str
        employees: list
        bank_errors: list
        coverage_pct: float
        sif_xml: str
        sif_valid: bool
        sif_errors: list
        days_to_deadline: int
        deadline_breached: bool
        alerts_sent: bool
        api_mode: str


def _fetch_payroll(state: dict) -> dict:
    mock_employees = [
        {"id": "emp-001", "name": "Ahmed Al-Rashidi", "iban": "AE070331234567890123456",
         "bank_code": "033", "net_salary": "15500.00", "currency": "AED"},
        {"id": "emp-002", "name": "Priya Sharma", "iban": "AE070331234567890123457",
         "bank_code": "033", "net_salary": "10600.00", "currency": "AED"},
        {"id": "emp-003", "name": "Juan Santos", "iban": "AE070331234567890123458",
         "bank_code": "033", "net_salary": "7300.00", "currency": "AED"},
    ]
    return {"employees": state.get("employees") or mock_employees}


def _validate_banks(state: dict) -> dict:
    bank_errors = []
    for emp in state.get("employees", []):
        iban = emp.get("iban", "")
        if not iban.startswith("AE") or len(iban) != 23:
            bank_errors.append({"employee_id": emp["id"], "error": "Invalid UAE IBAN"})
        if not emp.get("bank_code"):
            bank_errors.append({"employee_id": emp["id"], "error": "Missing bank code"})
    return {"bank_errors": bank_errors}


def _check_coverage(state: dict) -> dict:
    total = len(state.get("employees", []))
    errors = len(state.get("bank_errors", []))
    pct = ((total - errors) / total * 100) if total > 0 else 0.0
    return {"coverage_pct": round(pct, 2)}


def _generate_sif(state: dict) -> dict:
    today = date.today()
    root = ET.Element("SalaryInformation")
    root.set("xmlns", "http://www.mohre.gov.ae/wps/sif/v1")

    header = ET.SubElement(root, "Header")
    ET.SubElement(header, "EmployerID").text = state.get("employer_id", state.get("company_id", ""))
    ET.SubElement(header, "PayrollMonth").text = f"{state.get('payroll_year', today.year)}-{state.get('payroll_month', today.month):02d}"
    ET.SubElement(header, "GeneratedDate").text = today.isoformat()

    salaries = ET.SubElement(root, "Salaries")
    for emp in state.get("employees", []):
        rec = ET.SubElement(salaries, "SalaryRecord")
        ET.SubElement(rec, "EmployeeID").text = emp["id"]
        ET.SubElement(rec, "EmployeeName").text = emp["name"]
        ET.SubElement(rec, "IBAN").text = emp.get("iban", "")
        ET.SubElement(rec, "BankCode").text = emp.get("bank_code", "")
        ET.SubElement(rec, "NetSalary").text = emp.get("net_salary", "0.00")
        ET.SubElement(rec, "Currency").text = emp.get("currency", "AED")

    sif_xml = ET.tostring(root, encoding="unicode", xml_declaration=False)
    return {"sif_xml": sif_xml}


def _validate_sif(state: dict) -> dict:
    sif_errors = []
    xml_str = state.get("sif_xml", "")
    if not xml_str:
        sif_errors.append("Empty SIF XML")
    if state.get("bank_errors"):
        sif_errors.append(f"{len(state['bank_errors'])} employees have bank errors")
    return {"sif_valid": len(sif_errors) == 0, "sif_errors": sif_errors}


def _check_deadline(state: dict) -> dict:
    today = date.today()
    month = state.get("payroll_month", today.month)
    year = state.get("payroll_year", today.year)
    import calendar
    last_day = calendar.monthrange(year, month)[1]
    deadline = date(year, month, last_day)
    days_left = (deadline - today).days
    return {"days_to_deadline": days_left, "deadline_breached": days_left < 0}


def _send_alerts(state: dict) -> dict:
    days = state.get("days_to_deadline", 999)
    breached = state.get("deadline_breached", False)

    if breached:
        logger.error(
            "wps.deadline_breached",
            company_id=state.get("company_id"),
            month=state.get("payroll_month"),
        )
        if is_live_mode():
            prompt = (
                f"WPS deadline breached for company {state.get('company_id')}, "
                f"month {state.get('payroll_month')}/{state.get('payroll_year')}. "
                f"Coverage: {state.get('coverage_pct')}%, SIF errors: {state.get('sif_errors')}. "
                "MOHRE fine is AED 5,000+. Advise immediate actions."
            )
            claude_invoke(
                system="You are a UAE MOHRE WPS compliance specialist.",
                user_message=prompt,
                max_tokens=256,
            )
    elif days <= 3:
        logger.warning("wps.deadline_approaching", days=days, company_id=state.get("company_id"))

    return {"alerts_sent": True}


_wps_graph = None


def create_wps_graph():
    global _wps_graph
    if _wps_graph is not None or not LANGGRAPH_AVAILABLE:
        return _wps_graph

    g: StateGraph = StateGraph(WPSState)
    for name, fn in [
        ("fetch_payroll", _fetch_payroll),
        ("validate_banks", _validate_banks),
        ("check_coverage", _check_coverage),
        ("generate_sif", _generate_sif),
        ("validate_sif", _validate_sif),
        ("check_deadline", _check_deadline),
        ("send_alerts", _send_alerts),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "fetch_payroll")
    g.add_edge("fetch_payroll", "validate_banks")
    g.add_edge("validate_banks", "check_coverage")
    g.add_edge("check_coverage", "generate_sif")
    g.add_edge("generate_sif", "validate_sif")
    g.add_edge("validate_sif", "check_deadline")
    g.add_edge("check_deadline", "send_alerts")
    g.add_edge("send_alerts", END)

    _wps_graph = g.compile()
    return _wps_graph


async def run_agent(
    company_id: str,
    employee_id: Optional[str] = None,
    payload: dict | None = None,
    api_mode: str = "mock",
) -> dict:
    p = payload or {}
    today = date.today()
    initial: dict = {
        "company_id": company_id,
        "payroll_month": p.get("month", today.month),
        "payroll_year": p.get("year", today.year),
        "employer_id": p.get("employer_id", company_id),
        "employees": p.get("employees", []),
        "bank_errors": [],
        "coverage_pct": 0.0,
        "sif_xml": "",
        "sif_valid": False,
        "sif_errors": [],
        "days_to_deadline": 0,
        "deadline_breached": False,
        "alerts_sent": False,
        "api_mode": api_mode,
    }

    graph = create_wps_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return {
                "company_id": company_id,
                "payroll_month": final.get("payroll_month"),
                "payroll_year": final.get("payroll_year"),
                "coverage_pct": final.get("coverage_pct"),
                "sif_valid": final.get("sif_valid"),
                "sif_errors": final.get("sif_errors", []),
                "bank_errors": final.get("bank_errors", []),
                "days_to_deadline": final.get("days_to_deadline"),
                "deadline_breached": final.get("deadline_breached"),
                "sif_xml": final.get("sif_xml", ""),
                "api_mode": api_mode,
            }
        except Exception as exc:
            logger.exception("wps_agent.error", error=str(exc))

    return {"company_id": company_id, "error": "LangGraph unavailable", "api_mode": api_mode}


async def get_wps_status(company_id: str) -> dict:
    return await run_agent(company_id=company_id, api_mode="mock")

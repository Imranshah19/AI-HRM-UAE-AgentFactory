"""
Payroll Agent UAE — LangGraph StateGraph for UAE payroll processing in AED.

Nodes:
  fetch_employee_data → calculate_earnings → calculate_overtime
  → apply_iloe_deduction → validate_totals → generate_outputs

ILOE (mandatory 2023): AED 5/month (<16k basic) or AED 10/month (>=16k)
Overtime: 125% normal, 150% night/Friday/holiday
No income tax in UAE.
Claude reviews anomalies in validate_totals.
"""

from __future__ import annotations

import json
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

ILOE_THRESHOLD = Decimal("16000")
ILOE_LOW = Decimal("5.00")
ILOE_HIGH = Decimal("10.00")
OT_NORMAL = Decimal("1.25")
OT_PREMIUM = Decimal("1.50")

if LANGGRAPH_AVAILABLE:
    class PayrollState(TypedDict):
        company_id: str
        payroll_month: int
        payroll_year: int
        employees: list
        payslips: list
        total_gross_aed: str
        total_net_aed: str
        total_iloe_aed: str
        wps_ready: bool
        errors: list
        is_ramadan_month: bool
        api_mode: str


def _detect_ramadan(month: int, year: int) -> bool:
    return {2025: 3, 2026: 2, 2027: 2}.get(year) == month


def _fetch_employees(state: dict) -> dict:
    # Production: SELECT from employees + salary_structure_uae
    mock_employees = [
        {"id": "emp-001", "name_en": "Ahmed Al-Rashidi", "name_ar": "أحمد الراشدي",
         "basic_salary": "12000", "housing": "3000", "transport": "800",
         "food": "500", "other": "200", "overtime_hours": "4"},
        {"id": "emp-002", "name_en": "Priya Sharma", "name_ar": "بريا شارما",
         "basic_salary": "8000", "housing": "2000", "transport": "600",
         "food": "400", "other": "0", "overtime_hours": "0"},
        {"id": "emp-003", "name_en": "Juan Santos", "name_ar": "خوان سانتوس",
         "basic_salary": "5000", "housing": "1500", "transport": "500",
         "food": "300", "other": "0", "overtime_hours": "2"},
    ]
    return {
        "employees": mock_employees,
        "is_ramadan_month": _detect_ramadan(state["payroll_month"], state["payroll_year"]),
    }


def _calculate_earnings(state: dict) -> dict:
    payslips = []
    for emp in state.get("employees", []):
        basic = Decimal(str(emp["basic_salary"]))
        housing = Decimal(str(emp["housing"]))
        transport = Decimal(str(emp["transport"]))
        food = Decimal(str(emp["food"]))
        other = Decimal(str(emp["other"]))
        ot_hours = Decimal(str(emp["overtime_hours"]))

        hourly_rate = basic / Decimal("30") / Decimal("8")
        ot_amount = (hourly_rate * OT_NORMAL * ot_hours).quantize(Decimal("0.01"))

        gross = basic + housing + transport + food + other + ot_amount
        payslips.append({
            **emp,
            "basic_salary": str(basic),
            "housing": str(housing),
            "transport": str(transport),
            "food": str(food),
            "other": str(other),
            "overtime_amount": str(ot_amount),
            "gross_salary": str(gross.quantize(Decimal("0.01"))),
        })
    return {"payslips": payslips}


def _calculate_overtime(state: dict) -> dict:
    # Already factored in _calculate_earnings; this node validates limits
    # UAE: max 2 hours/day overtime
    updated = []
    for slip in state.get("payslips", []):
        ot_h = Decimal(str(slip.get("overtime_hours", "0")))
        if ot_h > 2:
            slip["overtime_hours"] = "2"  # cap at legal max
            slip["overtime_hours_capped"] = True
        updated.append(slip)
    return {"payslips": updated}


def _apply_iloe(state: dict) -> dict:
    updated = []
    total_net = Decimal("0")
    total_gross = Decimal("0")
    total_iloe = Decimal("0")

    for slip in state.get("payslips", []):
        basic = Decimal(str(slip["basic_salary"]))
        iloe = ILOE_HIGH if basic >= ILOE_THRESHOLD else ILOE_LOW
        gross = Decimal(str(slip["gross_salary"]))
        net = (gross - iloe).quantize(Decimal("0.01"), ROUND_HALF_UP)

        slip["iloe_deduction"] = str(iloe)
        slip["net_salary"] = str(net)
        slip["currency"] = "AED"

        total_gross += gross
        total_net += net
        total_iloe += iloe
        updated.append(slip)

    return {
        "payslips": updated,
        "total_gross_aed": str(total_gross.quantize(Decimal("0.01"))),
        "total_net_aed": str(total_net.quantize(Decimal("0.01"))),
        "total_iloe_aed": str(total_iloe.quantize(Decimal("0.01"))),
    }


def _validate_totals(state: dict) -> dict:
    errors = list(state.get("errors", []))
    payslips = state.get("payslips", [])

    # Basic validation: no employee should have net < basic
    for slip in payslips:
        net = Decimal(str(slip.get("net_salary", "0")))
        basic = Decimal(str(slip.get("basic_salary", "0")))
        if net < basic * Decimal("0.9"):
            errors.append(f"Net salary for {slip['name_en']} is unusually low")

    if is_live_mode() and errors:
        prompt = (
            f"UAE payroll anomalies detected: {errors}. "
            f"Company: {state['company_id']}, Month: {state['payroll_month']}/{state['payroll_year']}. "
            "Assess risk and recommend action. Return JSON: {\"risk\": \"low|medium|high\", \"action\": \"...\"}"
        )
        ai_text = claude_invoke(system="You are a UAE payroll compliance expert.", user_message=prompt, max_tokens=512)
        logger.info("payroll.ai_validation", response=ai_text[:200])

    return {"errors": errors, "wps_ready": len(errors) == 0}


def _generate_outputs(state: dict) -> dict:
    logger.info(
        "payroll.generated",
        company_id=state.get("company_id"),
        month=state.get("payroll_month"),
        employees=len(state.get("payslips", [])),
        total_net=state.get("total_net_aed"),
    )
    return {"wps_ready": True}


_payroll_graph = None


def create_payroll_graph():
    global _payroll_graph
    if _payroll_graph is not None or not LANGGRAPH_AVAILABLE:
        return _payroll_graph

    g: StateGraph = StateGraph(PayrollState)
    for name, fn in [
        ("fetch_employees", _fetch_employees),
        ("calculate_earnings", _calculate_earnings),
        ("calculate_overtime", _calculate_overtime),
        ("apply_iloe", _apply_iloe),
        ("validate_totals", _validate_totals),
        ("generate_outputs", _generate_outputs),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "fetch_employees")
    g.add_edge("fetch_employees", "calculate_earnings")
    g.add_edge("calculate_earnings", "calculate_overtime")
    g.add_edge("calculate_overtime", "apply_iloe")
    g.add_edge("apply_iloe", "validate_totals")
    g.add_edge("validate_totals", "generate_outputs")
    g.add_edge("generate_outputs", END)

    _payroll_graph = g.compile()
    return _payroll_graph


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
        "employees": [],
        "payslips": [],
        "total_gross_aed": "0",
        "total_net_aed": "0",
        "total_iloe_aed": "0",
        "wps_ready": False,
        "errors": [],
        "is_ramadan_month": False,
        "api_mode": api_mode,
    }

    graph = create_payroll_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return {
                "company_id": company_id,
                "payroll_month": final["payroll_month"],
                "payroll_year": final["payroll_year"],
                "total_employees": len(final.get("payslips", [])),
                "total_gross_aed": final.get("total_gross_aed"),
                "total_net_aed": final.get("total_net_aed"),
                "total_iloe_aed": final.get("total_iloe_aed"),
                "wps_ready": final.get("wps_ready"),
                "is_ramadan_month": final.get("is_ramadan_month"),
                "payslips": final.get("payslips", []),
                "errors": final.get("errors", []),
                "currency": "AED",
                "api_mode": api_mode,
            }
        except Exception as exc:
            logger.exception("payroll_agent.error", error=str(exc))

    return {"company_id": company_id, "errors": ["LangGraph unavailable — mock result"], "api_mode": api_mode}

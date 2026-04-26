"""
UAE Manual API Triggers — Human-initiated agent executions.

Routes under prefix: /api/v1/uae/agent/trigger/
For one-off manual runs: payroll, doc check, WPS validation, etc.

All agent dispatch goes through graph.run_uae_task (LangGraph master graph).
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, BackgroundTasks, status
from pydantic import BaseModel

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/agent", tags=["UAE Agent Triggers"])


# ─── Trigger schemas ───────────────────────────────────────────────────────────

class PayrollTriggerRequest(BaseModel):
    month: int | None = None
    year: int | None = None

class ChatRequest(BaseModel):
    message: str
    session_id: str
    employee_id: str | None = None
    company_id: str | None = None
    user_role: str = "employee"
    language: str = ""

class LeaveBalanceRequest(BaseModel):
    employee_id: str
    company_id: str

class GratuityRequest(BaseModel):
    employee_id: str
    basic_salary: float
    join_date: str
    exit_date: str
    exit_reason: str = "resignation"


# ─── Agent status & logs ───────────────────────────────────────────────────────

@router.get("/status", summary="Get status of all UAE agents (LangGraph)")
async def get_agent_status() -> dict:
    from app.agents.uae.graph import get_agent_status
    return await get_agent_status()


@router.get("/logs", summary="Get recent UAE agent execution logs")
async def get_agent_logs(limit: int = 50) -> dict:
    from app.agents.uae.graph import get_agent_logs
    logs = await get_agent_logs(limit=limit)
    return {"logs": logs, "count": len(logs)}


# ─── Manual payroll trigger ────────────────────────────────────────────────────

@router.post("/trigger/payroll/{company_id}", summary="Manually trigger payroll for a company")
async def trigger_payroll(
    company_id: str,
    payload: PayrollTriggerRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    logger.info("api_trigger_uae.payroll", company_id=company_id)
    today = date.today()
    background_tasks.add_task(
        _run_task_bg, "payroll", company_id, None,
        {"month": payload.month or today.month, "year": payload.year or today.year},
    )
    return {
        "status": "triggered",
        "company_id": company_id,
        "agent": "payroll",
        "message": "Payroll generation started in background",
    }


@router.post("/trigger/wps-validate/{company_id}", summary="Validate WPS submission for a company")
async def trigger_wps_validate(company_id: str) -> dict:
    from app.agents.uae.graph import run_uae_task
    today = date.today()
    result = await run_uae_task(
        task_type="wps",
        company_id=company_id,
        payload={"month": today.month, "year": today.year},
    )
    return {"company_id": company_id, "result": result}


@router.post("/trigger/documents-check", summary="Run document expiry check")
async def trigger_documents_check(
    company_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    background_tasks.add_task(_run_task_bg, "document_check", company_id, None, {})
    return {
        "status": "triggered",
        "company_id": company_id,
        "agent": "document",
        "message": "Document expiry check started in background",
    }


@router.post("/trigger/attendance-report", summary="Generate today's attendance report")
async def trigger_attendance_report(
    company_id: str,
    background_tasks: BackgroundTasks,
) -> dict:
    background_tasks.add_task(_run_task_bg, "attendance", company_id, None, {"event_type": "daily_report"})
    return {
        "status": "triggered",
        "company_id": company_id,
        "agent": "attendance",
    }


@router.post("/trigger/emiratisation-check", summary="Run Emiratisation compliance check")
async def trigger_emiratisation_check(company_id: str) -> dict:
    from app.agents.uae.graph import run_uae_task
    result = await run_uae_task(task_type="emiratisation", company_id=company_id)
    return {"company_id": company_id, "result": result}


@router.post("/trigger/gratuity", summary="Calculate gratuity for an employee")
async def trigger_gratuity(payload: GratuityRequest) -> dict:
    from app.agents.uae.graph import run_uae_task
    result = await run_uae_task(
        task_type="gratuity",
        company_id="",
        employee_id=payload.employee_id,
        payload={
            "basic_salary": payload.basic_salary,
            "join_date": payload.join_date,
            "exit_date": payload.exit_date,
            "exit_reason": payload.exit_reason,
        },
    )
    return result


@router.post("/trigger/wps-sif/{company_id}", summary="Generate WPS SIF file for a company")
async def trigger_wps_sif(company_id: str) -> dict:
    from app.agents.uae.graph import run_uae_task
    today = date.today()
    result = await run_uae_task(
        task_type="wps",
        company_id=company_id,
        payload={"month": today.month, "year": today.year},
    )
    wps_result = result.get("result", {})
    return {
        "company_id": company_id,
        "sif_valid": wps_result.get("sif_valid"),
        "coverage_pct": wps_result.get("coverage_pct"),
        "sif_errors": wps_result.get("sif_errors", []),
        "bank_errors": wps_result.get("bank_errors", []),
        "sif_xml_preview": (wps_result.get("sif_xml", "")[:500] + "...") if wps_result.get("sif_xml") else "",
    }


@router.post("/trigger/leave-balance", summary="Get leave balances for an employee")
async def trigger_leave_balance(payload: LeaveBalanceRequest) -> dict:
    from app.agents.uae.graph import run_uae_task
    result = await run_uae_task(
        task_type="leave_balance",
        company_id=payload.company_id,
        employee_id=payload.employee_id,
    )
    return result


@router.post("/trigger/insurance-check/{company_id}", summary="Run insurance compliance check")
async def trigger_insurance_check(company_id: str) -> dict:
    from app.agents.uae.graph import run_uae_task
    result = await run_uae_task(task_type="insurance", company_id=company_id)
    return result


@router.post("/trigger/contract-check/{company_id}", summary="Run contract expiry check")
async def trigger_contract_check(company_id: str) -> dict:
    from app.agents.uae.graph import run_uae_task
    result = await run_uae_task(task_type="contract", company_id=company_id)
    return result


# ─── Chatbot endpoint ──────────────────────────────────────────────────────────

@router.post("/chat", summary="UAE multilingual HR chatbot (EN/AR/UR/HI/TL)")
async def chat_with_hr_agent(payload: ChatRequest) -> dict:
    from app.agents.uae.graph import run_uae_task
    result = await run_uae_task(
        task_type="chat",
        company_id=payload.company_id or "",
        employee_id=payload.employee_id,
        payload={
            "message": payload.message,
            "session_id": payload.session_id,
            "language": payload.language,
        },
    )
    chat_result = result.get("result", {})
    return {
        "response": chat_result.get("response", ""),
        "language": chat_result.get("language", "en"),
        "intent": chat_result.get("intent", ""),
        "session_id": payload.session_id,
        "api_mode": result.get("api_mode", "mock"),
    }


# ─── Shared background runner ──────────────────────────────────────────────────

async def _run_task_bg(
    task_type: str,
    company_id: str,
    employee_id: str | None,
    payload: dict,
) -> None:
    try:
        from app.agents.uae.graph import run_uae_task
        result = await run_uae_task(
            task_type=task_type,
            company_id=company_id,
            employee_id=employee_id,
            payload=payload,
        )
        logger.info(
            "api_trigger_uae.task_complete",
            task_type=task_type,
            company_id=company_id,
            status=result.get("status"),
        )
    except Exception as exc:
        logger.error("api_trigger_uae.task_failed", task_type=task_type, error=str(exc))

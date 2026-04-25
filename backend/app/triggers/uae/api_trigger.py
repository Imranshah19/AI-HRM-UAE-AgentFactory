"""
UAE Manual API Triggers — Human-initiated agent executions.

Routes under prefix: /api/v1/uae/agent/trigger/
For one-off manual runs: payroll, doc check, WPS validation, etc.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel
from typing import Any

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


# ─── Agent status & logs ───────────────────────────────────────────────────────

@router.get("/status", summary="Get status of all 15 UAE agents")
async def get_agent_status() -> dict:
    from app.agents.uae.paperclip import get_paperclip
    paperclip = get_paperclip()
    status_data = await paperclip.get_status()

    from app.agents.uae.openclaw import get_openclaw
    claw = get_openclaw()

    return {
        "agents": status_data["agents"],
        "total_agents": status_data["total"],
        "api_mode": "live" if claw.is_live else "mock",
        "version": "UAE-1.0",
    }


@router.get("/logs", summary="Get recent UAE agent execution logs")
async def get_agent_logs(limit: int = 50) -> dict:
    from app.agents.uae.paperclip import get_paperclip
    paperclip = get_paperclip()
    logs = await paperclip.get_logs(limit=limit)
    return {"logs": logs, "count": len(logs)}


# ─── Manual payroll trigger ────────────────────────────────────────────────────

@router.post("/trigger/payroll/{company_id}", summary="Manually trigger payroll for a company")
async def trigger_payroll(
    company_id: str,
    payload: PayrollTriggerRequest,
    background_tasks: BackgroundTasks,
) -> dict:
    logger.info("api_trigger_uae.payroll", company_id=company_id)
    background_tasks.add_task(
        _run_payroll, company_id, payload.month, payload.year
    )
    return {
        "status": "triggered",
        "company_id": company_id,
        "agent": "PayrollAgent",
        "message": "Payroll generation started in background",
    }


@router.post("/trigger/wps-validate/{company_id}", summary="Validate WPS submission for a company")
async def trigger_wps_validate(company_id: str) -> dict:
    from app.agents.uae.wps import get_wps_agent
    from datetime import date
    agent = get_wps_agent()
    today = date.today()
    result = await agent.validate_wps_submission(
        company_id=company_id,
        month=today.month,
        year=today.year,
    )
    return {"company_id": company_id, "validation": result}


@router.post("/trigger/documents-check", summary="Run document expiry check for all companies")
async def trigger_documents_check(background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_run_documents_check_all)
    return {
        "status": "triggered",
        "agent": "DocumentAgent",
        "message": "Document expiry check started for all companies",
    }


@router.post("/trigger/attendance-report", summary="Generate today's attendance report")
async def trigger_attendance_report(company_id: str, background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(_run_attendance_report, company_id)
    return {
        "status": "triggered",
        "company_id": company_id,
        "agent": "AttendanceAgent",
    }


@router.post("/trigger/emiratisation-check", summary="Run Emiratisation compliance check")
async def trigger_emiratisation_check(company_id: str) -> dict:
    from app.agents.uae.emiratisation import get_emiratisation_agent
    agent = get_emiratisation_agent()
    result = await agent.run_monthly_check(company_id=company_id)
    return {
        "company_id": company_id,
        "result": result.to_dict(),
        "agent": "EmiratiisationAgent",
    }


@router.post("/trigger/gratuity-report", summary="Generate gratuity liability report")
async def trigger_gratuity_report(company_id: str) -> dict:
    from app.agents.uae.gratuity import get_gratuity_agent
    agent = get_gratuity_agent()
    result = await agent.generate_liability_report(company_id=company_id)
    return {"company_id": company_id, "report": result}


@router.post("/trigger/wps-sif/{company_id}", summary="Generate WPS SIF file for a company")
async def trigger_wps_sif(company_id: str) -> dict:
    from app.agents.uae.wps import get_wps_agent
    from datetime import date
    agent = get_wps_agent()
    today = date.today()
    result = await agent.generate_sif_file(
        company_id=company_id,
        salary_month=today.month,
        salary_year=today.year,
    )
    return {
        "company_id": company_id,
        "sif_generated": True,
        "is_valid": result.is_valid,
        "total_employees": len(result.employees),
        "total_amount_aed": str(result.total_amount_aed),
        "sif_xml_preview": result.sif_xml[:500] + "..." if len(result.sif_xml) > 500 else result.sif_xml,
        "validation_errors": result.validation_errors,
    }


# ─── Chatbot endpoint ──────────────────────────────────────────────────────────

@router.post("/chat", summary="UAE multilingual HR chatbot")
async def chat_with_hr_agent(payload: ChatRequest) -> dict:
    from app.agents.uae.chatbot import get_hr_chatbot_agent
    agent = get_hr_chatbot_agent()
    response = await agent.answer(
        message=payload.message,
        session_id=payload.session_id,
        employee_id=payload.employee_id,
        company_id=payload.company_id,
        user_role=payload.user_role,
    )
    return response.to_dict()


# ─── Background runners ────────────────────────────────────────────────────────

async def _run_payroll(company_id: str, month: int | None, year: int | None) -> None:
    try:
        from app.agents.uae.payroll import get_payroll_agent
        agent = get_payroll_agent()
        await agent.generate_payroll(
            company_id=company_id,
            payroll_month=month,
            payroll_year=year,
        )
        logger.info("api_trigger_uae.payroll_complete", company_id=company_id)
    except Exception as exc:
        logger.error("api_trigger_uae.payroll_failed", error=str(exc))


async def _run_documents_check_all() -> None:
    try:
        from app.agents.uae.document import get_document_agent
        agent = get_document_agent()
        result = await agent.check_all_expiries()
        logger.info("api_trigger_uae.docs_check_complete", alerts=result.total_alerts)
    except Exception as exc:
        logger.error("api_trigger_uae.docs_check_failed", error=str(exc))


async def _run_attendance_report(company_id: str) -> None:
    try:
        from app.agents.uae.attendance import get_attendance_agent
        agent = get_attendance_agent()
        result = await agent.generate_daily_report(company_id=company_id)
        logger.info(
            "api_trigger_uae.attendance_report_complete",
            company_id=company_id,
            present=result.present_count,
        )
    except Exception as exc:
        logger.error("api_trigger_uae.attendance_report_failed", error=str(exc))

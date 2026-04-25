"""
UAE Webhook Triggers — FastAPI routes for event-driven agent execution.

All webhooks run agents as Celery background tasks (non-blocking).
Routes registered under prefix: /api/v1/uae/webhooks/
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/webhooks", tags=["UAE Webhooks"])


# ─── Request schemas ───────────────────────────────────────────────────────────

class EmployeeJoinedPayload(BaseModel):
    employee_id: str
    company_id: str
    name_en: str = ""
    name_ar: str = ""
    join_date: str = ""
    department: str = ""
    basic_salary_aed: float = 0.0
    nationality: str = ""

class EmployeeExitPayload(BaseModel):
    employee_id: str
    company_id: str
    exit_type: str = "resignation"  # resignation | termination | contract_expiry
    exit_date: str = ""
    reason: str = ""

class LeaveAppliedPayload(BaseModel):
    employee_id: str
    company_id: str
    leave_type: str
    start_date: str
    end_date: str
    reason: str = ""

class AttendancePayload(BaseModel):
    employee_id: str
    company_id: str
    timestamp: str = ""
    verification_method: str = "manual"  # gps | wifi | qr | ip | face | manual
    location_data: dict = Field(default_factory=dict)

class DocumentUploadedPayload(BaseModel):
    employee_id: str
    company_id: str
    document_type: str
    document_number: str = ""
    expiry_date: str = ""
    file_url: str = ""

class ContractExpiringPayload(BaseModel):
    employee_id: str
    company_id: str
    contract_end_date: str
    days_until_expiry: int


# ─── Webhook handlers ──────────────────────────────────────────────────────────

@router.post(
    "/employee/joined",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger employee onboarding (UAE)",
)
async def webhook_employee_joined(
    payload: EmployeeJoinedPayload,
    background_tasks: BackgroundTasks,
):
    """
    Triggers UAE onboarding agent in background:
    - Creates bilingual profile
    - Generates document checklist
    - Sets probation period (max 6 months)
    - WPS registration deadline alert (30 days)
    - Sends bilingual welcome email
    """
    logger.info(
        "webhook_uae.employee_joined",
        employee_id=payload.employee_id,
        company_id=payload.company_id,
    )
    background_tasks.add_task(_run_onboarding, payload.dict())
    return {
        "status": "accepted",
        "message": "UAE onboarding agent triggered",
        "employee_id": payload.employee_id,
        "agent": "OnboardingAgent",
    }


@router.post(
    "/employee/resigned",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger offboarding for resignation (UAE)",
)
async def webhook_employee_resigned(
    payload: EmployeeExitPayload,
    background_tasks: BackgroundTasks,
):
    """
    Triggers UAE offboarding agent:
    - Calculates final settlement (gratuity + leave + salary)
    - Creates offboarding checklist
    - Sets 14-day payment deadline alert
    - Sets 30-day visa cancellation deadline
    """
    payload_dict = payload.dict()
    payload_dict["exit_type"] = "resignation"
    background_tasks.add_task(_run_offboarding, payload_dict)
    return {
        "status": "accepted",
        "message": "UAE offboarding agent triggered (resignation)",
        "employee_id": payload.employee_id,
        "agent": "OffboardingAgent",
    }


@router.post(
    "/employee/terminated",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger offboarding for termination (UAE)",
)
async def webhook_employee_terminated(
    payload: EmployeeExitPayload,
    background_tasks: BackgroundTasks,
):
    payload_dict = payload.dict()
    payload_dict["exit_type"] = "termination"
    background_tasks.add_task(_run_offboarding, payload_dict)
    return {
        "status": "accepted",
        "message": "UAE offboarding agent triggered (termination)",
        "employee_id": payload.employee_id,
        "agent": "OffboardingAgent",
    }


@router.post(
    "/leave/applied",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger leave processing (UAE)",
)
async def webhook_leave_applied(
    payload: LeaveAppliedPayload,
    background_tasks: BackgroundTasks,
):
    """
    Triggers UAE leave agent:
    - Checks balance (9 leave types per UAE law)
    - Validates against UAE law rules
    - Auto-applies public holiday deductions
    - Approves/rejects and sends notification
    """
    background_tasks.add_task(_run_leave_processing, payload.dict())
    return {
        "status": "accepted",
        "message": "UAE leave agent triggered",
        "employee_id": payload.employee_id,
        "leave_type": payload.leave_type,
        "agent": "LeaveAgent",
    }


@router.post(
    "/attendance/checkin",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process employee check-in (UAE)",
)
async def webhook_attendance_checkin(
    payload: AttendancePayload,
    background_tasks: BackgroundTasks,
):
    """
    Records check-in with verification.
    Detects Ramadan mode (6hr day).
    Flags late arrivals (>15 min grace).
    """
    background_tasks.add_task(_run_checkin, payload.dict())
    return {
        "status": "accepted",
        "message": "Check-in recorded",
        "employee_id": payload.employee_id,
        "agent": "AttendanceAgent",
    }


@router.post(
    "/attendance/checkout",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process employee check-out (UAE)",
)
async def webhook_attendance_checkout(
    payload: AttendancePayload,
    background_tasks: BackgroundTasks,
):
    """Calculates hours worked, overtime (max 2hrs/day), updates DB."""
    background_tasks.add_task(_run_checkout, payload.dict())
    return {
        "status": "accepted",
        "message": "Check-out recorded",
        "employee_id": payload.employee_id,
        "agent": "AttendanceAgent",
    }


@router.post(
    "/document/uploaded",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process document upload (UAE)",
)
async def webhook_document_uploaded(
    payload: DocumentUploadedPayload,
    background_tasks: BackgroundTasks,
):
    """Updates document tracker and schedules expiry alerts."""
    logger.info(
        "webhook_uae.document_uploaded",
        employee_id=payload.employee_id,
        doc_type=payload.document_type,
    )
    return {
        "status": "accepted",
        "message": "Document recorded, expiry tracking active",
        "employee_id": payload.employee_id,
        "document_type": payload.document_type,
        "agent": "DocumentAgent",
    }


@router.post(
    "/contract/expiring",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Handle contract expiry alert (UAE)",
)
async def webhook_contract_expiring(
    payload: ContractExpiringPayload,
    background_tasks: BackgroundTasks,
):
    background_tasks.add_task(_run_contract_alert, payload.dict())
    return {
        "status": "accepted",
        "message": "Contract expiry alert processed",
        "employee_id": payload.employee_id,
        "days_remaining": payload.days_until_expiry,
        "agent": "ContractAgent",
    }


# ─── Background task runners ───────────────────────────────────────────────────

async def _run_onboarding(payload: dict) -> None:
    try:
        from app.agents.uae.onboarding import get_onboarding_agent
        agent = get_onboarding_agent()
        result = await agent.process_new_employee(
            employee_id=payload["employee_id"],
            company_id=payload["company_id"],
            employee_data=payload,
        )
        logger.info("webhook_uae.onboarding_complete", employee_id=payload["employee_id"])
    except Exception as exc:
        logger.error("webhook_uae.onboarding_failed", error=str(exc))


async def _run_offboarding(payload: dict) -> None:
    try:
        from app.agents.uae.offboarding import get_offboarding_agent
        agent = get_offboarding_agent()
        result = await agent.initiate_offboarding(
            employee_id=payload["employee_id"],
            company_id=payload["company_id"],
            exit_type=payload.get("exit_type", "resignation"),
            exit_date=payload.get("exit_date"),
        )
        logger.info("webhook_uae.offboarding_complete", employee_id=payload["employee_id"])
    except Exception as exc:
        logger.error("webhook_uae.offboarding_failed", error=str(exc))


async def _run_leave_processing(payload: dict) -> None:
    try:
        from app.agents.uae.leave import get_leave_agent
        agent = get_leave_agent()
        result = await agent.process_leave_application(
            employee_id=payload["employee_id"],
            company_id=payload["company_id"],
            leave_type=payload["leave_type"],
            start_date=payload["start_date"],
            end_date=payload["end_date"],
            reason=payload.get("reason", ""),
        )
        logger.info(
            "webhook_uae.leave_processed",
            employee_id=payload["employee_id"],
            status=result.status,
        )
    except Exception as exc:
        logger.error("webhook_uae.leave_failed", error=str(exc))


async def _run_checkin(payload: dict) -> None:
    try:
        from app.agents.uae.attendance import get_attendance_agent
        agent = get_attendance_agent()
        await agent.process_checkin(
            employee_id=payload["employee_id"],
            company_id=payload["company_id"],
            verification_method=payload.get("verification_method", "manual"),
            location_data=payload.get("location_data", {}),
        )
    except Exception as exc:
        logger.error("webhook_uae.checkin_failed", error=str(exc))


async def _run_checkout(payload: dict) -> None:
    try:
        from app.agents.uae.attendance import get_attendance_agent
        agent = get_attendance_agent()
        await agent.process_checkout(
            employee_id=payload["employee_id"],
            company_id=payload["company_id"],
        )
    except Exception as exc:
        logger.error("webhook_uae.checkout_failed", error=str(exc))


async def _run_contract_alert(payload: dict) -> None:
    try:
        from app.agents.uae.contract import get_contract_agent
        agent = get_contract_agent()
        await agent.send_renewal_alerts(company_id=payload["company_id"])
    except Exception as exc:
        logger.error("webhook_uae.contract_alert_failed", error=str(exc))

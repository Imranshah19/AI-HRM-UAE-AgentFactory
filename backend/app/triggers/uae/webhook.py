"""
UAE Webhook Triggers — FastAPI routes for event-driven agent execution.

All webhooks run agents as background tasks (non-blocking).
Routes registered under prefix: /api/v1/uae/webhooks/

Uses LangGraph master graph (graph.run_uae_task) for all agent dispatch.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, status
from pydantic import BaseModel, Field

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
    exit_type: str = "resignation"
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
    event_type: str = "checkin"  # checkin | checkout
    timestamp: str = ""
    verification_method: str = "manual"
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
    logger.info(
        "webhook_uae.employee_joined",
        employee_id=payload.employee_id,
        company_id=payload.company_id,
    )
    background_tasks.add_task(_run_task, "onboarding", payload.company_id, payload.employee_id, {
        "employee_name": payload.name_en,
        "nationality": payload.nationality,
        "department": payload.department,
        "basic_salary": payload.basic_salary_aed,
        "start_date": payload.join_date,
    })
    return {
        "status": "accepted",
        "message": "UAE onboarding agent triggered",
        "employee_id": payload.employee_id,
        "agent": "onboarding",
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
    background_tasks.add_task(_run_task, "offboarding", payload.company_id, payload.employee_id, {
        "exit_reason": "resignation",
        "exit_date": payload.exit_date,
    })
    return {
        "status": "accepted",
        "message": "UAE offboarding agent triggered (resignation)",
        "employee_id": payload.employee_id,
        "agent": "offboarding",
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
    background_tasks.add_task(_run_task, "offboarding", payload.company_id, payload.employee_id, {
        "exit_reason": "termination",
        "exit_date": payload.exit_date,
    })
    return {
        "status": "accepted",
        "message": "UAE offboarding agent triggered (termination)",
        "employee_id": payload.employee_id,
        "agent": "offboarding",
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
    background_tasks.add_task(_run_task, "leave_apply", payload.company_id, payload.employee_id, {
        "leave_type": payload.leave_type,
        "start_date": payload.start_date,
        "end_date": payload.end_date,
        "reason": payload.reason,
    })
    return {
        "status": "accepted",
        "message": "UAE leave agent triggered",
        "employee_id": payload.employee_id,
        "leave_type": payload.leave_type,
        "agent": "leave",
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
    background_tasks.add_task(_run_task, "attendance", payload.company_id, payload.employee_id, {
        "event_type": "checkin",
        "timestamp": payload.timestamp,
        "verification_method": payload.verification_method,
        "location_data": payload.location_data,
    })
    return {
        "status": "accepted",
        "message": "Check-in recorded",
        "employee_id": payload.employee_id,
        "agent": "attendance",
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
    background_tasks.add_task(_run_task, "attendance", payload.company_id, payload.employee_id, {
        "event_type": "checkout",
        "timestamp": payload.timestamp,
        "verification_method": payload.verification_method,
        "location_data": payload.location_data,
    })
    return {
        "status": "accepted",
        "message": "Check-out recorded",
        "employee_id": payload.employee_id,
        "agent": "attendance",
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
    logger.info(
        "webhook_uae.document_uploaded",
        employee_id=payload.employee_id,
        doc_type=payload.document_type,
    )
    background_tasks.add_task(_run_task, "document_check", payload.company_id, payload.employee_id, {
        "document_type": payload.document_type,
        "document_number": payload.document_number,
        "expiry_date": payload.expiry_date,
    })
    return {
        "status": "accepted",
        "message": "Document recorded, expiry tracking active",
        "employee_id": payload.employee_id,
        "document_type": payload.document_type,
        "agent": "document",
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
    background_tasks.add_task(_run_task, "contract", payload.company_id, payload.employee_id, {
        "contract_end_date": payload.contract_end_date,
        "days_until_expiry": payload.days_until_expiry,
    })
    return {
        "status": "accepted",
        "message": "Contract expiry alert processed",
        "employee_id": payload.employee_id,
        "days_remaining": payload.days_until_expiry,
        "agent": "contract",
    }


# ─── Shared background runner ──────────────────────────────────────────────────

async def _run_task(
    task_type: str,
    company_id: str,
    employee_id: str,
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
            "webhook_uae.task_complete",
            task_type=task_type,
            company_id=company_id,
            employee_id=employee_id,
            status=result.get("status"),
        )
    except Exception as exc:
        logger.error(
            "webhook_uae.task_failed",
            task_type=task_type,
            company_id=company_id,
            error=str(exc),
        )

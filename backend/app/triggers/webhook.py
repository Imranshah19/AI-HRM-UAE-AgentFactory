"""
Agent Factory — Webhook Router for AI-HRMS.

Provides HTTP webhook endpoints that external systems (or internal services)
call to activate agents automatically.

Webhooks defined here:
  POST /agent/webhooks/leave/applied
      Called when a new leave request is submitted.
      Activates LeaveAgent → AI recommendation → stores result in Redis.

  POST /agent/webhooks/leave/status-changed
      Called when a leave request is approved/rejected.
      Logs the event; can trigger downstream automations.

  POST /agent/webhooks/attendance/checkin
      Called when an employee checks in late.
      Activates AttendanceAgent for late-arrival insight.

  GET  /agent/webhooks/health
      Liveness check for the webhook layer.

All endpoints are authenticated via the existing JWT dependency.
Registered under the /agent prefix in Phase 3 (api/v1/agents/router.py).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/agent/webhooks", tags=["Agent Webhooks"])


# ─── Webhook payload schemas ──────────────────────────────────────────────────

class LeaveAppliedPayload(BaseModel):
    leave_request_id: str = Field(..., description="UUID of the LeaveRequest row")
    tenant_id:        str
    employee_id:      str
    leave_type:       str | None = None
    start_date:       str | None = None
    end_date:         str | None = None
    total_days:       float | None = None

    model_config = {"json_schema_extra": {
        "example": {
            "leave_request_id": "550e8400-e29b-41d4-a716-446655440000",
            "tenant_id":        "system",
            "employee_id":      "550e8400-e29b-41d4-a716-446655440001",
            "leave_type":       "Annual",
            "start_date":       "2026-05-01",
            "end_date":         "2026-05-05",
            "total_days":       5.0,
        }
    }}


class LeaveStatusChangedPayload(BaseModel):
    leave_request_id: str
    tenant_id:        str
    employee_id:      str
    new_status:       str   # "approved" | "rejected" | "cancelled"
    changed_by:       str | None = None
    reason:           str | None = None


class AttendanceCheckinPayload(BaseModel):
    employee_id:  str
    tenant_id:    str
    check_in_time: str          # ISO datetime string
    minutes_late: int = 0
    source:       str = "web"   # "web" | "mobile" | "biometric"


class WebhookResponse(BaseModel):
    status:      str
    task_id:     str | None = None
    message:     str
    timestamp:   str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ─── Background task runners ──────────────────────────────────────────────────

async def _run_leave_analysis(
    leave_request_id: str,
    tenant_id: str,
    db: AsyncSession,
) -> None:
    """
    Background task: invoke LeaveAgent and cache the result in Redis.
    Does NOT block the HTTP response.
    """
    import json
    try:
        from app.agents.paperclip import get_paperclip
        from app.core.redis import get_redis

        paperclip = get_paperclip()
        result    = await paperclip.dispatch(
            domain="leave",
            action="analyse",
            payload={"leave_request_id": leave_request_id},
            tenant_id=tenant_id,
            db=db,
        )

        redis_key = f"agent:leave_analysis:{leave_request_id}"
        try:
            redis = get_redis()
            await redis.setex(
                redis_key,
                86400,          # TTL 24 hours
                json.dumps(result.to_dict(), default=str),
            )
            await redis.aclose()
        except Exception as redis_exc:
            logger.warning("webhook.leave_cache_failed", error=str(redis_exc))

        logger.info(
            "webhook.leave_analysis_complete",
            leave_request_id=leave_request_id,
            status=result.status,
            recommendation=getattr(result.result, "recommendation", "unknown"),
        )

    except Exception as exc:
        logger.exception(
            "webhook.leave_analysis_error",
            leave_request_id=leave_request_id,
            error=str(exc),
        )


async def _run_attendance_insight(
    employee_id: str,
    tenant_id: str,
    minutes_late: int,
    db: AsyncSession,
) -> None:
    """
    Background task: generate attendance insight for a late check-in.
    """
    try:
        from app.agents.paperclip import get_paperclip

        paperclip = get_paperclip()
        await paperclip.dispatch(
            domain="attendance",
            action="daily_report",
            payload={},
            tenant_id=tenant_id,
            db=db,
        )
        logger.info(
            "webhook.attendance_insight_complete",
            employee_id=employee_id,
            minutes_late=minutes_late,
        )
    except Exception as exc:
        logger.exception(
            "webhook.attendance_insight_error",
            employee_id=employee_id,
            error=str(exc),
        )


# ─── Webhook endpoints ────────────────────────────────────────────────────────

@router.post(
    "/leave/applied",
    response_model=WebhookResponse,
    summary="Webhook: New leave application submitted",
    description=(
        "Triggered when an employee submits a leave request. "
        "Activates the Leave Agent in the background to analyse "
        "the request and store an AI recommendation."
    ),
)
async def webhook_leave_applied(
    payload:          LeaveAppliedPayload,
    background_tasks: BackgroundTasks,
    db:               Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> WebhookResponse:
    import uuid
    task_id = str(uuid.uuid4())

    logger.info(
        "webhook.leave_applied",
        task_id=task_id,
        leave_request_id=payload.leave_request_id,
        employee_id=payload.employee_id,
        tenant_id=payload.tenant_id,
    )

    background_tasks.add_task(
        _run_leave_analysis,
        leave_request_id=payload.leave_request_id,
        tenant_id=payload.tenant_id,
        db=db,
    )

    return WebhookResponse(
        status="accepted",
        task_id=task_id,
        message=(
            f"Leave analysis for request {payload.leave_request_id} "
            "queued. Fetch result at GET /agent/triggers/leave/analysis/{leave_request_id}"
        ),
    )


@router.post(
    "/leave/status-changed",
    response_model=WebhookResponse,
    summary="Webhook: Leave request status changed",
)
async def webhook_leave_status_changed(
    payload:      LeaveStatusChangedPayload,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> WebhookResponse:
    import uuid

    logger.info(
        "webhook.leave_status_changed",
        leave_request_id=payload.leave_request_id,
        new_status=payload.new_status,
        tenant_id=payload.tenant_id,
    )

    # Future: trigger downstream agent actions based on status
    # e.g., update calendar, notify payroll if long unpaid leave, etc.

    if payload.new_status not in ("approved", "rejected", "cancelled", "recalled"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status: {payload.new_status}",
        )

    return WebhookResponse(
        status="received",
        task_id=str(uuid.uuid4()),
        message=f"Leave status change event logged: {payload.new_status}",
    )


@router.post(
    "/attendance/checkin",
    response_model=WebhookResponse,
    summary="Webhook: Employee check-in event (late arrival)",
)
async def webhook_attendance_checkin(
    payload:          AttendanceCheckinPayload,
    background_tasks: BackgroundTasks,
    db:               Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> WebhookResponse:
    import uuid
    task_id = str(uuid.uuid4())

    logger.info(
        "webhook.attendance_checkin",
        task_id=task_id,
        employee_id=payload.employee_id,
        minutes_late=payload.minutes_late,
    )

    if payload.minutes_late > 0:
        background_tasks.add_task(
            _run_attendance_insight,
            employee_id=payload.employee_id,
            tenant_id=payload.tenant_id,
            minutes_late=payload.minutes_late,
            db=db,
        )

    return WebhookResponse(
        status="accepted",
        task_id=task_id,
        message=(
            f"Check-in event received for employee {payload.employee_id}. "
            + (f"Late arrival insight queued ({payload.minutes_late} min late)."
               if payload.minutes_late > 0 else "On-time arrival logged.")
        ),
    )


@router.get(
    "/health",
    summary="Webhook layer health check",
    tags=["Agent Webhooks"],
)
async def webhook_health() -> dict:
    return {
        "status":     "healthy",
        "layer":      "agent_webhooks",
        "endpoints": [
            "POST /agent/webhooks/leave/applied",
            "POST /agent/webhooks/leave/status-changed",
            "POST /agent/webhooks/attendance/checkin",
        ],
    }

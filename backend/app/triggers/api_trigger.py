"""
Agent Factory — Manual Trigger API Endpoints for AI-HRMS.

These REST endpoints let HR managers and admins manually trigger agents
from the dashboard UI without waiting for the scheduled beat tasks.

Endpoints:
  POST /agent/triggers/leave/analyse/{request_id}
      Immediately analyse a leave request with AI.

  GET  /agent/triggers/leave/analysis/{request_id}
      Retrieve a cached leave analysis result from Redis.

  POST /agent/triggers/payroll/validate/{run_id}
      Validate a payroll run with AI before approving.

  POST /agent/triggers/payroll/summarise/{run_id}
      Generate an AI summary of a completed payroll run.

  POST /agent/triggers/attendance/report
      Trigger a daily attendance report manually.

  GET  /agent/triggers/attendance/absentees
      Get list of chronic absentees (last 30 days).

  GET  /agent/triggers/agents/status
      Health and capability status of all registered agents.

  GET  /agent/triggers/agents/logs
      Recent agent execution logs (from Redis).

All endpoints require authentication and superadmin / hr_manager role.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/agent/triggers", tags=["Agent Triggers"])


# ─── Response schemas ─────────────────────────────────────────────────────────

class TriggerResponse(BaseModel):
    task_id:    str
    domain:     str
    action:     str
    status:     str
    result:     dict | None = None
    duration_ms: float | None = None
    timestamp:  str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class AgentStatusResponse(BaseModel):
    agents:     dict
    openclaw:   dict
    timestamp:  str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ─── Leave triggers ───────────────────────────────────────────────────────────

@router.post(
    "/leave/analyse/{request_id}",
    response_model=TriggerResponse,
    summary="AI: Analyse a leave request",
    description=(
        "Immediately invoke the Leave Agent to analyse a leave request. "
        "Returns the AI recommendation (approve/reject/review), reason, "
        "flags, and a draft manager message."
    ),
)
async def trigger_leave_analysis(
    request_id:   str,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TriggerResponse:
    tenant_id = _get_tenant_id(current_user)

    from app.agents.paperclip import get_paperclip
    paperclip  = get_paperclip()
    task_result = await paperclip.dispatch(
        domain="leave",
        action="analyse",
        payload={"leave_request_id": request_id},
        tenant_id=tenant_id,
        db=db,
    )

    return TriggerResponse(
        task_id=task_result.task_id,
        domain=task_result.domain,
        action=task_result.action,
        status=task_result.status,
        result=_serialise_result(task_result.result),
        duration_ms=task_result.duration_ms,
    )


@router.get(
    "/leave/analysis/{request_id}",
    summary="Get cached leave analysis result",
    description="Retrieve a previously cached AI analysis for a leave request from Redis.",
)
async def get_leave_analysis(
    request_id:   str,
    current_user=Depends(get_current_user),
) -> dict:
    redis_key = f"agent:leave_analysis:{request_id}"
    try:
        from app.core.redis import get_redis
        redis  = get_redis()
        cached = await redis.get(redis_key)
        await redis.aclose()

        if cached is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No cached analysis for leave request {request_id}. "
                       "Trigger one via POST /agent/triggers/leave/analyse/{request_id}",
            )
        return json.loads(cached)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("get_leave_analysis.redis_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Redis unavailable — cannot retrieve cached analysis.",
        )


@router.post(
    "/leave/detect-anomalies",
    response_model=TriggerResponse,
    summary="AI: Detect leave anomalies across all employees",
)
async def trigger_leave_anomalies(
    db:           Annotated[AsyncSession, Depends(get_db)],
    lookback_days: int = Query(default=90, ge=7, le=365),
    current_user=Depends(get_current_user),
) -> TriggerResponse:
    tenant_id = _get_tenant_id(current_user)

    from app.agents.paperclip import get_paperclip
    paperclip   = get_paperclip()
    task_result = await paperclip.dispatch(
        domain="leave",
        action="detect_anomalies",
        payload={"lookback_days": lookback_days},
        tenant_id=tenant_id,
        db=db,
    )

    return TriggerResponse(
        task_id=task_result.task_id,
        domain=task_result.domain,
        action=task_result.action,
        status=task_result.status,
        result=_serialise_result(task_result.result),
        duration_ms=task_result.duration_ms,
    )


# ─── Payroll triggers ─────────────────────────────────────────────────────────

@router.post(
    "/payroll/validate/{run_id}",
    response_model=TriggerResponse,
    summary="AI: Validate a payroll run before approval",
    description=(
        "Run the AI payroll validation agent on a payroll run. "
        "Returns recommendation (approve/hold/reject), anomalies found, "
        "compliance flags, and an overall risk score (0-100)."
    ),
)
async def trigger_payroll_validation(
    run_id:       str,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TriggerResponse:
    tenant_id   = _get_tenant_id(current_user)

    from app.agents.paperclip import get_paperclip
    paperclip   = get_paperclip()
    task_result = await paperclip.dispatch(
        domain="payroll",
        action="validate",
        payload={"run_id": run_id},
        tenant_id=tenant_id,
        db=db,
    )

    return TriggerResponse(
        task_id=task_result.task_id,
        domain=task_result.domain,
        action=task_result.action,
        status=task_result.status,
        result=_serialise_result(task_result.result),
        duration_ms=task_result.duration_ms,
    )


@router.post(
    "/payroll/summarise/{run_id}",
    response_model=TriggerResponse,
    summary="AI: Generate natural-language payroll summary",
    description="Ask Claude to write a plain-English HR summary of a processed payroll run.",
)
async def trigger_payroll_summary(
    run_id:       str,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> TriggerResponse:
    tenant_id   = _get_tenant_id(current_user)

    from app.agents.paperclip import get_paperclip
    paperclip   = get_paperclip()
    task_result = await paperclip.dispatch(
        domain="payroll",
        action="summarise",
        payload={"run_id": run_id},
        tenant_id=tenant_id,
        db=db,
    )

    return TriggerResponse(
        task_id=task_result.task_id,
        domain=task_result.domain,
        action=task_result.action,
        status=task_result.status,
        result=_serialise_result(task_result.result),
        duration_ms=task_result.duration_ms,
    )


# ─── Attendance triggers ──────────────────────────────────────────────────────

@router.post(
    "/attendance/report",
    response_model=TriggerResponse,
    summary="AI: Generate today's attendance report",
    description=(
        "Manually trigger the daily attendance report. "
        "Returns attendance stats, absent/late employees, and AI insights."
    ),
)
async def trigger_attendance_report(
    db:           Annotated[AsyncSession, Depends(get_db)],
    report_date:  str | None = Query(default=None, description="ISO date, defaults to today"),
    current_user=Depends(get_current_user),
) -> TriggerResponse:
    tenant_id = _get_tenant_id(current_user)

    parsed_date = None
    if report_date:
        try:
            parsed_date = date.fromisoformat(report_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date format: {report_date}. Use YYYY-MM-DD.",
            )

    from app.agents.paperclip import get_paperclip
    paperclip   = get_paperclip()
    task_result = await paperclip.dispatch(
        domain="attendance",
        action="daily_report",
        payload={"report_date": parsed_date or date.today()},
        tenant_id=tenant_id,
        db=db,
    )

    return TriggerResponse(
        task_id=task_result.task_id,
        domain=task_result.domain,
        action=task_result.action,
        status=task_result.status,
        result=_serialise_result(task_result.result),
        duration_ms=task_result.duration_ms,
    )


@router.get(
    "/attendance/absentees",
    summary="AI: List chronic absentees",
    description="Detect employees with 5+ absences in the last N days.",
)
async def trigger_chronic_absentees(
    db:            Annotated[AsyncSession, Depends(get_db)],
    lookback_days: int = Query(default=30, ge=7, le=365),
    min_absences:  int = Query(default=5, ge=1, le=50),
    current_user=Depends(get_current_user),
) -> TriggerResponse:
    tenant_id   = _get_tenant_id(current_user)

    from app.agents.paperclip import get_paperclip
    paperclip   = get_paperclip()
    task_result = await paperclip.dispatch(
        domain="attendance",
        action="chronic_absentees",
        payload={"lookback_days": lookback_days, "threshold_absences": min_absences},
        tenant_id=tenant_id,
        db=db,
    )

    return TriggerResponse(
        task_id=task_result.task_id,
        domain=task_result.domain,
        action=task_result.action,
        status=task_result.status,
        result=_serialise_result(task_result.result),
        duration_ms=task_result.duration_ms,
    )


@router.get(
    "/attendance/late-trend",
    summary="Late arrival trend (last N days)",
)
async def trigger_late_trend(
    db:           Annotated[AsyncSession, Depends(get_db)],
    days:         int = Query(default=7, ge=1, le=30),
    current_user=Depends(get_current_user),
) -> TriggerResponse:
    tenant_id   = _get_tenant_id(current_user)

    from app.agents.paperclip import get_paperclip
    paperclip   = get_paperclip()
    task_result = await paperclip.dispatch(
        domain="attendance",
        action="late_trend",
        payload={"days": days},
        tenant_id=tenant_id,
        db=db,
    )

    return TriggerResponse(
        task_id=task_result.task_id,
        domain=task_result.domain,
        action=task_result.action,
        status=task_result.status,
        result=_serialise_result(task_result.result),
        duration_ms=task_result.duration_ms,
    )


# ─── Agent status & logs ──────────────────────────────────────────────────────

@router.get(
    "/agents/status",
    response_model=AgentStatusResponse,
    summary="Agent Factory: Status of all agents",
    description="Returns which agents are registered, their available actions, and OpenClaw API status.",
)
async def get_agents_status(
    current_user=Depends(get_current_user),
) -> AgentStatusResponse:
    from app.agents.paperclip import get_paperclip
    from app.agents.openclaw import get_openclaw

    paperclip = get_paperclip()
    claw      = get_openclaw()

    agents_status = await paperclip.get_agent_status()
    openclaw_status = {
        "model":        claw.model,
        "api_key_set":  bool(claw.api_key),
        "max_tokens":   claw.max_tokens,
        "mode":         "live" if claw.api_key else "mock",
    }

    return AgentStatusResponse(
        agents=agents_status,
        openclaw=openclaw_status,
    )


@router.get(
    "/agents/logs",
    summary="Agent Factory: Recent execution logs",
    description="Returns last N agent task executions from Redis.",
)
async def get_agent_logs(
    limit:        int = Query(default=20, ge=1, le=100),
    current_user=Depends(get_current_user),
) -> dict:
    from app.agents.paperclip import get_paperclip

    paperclip = get_paperclip()
    logs      = await paperclip.get_agent_logs(limit=limit)

    return {
        "count":     len(logs),
        "logs":      logs,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ─── Private helpers ──────────────────────────────────────────────────────────

def _get_tenant_id(current_user) -> str:
    """Extract tenant_id from the current authenticated user object."""
    if hasattr(current_user, "tenant_id"):
        return str(current_user.tenant_id)
    if isinstance(current_user, dict):
        return str(current_user.get("tenant_id", "system"))
    return "system"


def _serialise_result(result) -> dict | None:
    if result is None:
        return None
    if isinstance(result, dict):
        return result
    if isinstance(result, list):
        return {"items": result, "count": len(result)}
    if hasattr(result, "to_dict"):
        return result.to_dict()
    if hasattr(result, "__dict__"):
        return {k: v for k, v in result.__dict__.items() if not k.startswith("_")}
    return {"value": str(result)}

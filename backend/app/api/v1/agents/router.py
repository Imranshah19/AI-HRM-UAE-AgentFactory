"""
Agent Factory — Unified Agent Router (API v1).

This is the single registration point for ALL agent routes.
It is included into the existing v1_router in api/v1/router.py
with 2 additive lines — no existing routes are changed.

Route map (all under /api/v1):
  ┌─────────────────────────────────────────────────────────────────┐
  │  Source                │  Prefix                               │
  ├────────────────────────┼───────────────────────────────────────┤
  │  triggers/webhook.py   │  /agent/webhooks/*                    │
  │  triggers/api_trigger  │  /agent/triggers/*                    │
  │  This file             │  /agent/status                        │
  │  This file             │  /agent/logs                          │
  │  This file             │  /agent/logs/{task_id}                │
  └─────────────────────────────────────────────────────────────────┘

OpenClaw (Claude API) connection status:
  - Reads ANTHROPIC_API_KEY from os.environ
  - /agent/status.openclaw.mode = "live" | "mock"
  - All 4 agents (Leave, Payroll, Attendance, Chatbot) share the same
    OpenClaw singleton — instantiated on first request, cached for lifetime
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.triggers.webhook import router as webhook_router
from app.triggers.api_trigger import router as trigger_router

logger = structlog.get_logger(__name__)

# ─── Master agent router ──────────────────────────────────────────────────────

agent_router = APIRouter(tags=["Agent Factory"])

# Mount Phase 2 routers (they carry their own prefixes)
agent_router.include_router(webhook_router)   # /agent/webhooks/*
agent_router.include_router(trigger_router)   # /agent/triggers/*


# ─── DB log helper ────────────────────────────────────────────────────────────

async def _persist_agent_log(
    db:           AsyncSession,
    task_result,
    tenant_id:    str,
    triggered_by: str = "api",
    user_id:      str | None = None,
) -> None:
    """
    Write an AgentTaskResult to the agent_logs table.
    Called by status/trigger endpoints after Paperclip.dispatch() returns.
    Safe to call fire-and-forget — errors are logged but not re-raised.
    """
    try:
        from app.models.agent_log import AgentLog

        result_data = None
        if task_result.result is not None:
            if hasattr(task_result.result, "to_dict"):
                result_data = task_result.result.to_dict()
            elif isinstance(task_result.result, dict):
                result_data = task_result.result
            else:
                result_data = {"value": str(task_result.result)}

        model_used   = None
        input_tokens = None
        output_tokens = None

        if isinstance(result_data, dict):
            model_used    = result_data.get("model")
            input_tokens  = result_data.get("input_tokens")
            output_tokens = result_data.get("output_tokens")

        log = AgentLog(
            task_id=task_result.task_id,
            agent_name=task_result.agent_name,
            domain=task_result.domain,
            action=task_result.action,
            status=task_result.status,
            result=result_data,
            duration_ms=task_result.duration_ms,
            tenant_id=tenant_id,
            triggered_by=triggered_by,
            triggered_by_user_id=user_id,
            model_used=model_used,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        db.add(log)
        await db.flush()
    except Exception as exc:
        logger.warning("agent_log.persist_failed", error=str(exc))


# ─── /agent/status ───────────────────────────────────────────────────────────

@agent_router.get(
    "/agent/status",
    summary="Agent Factory: Full system status",
    description=(
        "Returns the live status of all agents, OpenClaw (Claude API) "
        "connection, Celery beat schedule, and a snapshot of recent executions."
    ),
    tags=["Agent Factory"],
)
async def agent_system_status(
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    from app.agents.paperclip import get_paperclip
    from app.agents.openclaw import get_openclaw
    from app.models.agent_log import AgentLog
    from app.triggers.scheduler import AGENT_BEAT_SCHEDULE

    paperclip = get_paperclip()
    claw      = get_openclaw()

    # ── OpenClaw status ────────────────────────────────────────────────────────
    openclaw_status = {
        "model":           claw.model,
        "api_key_set":     bool(claw.api_key),
        "api_key_preview": (
            f"{claw.api_key[:8]}…"
            if claw.api_key else "NOT SET — using mock responses"
        ),
        "max_tokens":      claw.max_tokens,
        "mode":            "live" if claw.api_key else "mock",
        "hint": (
            None if claw.api_key
            else "Set ANTHROPIC_API_KEY environment variable to enable real Claude responses"
        ),
    }

    # ── Agents capability map ──────────────────────────────────────────────────
    agents_status = await paperclip.get_agent_status()

    # ── Beat schedule ──────────────────────────────────────────────────────────
    schedule_info = {}
    for key, entry in AGENT_BEAT_SCHEDULE.items():
        sched = entry["schedule"]
        schedule_info[key] = {
            "task":     entry["task"],
            "schedule": str(sched),
        }

    # ── Recent DB logs (last 10) ───────────────────────────────────────────────
    try:
        recent_rows = await db.execute(
            select(AgentLog)
            .order_by(desc(AgentLog.created_at))
            .limit(10)
        )
        recent_logs = [r.to_dict() for r in recent_rows.scalars().all()]
    except Exception:
        recent_logs = []

    # ── DB stats ──────────────────────────────────────────────────────────────
    db_stats: dict = {}
    try:
        from sqlalchemy import func
        stats_rows = await db.execute(
            select(
                AgentLog.domain,
                AgentLog.status,
                func.count(AgentLog.id).label("cnt"),
            )
            .group_by(AgentLog.domain, AgentLog.status)
        )
        for row in stats_rows.fetchall():
            db_stats.setdefault(row.domain, {})[row.status] = row.cnt
    except Exception:
        pass

    # ── Redis log count ───────────────────────────────────────────────────────
    redis_log_count = 0
    try:
        from app.core.redis import get_redis
        redis = get_redis()
        redis_log_count = await redis.llen("agent:logs")
        await redis.aclose()
    except Exception:
        pass

    return {
        "timestamp":     datetime.now(timezone.utc).isoformat(),
        "system":        "AI-HRMS Agent Factory",
        "version":       "1.0.0",
        "openclaw":      openclaw_status,
        "agents":        agents_status,
        "beat_schedule": schedule_info,
        "logs": {
            "redis_count":  redis_log_count,
            "db_stats":     db_stats,
            "recent":       recent_logs,
        },
        "routes": {
            "webhooks":  "/api/v1/agent/webhooks",
            "triggers":  "/api/v1/agent/triggers",
            "status":    "/api/v1/agent/status",
            "logs":      "/api/v1/agent/logs",
        },
    }


# ─── /agent/logs — DB-backed history ─────────────────────────────────────────

@agent_router.get(
    "/agent/logs",
    summary="Agent Factory: Execution history (DB)",
    description=(
        "Queryable, persistent log of all agent task executions. "
        "Filterable by domain, action, status, and date range."
    ),
    tags=["Agent Factory"],
)
async def list_agent_logs(
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
    domain:       str | None = Query(default=None),
    action:       str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    triggered_by: str | None = Query(default=None),
    date_from:    str | None = Query(default=None, description="ISO date, e.g. 2026-04-01"),
    date_to:      str | None = Query(default=None, description="ISO date, e.g. 2026-04-30"),
    limit:        int         = Query(default=25, ge=1, le=100),
    offset:       int         = Query(default=0, ge=0),
) -> dict:
    from app.models.agent_log import AgentLog
    from sqlalchemy import func

    q = select(AgentLog).order_by(desc(AgentLog.created_at))

    if domain:
        q = q.where(AgentLog.domain == domain)
    if action:
        q = q.where(AgentLog.action == action)
    if status_filter:
        q = q.where(AgentLog.status == status_filter)
    if triggered_by:
        q = q.where(AgentLog.triggered_by == triggered_by)
    if date_from:
        try:
            q = q.where(AgentLog.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date_from: {date_from}",
            )
    if date_to:
        try:
            q = q.where(AgentLog.created_at <= datetime.fromisoformat(date_to + "T23:59:59"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid date_to: {date_to}",
            )

    count_q = select(func.count()).select_from(q.subquery())
    total   = (await db.execute(count_q)).scalar() or 0

    rows = await db.execute(q.limit(limit).offset(offset))
    logs = [r.to_dict() for r in rows.scalars().all()]

    return {
        "total":  total,
        "limit":  limit,
        "offset": offset,
        "logs":   logs,
    }


@agent_router.get(
    "/agent/logs/{task_id}",
    summary="Agent Factory: Single execution log by task_id",
    tags=["Agent Factory"],
)
async def get_agent_log_by_task(
    task_id:      str,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    from app.models.agent_log import AgentLog

    row = await db.execute(
        select(AgentLog).where(AgentLog.task_id == task_id)
    )
    log = row.scalar_one_or_none()
    if log is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent log with task_id '{task_id}' not found.",
        )
    return log.to_dict()


# ─── /agent/logs — write endpoint (called internally by triggers) ──────────

@agent_router.post(
    "/agent/logs",
    status_code=status.HTTP_201_CREATED,
    summary="Agent Factory: Persist an agent task result",
    description=(
        "Internal endpoint called by webhook and trigger handlers to persist "
        "agent results to the DB. Not intended for direct external use."
    ),
    tags=["Agent Factory"],
    include_in_schema=False,
)
async def create_agent_log(
    payload:      dict,
    db:           Annotated[AsyncSession, Depends(get_db)],
    current_user=Depends(get_current_user),
) -> dict:
    from app.models.agent_log import AgentLog

    required = {"task_id", "agent_name", "domain", "action", "status"}
    missing  = required - set(payload.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Missing required fields: {missing}",
        )

    log = AgentLog(
        task_id=payload["task_id"],
        agent_name=payload["agent_name"],
        domain=payload["domain"],
        action=payload["action"],
        status=payload["status"],
        result=payload.get("result"),
        duration_ms=payload.get("duration_ms"),
        tenant_id=payload.get("tenant_id"),
        triggered_by=payload.get("triggered_by", "api"),
        triggered_by_user_id=payload.get("triggered_by_user_id"),
        model_used=payload.get("model_used"),
        input_tokens=payload.get("input_tokens"),
        output_tokens=payload.get("output_tokens"),
    )
    db.add(log)
    await db.flush()
    return log.to_dict()

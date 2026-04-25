"""
Paperclip — Agent Orchestrator for AI-HRMS Agent Factory.

Paperclip is the central routing layer that:
  1. Receives an agent task request (with domain + action)
  2. Routes it to the correct specialist agent
  3. Returns a unified AgentTaskResult
  4. Logs all agent executions to Redis for the dashboard

Think of Paperclip as the "manager" and the individual agents as "specialists".

Usage:
    from app.agents.paperclip import get_paperclip

    orchestrator = get_paperclip()
    result = await orchestrator.dispatch(
        domain="leave",
        action="analyse",
        payload={"leave_request_id": "uuid..."},
        db=db,
        tenant_id="...",
    )
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ─── Task schemas ─────────────────────────────────────────────────────────────

@dataclass
class AgentTaskResult:
    task_id:    str
    domain:     str
    action:     str
    status:     str          # "success" | "error" | "skipped"
    result:     Any
    agent_name: str
    duration_ms: float
    timestamp:  str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        result_data = self.result
        if hasattr(self.result, "to_dict"):
            result_data = self.result.to_dict()
        elif hasattr(self.result, "__dict__"):
            result_data = self.result.__dict__

        return {
            "task_id":    self.task_id,
            "domain":     self.domain,
            "action":     self.action,
            "status":     self.status,
            "result":     result_data,
            "agent_name": self.agent_name,
            "duration_ms": self.duration_ms,
            "timestamp":  self.timestamp,
        }


# ─── Domain ↔ Agent routing table ────────────────────────────────────────────

# Lazy imports — agents only loaded when needed
AGENT_REGISTRY: dict[str, dict] = {
    "leave": {
        "loader":  "app.agents.leave_agent:get_leave_agent",
        "actions": {
            "analyse":          "analyse_leave_request",
            "detect_anomalies": "detect_anomalies",
        },
    },
    "payroll": {
        "loader":  "app.agents.payroll_agent:get_payroll_agent",
        "actions": {
            "validate": "validate_payroll_run",
            "summarise": "generate_payroll_summary",
        },
    },
    "attendance": {
        "loader":  "app.agents.attendance_agent:get_attendance_agent",
        "actions": {
            "daily_report":     "generate_daily_report",
            "chronic_absentees": "detect_chronic_absentees",
            "late_trend":       "get_late_arrival_trend",
        },
    },
    "chatbot": {
        "loader":  "app.agents.chatbot_agent:get_chatbot_agent",
        "actions": {
            "answer": "answer",
        },
    },
}


# ─── Paperclip Orchestrator ───────────────────────────────────────────────────

class Paperclip:
    """
    Central agent orchestrator. Routes task requests to specialist agents
    and persists execution logs in Redis for the dashboard.
    """

    REDIS_LOG_KEY    = "agent:logs"
    REDIS_LOG_MAXLEN = 500    # max events kept in Redis stream

    def __init__(self):
        self._agents: dict[str, Any] = {}

    async def dispatch(
        self,
        domain:    str,
        action:    str,
        payload:   dict,
        tenant_id: str,
        db=None,
    ) -> AgentTaskResult:
        """
        Route a task to the appropriate agent and return a unified result.

        Args:
            domain:    "leave" | "payroll" | "attendance" | "chatbot"
            action:    domain-specific action key (see AGENT_REGISTRY)
            payload:   keyword args forwarded to the agent method
            tenant_id: current tenant
            db:        AsyncSession (required for DB-backed agents)
        """
        task_id = str(uuid.uuid4())
        start   = time.monotonic()

        logger.info(
            "paperclip.dispatch",
            task_id=task_id,
            domain=domain,
            action=action,
            tenant_id=tenant_id,
        )

        if domain not in AGENT_REGISTRY:
            return self._error_result(
                task_id, domain, action, start,
                f"Unknown domain '{domain}'. Valid: {list(AGENT_REGISTRY.keys())}",
            )

        reg = AGENT_REGISTRY[domain]
        if action not in reg["actions"]:
            return self._error_result(
                task_id, domain, action, start,
                f"Unknown action '{action}' for domain '{domain}'. "
                f"Valid: {list(reg['actions'].keys())}",
            )

        try:
            agent = self._load_agent(domain, reg["loader"])
        except Exception as exc:
            return self._error_result(task_id, domain, action, start, str(exc))

        method_name = reg["actions"][action]
        method      = getattr(agent, method_name, None)
        if method is None:
            return self._error_result(
                task_id, domain, action, start,
                f"Agent method '{method_name}' not found on {type(agent).__name__}",
            )

        try:
            call_kwargs: dict[str, Any] = dict(payload)
            if db is not None:
                call_kwargs["db"] = db
            if "tenant_id" not in call_kwargs:
                call_kwargs["tenant_id"] = tenant_id

            result = await method(**call_kwargs)
            duration = (time.monotonic() - start) * 1000

            task_result = AgentTaskResult(
                task_id=task_id,
                domain=domain,
                action=action,
                status="success",
                result=result,
                agent_name=type(agent).__name__,
                duration_ms=round(duration, 1),
            )

            logger.info(
                "paperclip.success",
                task_id=task_id,
                duration_ms=task_result.duration_ms,
            )

        except Exception as exc:
            logger.exception("paperclip.agent_error", task_id=task_id, error=str(exc))
            task_result = self._error_result(task_id, domain, action, start, str(exc))

        await self._log_to_redis(task_result)
        return task_result

    async def get_agent_logs(self, limit: int = 50) -> list[dict]:
        """
        Retrieve the last N agent execution logs from Redis.
        Returns an empty list if Redis is unavailable.
        """
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            raw   = await redis.lrange(self.REDIS_LOG_KEY, 0, limit - 1)
            await redis.aclose()
            return [json.loads(item) for item in raw]
        except Exception as exc:
            logger.warning("paperclip.redis_log_read_failed", error=str(exc))
            return []

    async def get_agent_status(self) -> dict:
        """
        Return health status of all registered agents.
        """
        return {
            domain: {
                "available": True,
                "actions":   list(reg["actions"].keys()),
            }
            for domain, reg in AGENT_REGISTRY.items()
        }

    # ── Private helpers ────────────────────────────────────────────────────────

    def _load_agent(self, domain: str, loader_path: str) -> Any:
        if domain in self._agents:
            return self._agents[domain]

        module_path, func_name = loader_path.split(":")
        import importlib
        module = importlib.import_module(module_path)
        factory = getattr(module, func_name)
        agent = factory()
        self._agents[domain] = agent
        return agent

    def _error_result(
        self, task_id: str, domain: str, action: str, start: float, error_msg: str
    ) -> AgentTaskResult:
        duration = (time.monotonic() - start) * 1000
        logger.error("paperclip.error", task_id=task_id, error=error_msg)
        return AgentTaskResult(
            task_id=task_id,
            domain=domain,
            action=action,
            status="error",
            result={"error": error_msg},
            agent_name="Paperclip",
            duration_ms=round(duration, 1),
        )

    async def _log_to_redis(self, result: AgentTaskResult) -> None:
        try:
            from app.core.redis import get_redis
            redis  = get_redis()
            entry  = json.dumps(result.to_dict(), default=str)
            await redis.lpush(self.REDIS_LOG_KEY, entry)
            await redis.ltrim(self.REDIS_LOG_KEY, 0, self.REDIS_LOG_MAXLEN - 1)
            await redis.aclose()
        except Exception as exc:
            logger.warning("paperclip.redis_log_write_failed", error=str(exc))


# ─── Singleton ────────────────────────────────────────────────────────────────

_paperclip: Paperclip | None = None


def get_paperclip() -> Paperclip:
    global _paperclip
    if _paperclip is None:
        _paperclip = Paperclip()
    return _paperclip

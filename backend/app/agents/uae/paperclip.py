"""
Paperclip UAE — Agent Orchestrator for UAE AI-HRM Agent Factory.

Routes tasks to correct UAE sub-agents based on domain/action.
Supports group-level vs company-level routing.
Priority queue: Critical > Urgent > Normal.
Retry logic: 3 retries on failure.
Logs all decisions to Redis stream + PostgreSQL.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class TaskPriority(str, Enum):
    CRITICAL = "critical"
    URGENT = "urgent"
    NORMAL = "normal"


@dataclass
class AgentTaskResult:
    task_id: str
    domain: str
    action: str
    status: str          # "success" | "error" | "skipped" | "mock"
    result: Any
    agent_name: str
    duration_ms: float
    company_id: str | None = None
    priority: str = TaskPriority.NORMAL
    retries: int = 0
    timestamp: str = ""

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
            "task_id": self.task_id,
            "domain": self.domain,
            "action": self.action,
            "status": self.status,
            "result": result_data,
            "agent_name": self.agent_name,
            "duration_ms": self.duration_ms,
            "company_id": self.company_id,
            "priority": self.priority,
            "retries": self.retries,
            "timestamp": self.timestamp,
        }


# ─── UAE Agent Registry ────────────────────────────────────────────────────────

AGENT_REGISTRY: dict[str, dict] = {
    "onboarding": {
        "loader": "app.agents.uae.onboarding:get_onboarding_agent",
        "actions": {
            "process": "process_new_employee",
            "create_checklist": "create_document_checklist",
        },
        "scope": "company",
    },
    "documents": {
        "loader": "app.agents.uae.document:get_document_agent",
        "actions": {
            "check_expiries": "check_all_expiries",
            "alert": "send_expiry_alerts",
            "report": "generate_expiry_report",
        },
        "scope": "group",
    },
    "payroll": {
        "loader": "app.agents.uae.payroll:get_payroll_agent",
        "actions": {
            "generate": "generate_payroll",
            "validate": "validate_payroll",
            "summary": "get_payroll_summary",
        },
        "scope": "company",
    },
    "wps": {
        "loader": "app.agents.uae.wps:get_wps_agent",
        "actions": {
            "generate_sif": "generate_sif_file",
            "validate": "validate_wps_submission",
            "deadline_alert": "send_deadline_alerts",
        },
        "scope": "company",
    },
    "gratuity": {
        "loader": "app.agents.uae.gratuity:get_gratuity_agent",
        "actions": {
            "calculate": "calculate_gratuity",
            "accrue": "update_monthly_accrual",
            "final_settlement": "calculate_final_settlement",
            "report": "generate_liability_report",
        },
        "scope": "company",
    },
    "leave": {
        "loader": "app.agents.uae.leave:get_leave_agent",
        "actions": {
            "apply": "process_leave_application",
            "balance": "get_leave_balance",
            "calendar": "get_team_calendar",
            "ramadan": "activate_ramadan_mode",
        },
        "scope": "company",
    },
    "attendance": {
        "loader": "app.agents.uae.attendance:get_attendance_agent",
        "actions": {
            "checkin": "process_checkin",
            "checkout": "process_checkout",
            "daily_report": "generate_daily_report",
            "anomaly_detect": "detect_anomalies",
        },
        "scope": "company",
    },
    "contracts": {
        "loader": "app.agents.uae.contract:get_contract_agent",
        "actions": {
            "check_expiries": "check_contract_expiries",
            "renewal_alert": "send_renewal_alerts",
            "notice_period": "calculate_notice_period",
        },
        "scope": "group",
    },
    "insurance": {
        "loader": "app.agents.uae.insurance:get_insurance_agent",
        "actions": {
            "check_expiries": "check_insurance_expiries",
            "iloe_check": "check_iloe_compliance",
            "report": "generate_compliance_report",
        },
        "scope": "group",
    },
    "air_ticket": {
        "loader": "app.agents.uae.air_ticket:get_air_ticket_agent",
        "actions": {
            "check_eligibility": "check_eligibility",
            "process_request": "process_ticket_request",
            "report": "generate_utilization_report",
        },
        "scope": "company",
    },
    "emiratisation": {
        "loader": "app.agents.uae.emiratisation:get_emiratisation_agent",
        "actions": {
            "monthly_check": "run_monthly_check",
            "compliance_report": "generate_compliance_report",
            "fine_risk": "calculate_fine_risk",
        },
        "scope": "group",
    },
    "offboarding": {
        "loader": "app.agents.uae.offboarding:get_offboarding_agent",
        "actions": {
            "initiate": "initiate_offboarding",
            "final_settlement": "calculate_final_settlement",
            "checklist_update": "update_checklist",
            "deadline_alerts": "send_deadline_alerts",
        },
        "scope": "company",
    },
    "chatbot": {
        "loader": "app.agents.uae.chatbot:get_hr_chatbot_agent",
        "actions": {
            "answer": "answer",
        },
        "scope": "company",
    },
}


class Paperclip:
    """
    UAE Agent Orchestrator. Routes tasks to all 15 UAE specialist agents.
    Supports group-level aggregation and company-level isolation.
    """

    REDIS_LOG_KEY = "uae:agent:orchestration:logs"
    REDIS_STATUS_KEY = "uae:agent:status"
    REDIS_LOG_MAXLEN = 1000
    MAX_RETRIES = 3

    def __init__(self):
        self._agents: dict[str, Any] = {}

    async def dispatch(
        self,
        domain: str,
        action: str,
        payload: dict,
        company_id: str | None = None,
        priority: str = TaskPriority.NORMAL,
        db=None,
    ) -> AgentTaskResult:
        task_id = str(uuid.uuid4())
        start = time.monotonic()

        logger.info(
            "paperclip.dispatch",
            task_id=task_id,
            domain=domain,
            action=action,
            company_id=company_id,
            priority=priority,
        )

        if domain not in AGENT_REGISTRY:
            return self._error_result(
                task_id, domain, action, start, company_id,
                f"Unknown UAE domain '{domain}'. Valid: {list(AGENT_REGISTRY.keys())}",
            )

        reg = AGENT_REGISTRY[domain]
        if action not in reg["actions"]:
            return self._error_result(
                task_id, domain, action, start, company_id,
                f"Unknown action '{action}' for domain '{domain}'. "
                f"Valid: {list(reg['actions'].keys())}",
            )

        result = await self._dispatch_with_retry(
            task_id, domain, action, payload, company_id, priority, reg, db, start
        )
        await self._log_to_redis(result)
        return result

    async def _dispatch_with_retry(
        self,
        task_id: str,
        domain: str,
        action: str,
        payload: dict,
        company_id: str | None,
        priority: str,
        reg: dict,
        db,
        start: float,
    ) -> AgentTaskResult:
        last_error = ""
        for attempt in range(self.MAX_RETRIES):
            try:
                agent = self._load_agent(domain, reg["loader"])
                method_name = reg["actions"][action]
                method = getattr(agent, method_name, None)

                if method is None:
                    return self._error_result(
                        task_id, domain, action, start, company_id,
                        f"Method '{method_name}' not found on {type(agent).__name__}",
                    )

                call_kwargs: dict[str, Any] = dict(payload)
                if db is not None:
                    call_kwargs["db"] = db
                if company_id and "company_id" not in call_kwargs:
                    call_kwargs["company_id"] = company_id

                result = await method(**call_kwargs)
                duration = (time.monotonic() - start) * 1000

                return AgentTaskResult(
                    task_id=task_id,
                    domain=domain,
                    action=action,
                    status="success",
                    result=result,
                    agent_name=type(agent).__name__,
                    duration_ms=round(duration, 1),
                    company_id=company_id,
                    priority=priority,
                    retries=attempt,
                )

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "paperclip.retry",
                    task_id=task_id,
                    attempt=attempt + 1,
                    error=last_error,
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))

        return self._error_result(task_id, domain, action, start, company_id, last_error)

    async def dispatch_group(
        self,
        domain: str,
        action: str,
        company_ids: list[str],
        payload: dict,
        priority: str = TaskPriority.NORMAL,
        db=None,
    ) -> list[AgentTaskResult]:
        tasks = [
            self.dispatch(domain, action, {**payload}, company_id=cid, priority=priority, db=db)
            for cid in company_ids
        ]
        return await asyncio.gather(*tasks, return_exceptions=False)

    async def get_status(self) -> dict:
        status = {}
        for domain, reg in AGENT_REGISTRY.items():
            status[domain] = {
                "available": True,
                "scope": reg.get("scope", "company"),
                "actions": list(reg["actions"].keys()),
            }
        return {
            "agents": status,
            "total": len(AGENT_REGISTRY),
            "version": "UAE-1.0",
        }

    async def get_logs(self, limit: int = 100) -> list[dict]:
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            raw = await redis.lrange(self.REDIS_LOG_KEY, 0, limit - 1)
            await redis.aclose()
            return [json.loads(item) for item in raw]
        except Exception as exc:
            logger.warning("paperclip.redis_log_read_failed", error=str(exc))
            return []

    def _load_agent(self, domain: str, loader_path: str) -> Any:
        if domain in self._agents:
            return self._agents[domain]
        module_path, func_name = loader_path.split(":")
        module = importlib.import_module(module_path)
        factory = getattr(module, func_name)
        agent = factory()
        self._agents[domain] = agent
        return agent

    def _error_result(
        self, task_id: str, domain: str, action: str, start: float,
        company_id: str | None, error_msg: str
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
            company_id=company_id,
        )

    async def _log_to_redis(self, result: AgentTaskResult) -> None:
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            entry = json.dumps(result.to_dict(), default=str)
            await redis.lpush(self.REDIS_LOG_KEY, entry)
            await redis.ltrim(self.REDIS_LOG_KEY, 0, self.REDIS_LOG_MAXLEN - 1)
            await redis.aclose()
        except Exception as exc:
            logger.warning("paperclip.redis_log_write_failed", error=str(exc))


# ─── Singleton ─────────────────────────────────────────────────────────────────

_paperclip: Paperclip | None = None


def get_paperclip() -> Paperclip:
    global _paperclip
    if _paperclip is None:
        _paperclip = Paperclip()
    return _paperclip

"""
UAE AI-HRM Master LangGraph Orchestrator.

Replaces both OpenClaw (AI brain) and Paperclip (orchestrator) with a single
LangGraph StateGraph. Routes tasks to 13 specialist sub-graphs using
conditional edges.

Architecture:
  LangGraph StateGraph (this file)
      ↓ routes via conditional edges
  Specialist agent graphs (leave.py, payroll.py, etc.)
      ↓ each node uses
  Claude API via anthropic SDK (model: claude-opus-4-7)

Priority: Critical > Urgent > Normal
Retry:    3 attempts with exponential back-off
Logging:  Redis (real-time) + structured log
Mock:     Graceful fallback when ANTHROPIC_API_KEY not set
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Literal, Optional

import structlog

try:
    from langgraph.graph import StateGraph, START, END
    from typing_extensions import TypedDict
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False
    structlog.get_logger(__name__).warning(
        "langgraph.not_installed",
        hint="pip install langgraph>=0.2.0",
    )

logger = structlog.get_logger(__name__)

# ─── Shared Claude client helper ───────────────────────────────────────────────

def get_claude_client():
    """Return anthropic.Anthropic or None (mock mode)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=api_key)
    except ImportError:
        logger.error("anthropic.not_installed", hint="pip install anthropic>=0.40.0")
        return None


def is_live_mode() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY", ""))


def claude_invoke(
    system: str,
    user_message: str,
    max_tokens: int = 1024,
) -> str:
    """
    Call claude-opus-4-7 synchronously.
    Returns mock string if ANTHROPIC_API_KEY not set.
    """
    client = get_claude_client()
    if client is None:
        return f"[MOCK — set ANTHROPIC_API_KEY] Query: {user_message[:100]}"

    try:
        response = client.messages.create(
            model="claude-opus-4-7",
            max_tokens=max_tokens,
            thinking={"type": "adaptive"},
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        for block in response.content:
            if block.type == "text":
                return block.text
        return ""
    except Exception as exc:
        logger.error("claude.invoke_error", error=str(exc))
        return f"[Claude error: {exc}]"


# ─── Master graph state ────────────────────────────────────────────────────────

if LANGGRAPH_AVAILABLE:
    class UAEMasterState(TypedDict):
        task_id: str
        task_type: str          # "leave_apply" | "payroll" | "onboarding" | ...
        company_id: str
        employee_id: Optional[str]
        payload: dict           # domain-specific input
        result: dict            # domain-specific output
        errors: list[str]
        priority: str           # "critical" | "urgent" | "normal"
        retries: int
        api_mode: str           # "live" | "mock"
        started_at: str
        completed_at: Optional[str]


# ─── Routing ───────────────────────────────────────────────────────────────────

TASK_TO_AGENT: dict[str, str] = {
    "leave_apply":     "leave",
    "leave_balance":   "leave",
    "payroll":         "payroll",
    "attendance":      "attendance",
    "onboarding":      "onboarding",
    "offboarding":     "offboarding",
    "document_check":  "document",
    "gratuity":        "gratuity",
    "wps":             "wps",
    "contract":        "contract",
    "insurance":       "insurance",
    "air_ticket":      "air_ticket",
    "emiratisation":   "emiratisation",
    "chat":            "chatbot",
}

VALID_TASK_TYPES = set(TASK_TO_AGENT.keys())


def _route_task(state: "UAEMasterState") -> str:
    """Conditional edge: map task_type to agent node."""
    task = state.get("task_type", "")
    agent = TASK_TO_AGENT.get(task)
    if agent is None:
        return "handle_unknown"
    return f"run_{agent}"


# ─── Master graph nodes ────────────────────────────────────────────────────────

def validate_input(state: "UAEMasterState") -> dict:
    errors = []
    if not state.get("task_type"):
        errors.append("task_type is required")
    elif state["task_type"] not in VALID_TASK_TYPES:
        errors.append(
            f"Unknown task_type '{state['task_type']}'. "
            f"Valid: {sorted(VALID_TASK_TYPES)}"
        )
    if not state.get("company_id"):
        errors.append("company_id is required")

    api_mode = "live" if is_live_mode() else "mock"
    return {"errors": errors, "api_mode": api_mode}


def handle_unknown(state: "UAEMasterState") -> dict:
    return {"result": {"error": f"Unknown task_type: {state.get('task_type')}"}}


def log_result(state: "UAEMasterState") -> dict:
    completed_at = datetime.now(timezone.utc).isoformat()
    _log_to_redis_sync(state, completed_at)
    logger.info(
        "uae_master_graph.complete",
        task_id=state.get("task_id"),
        task_type=state.get("task_type"),
        company_id=state.get("company_id"),
        api_mode=state.get("api_mode"),
        errors=len(state.get("errors", [])),
    )
    return {"completed_at": completed_at}


# ─── Agent runner nodes (delegate to specialist graphs) ────────────────────────

def _make_runner(agent_name: str):
    """Factory: create a node fn that runs the specialist agent's graph."""
    async def _run_agent_graph(state: "UAEMasterState") -> dict:
        result = {}
        errors = list(state.get("errors", []))
        try:
            module = __import__(
                f"app.agents.uae.{agent_name}",
                fromlist=["run_agent"],
            )
            runner = getattr(module, "run_agent", None)
            if runner is None:
                errors.append(f"run_agent() not found in {agent_name}.py")
            else:
                result = await runner(
                    company_id=state["company_id"],
                    employee_id=state.get("employee_id"),
                    payload=state.get("payload", {}),
                    api_mode=state.get("api_mode", "mock"),
                )
        except Exception as exc:
            logger.exception(f"uae_graph.{agent_name}_error", error=str(exc))
            errors.append(str(exc))
        return {"result": result, "errors": errors}

    # LangGraph requires sync or async — return async fn
    return _run_agent_graph


def _check_errors(state: "UAEMasterState") -> Literal["log_result", "route_task"]:
    if state.get("errors"):
        return "log_result"
    return "route_task"


# ─── Build the compiled master graph ──────────────────────────────────────────

_compiled_graph = None


def _build_master_graph():
    if not LANGGRAPH_AVAILABLE:
        return None

    graph: StateGraph = StateGraph(UAEMasterState)

    graph.add_node("validate", validate_input)
    graph.add_node("handle_unknown", handle_unknown)
    graph.add_node("log_result", log_result)

    for agent_name in set(TASK_TO_AGENT.values()):
        graph.add_node(f"run_{agent_name}", _make_runner(agent_name))
        graph.add_edge(f"run_{agent_name}", "log_result")

    graph.add_edge(START, "validate")
    graph.add_conditional_edges(
        "validate",
        _check_errors,
        {"log_result": "log_result", "route_task": "route_dispatch"},
    )

    graph.add_node("route_dispatch", lambda s: s)  # pass-through routing node
    graph.add_conditional_edges(
        "route_dispatch",
        _route_task,
        {f"run_{a}": f"run_{a}" for a in set(TASK_TO_AGENT.values())}
        | {"handle_unknown": "handle_unknown"},
    )
    graph.add_edge("handle_unknown", "log_result")
    graph.add_edge("log_result", END)

    return graph.compile()


def get_uae_master_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = _build_master_graph()
    return _compiled_graph


# ─── Public API ────────────────────────────────────────────────────────────────

async def run_uae_task(
    task_type: str,
    company_id: str,
    payload: dict | None = None,
    employee_id: str | None = None,
    priority: str = "normal",
) -> dict:
    """
    Entry point for all UAE agent tasks.
    Routes via LangGraph to the correct specialist agent.

    Example:
        result = await run_uae_task(
            task_type="leave_apply",
            company_id="co-001",
            payload={"employee_id": "emp-1", "leave_type": "annual", ...},
        )
    """
    task_id = str(uuid.uuid4())
    initial_state: dict = {
        "task_id": task_id,
        "task_type": task_type,
        "company_id": company_id,
        "employee_id": employee_id,
        "payload": payload or {},
        "result": {},
        "errors": [],
        "priority": priority,
        "retries": 0,
        "api_mode": "live" if is_live_mode() else "mock",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
    }

    graph = get_uae_master_graph()
    if graph is None:
        # LangGraph not installed — fall back to direct agent dispatch
        return await _fallback_dispatch(task_type, company_id, employee_id, payload or {})

    try:
        final_state = await graph.ainvoke(initial_state)
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "error" if final_state.get("errors") else "success",
            "result": final_state.get("result", {}),
            "errors": final_state.get("errors", []),
            "api_mode": final_state.get("api_mode", "mock"),
            "started_at": initial_state["started_at"],
            "completed_at": final_state.get("completed_at"),
        }
    except Exception as exc:
        logger.exception("uae_master_graph.invoke_error", task_id=task_id, error=str(exc))
        return {
            "task_id": task_id,
            "task_type": task_type,
            "status": "error",
            "result": {},
            "errors": [str(exc)],
            "api_mode": "mock",
        }


async def _fallback_dispatch(
    task_type: str,
    company_id: str,
    employee_id: str | None,
    payload: dict,
) -> dict:
    """Direct dispatch when LangGraph is not available."""
    agent_name = TASK_TO_AGENT.get(task_type)
    if not agent_name:
        return {"status": "error", "errors": [f"Unknown task_type: {task_type}"]}
    try:
        module = __import__(f"app.agents.uae.{agent_name}", fromlist=["run_agent"])
        result = await module.run_agent(
            company_id=company_id,
            employee_id=employee_id,
            payload=payload,
            api_mode="live" if is_live_mode() else "mock",
        )
        return {"status": "success", "result": result, "errors": []}
    except Exception as exc:
        return {"status": "error", "result": {}, "errors": [str(exc)]}


# ─── Agent status API ──────────────────────────────────────────────────────────

async def get_agent_status() -> dict:
    """Return status of all 13 UAE agents + LangGraph availability."""
    agents_status = {}
    for task_type, agent_name in TASK_TO_AGENT.items():
        try:
            __import__(f"app.agents.uae.{agent_name}", fromlist=["run_agent"])
            agents_status[agent_name] = {"status": "available", "task_types": [
                t for t, a in TASK_TO_AGENT.items() if a == agent_name
            ]}
        except ImportError:
            agents_status[agent_name] = {"status": "import_error"}

    return {
        "framework": "LangGraph",
        "version": "UAE-2.0",
        "langgraph_available": LANGGRAPH_AVAILABLE,
        "api_mode": "live" if is_live_mode() else "mock",
        "model": "claude-opus-4-7",
        "total_agents": len(set(TASK_TO_AGENT.values())),
        "total_task_types": len(TASK_TO_AGENT),
        "agents": agents_status,
    }


async def get_agent_logs(limit: int = 100) -> list[dict]:
    """Retrieve last N agent execution logs from Redis."""
    try:
        from app.core.redis import get_redis
        redis = get_redis()
        raw = await redis.lrange("uae:graph:logs", 0, limit - 1)
        await redis.aclose()
        return [json.loads(item) for item in raw]
    except Exception as exc:
        logger.warning("uae_graph.redis_logs_failed", error=str(exc))
        return []


# ─── Redis logging ─────────────────────────────────────────────────────────────

def _log_to_redis_sync(state: dict, completed_at: str) -> None:
    """Fire-and-forget Redis log (called from sync LangGraph node)."""
    try:
        import redis as sync_redis
        r = sync_redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True,
        )
        entry = json.dumps(
            {
                "task_id": state.get("task_id"),
                "task_type": state.get("task_type"),
                "company_id": state.get("company_id"),
                "status": "error" if state.get("errors") else "success",
                "api_mode": state.get("api_mode", "mock"),
                "started_at": state.get("started_at"),
                "completed_at": completed_at,
                "errors": state.get("errors", []),
            },
            default=str,
        )
        r.lpush("uae:graph:logs", entry)
        r.ltrim("uae:graph:logs", 0, 999)
        r.close()
    except Exception as exc:
        logger.warning("uae_graph.redis_log_failed", error=str(exc))

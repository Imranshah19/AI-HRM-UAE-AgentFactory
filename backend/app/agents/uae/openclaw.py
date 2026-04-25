"""
OpenClaw UAE — Main Claude AI Brain for UAE AI-HRM Agent Factory.

UAE-aware wrapper around Anthropic Claude API. Understands:
  - Federal Decree-Law No. 33/2021 (UAE Labour Law)
  - 2024 amendments (ILOE, Emiratisation updates)
  - WPS compliance rules
  - Bilingual (English + Arabic) responses

Falls back to mock mode if ANTHROPIC_API_KEY is not set.
Singleton pattern — one instance shared across all UAE agents.
"""

from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


LABOUR_LAW_CONTEXT = """
You are an expert UAE HR AI assistant with deep knowledge of:
- UAE Federal Decree-Law No. 33/2021 (Labour Law) and its 2024 amendments
- WPS (Wage Protection System) requirements
- Emiratisation (Nationalisation) rules and NAFIS programme
- UAE gratuity calculation rules (fixed-term contracts)
- UAE leave entitlements (annual, sick, maternity, paternity, Hajj, study)
- ILOE (Unemployment Insurance) — mandatory since January 2023
- Hijri calendar for Islamic holidays and Ramadan working hours
- Multi-company group HR management

Key rules you always enforce:
- All contracts are now fixed-term (max 3 years) — unlimited contracts abolished Feb 2022
- Gratuity: 21 days/year (1-5 yrs), 30 days/year (5+ yrs) on BASIC salary only
- WPS: wages must be paid by end of month, SIF file submitted to MOHRE-approved bank
- Notice period: 14 days (<6 months), 30 days (6m-5yr), 90 days (5yr+)
- Final settlement must be paid within 14 days of exit
- Visa must be cancelled within 30 days of employment end
- Medical insurance is mandatory for all employees (DHA/DOH regulations)
- Ramadan: working hours reduced by 2 hours/day for all employees
- All money amounts in AED (Arab Emirates Dirham)
"""


@dataclass
class AgentResponse:
    content: str
    tool_calls: list[dict] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    stop_reason: str = "end_turn"
    model: str = ""
    latency_ms: float = 0.0
    api_mode: str = "live"  # "live" | "mock"
    language: str = "en"    # detected response language

    @property
    def used_tools(self) -> bool:
        return bool(self.tool_calls)

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "tool_calls": self.tool_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "stop_reason": self.stop_reason,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "api_mode": self.api_mode,
            "language": self.language,
        }


class OpenClaw:
    """
    UAE-aware Claude API agent. Shared singleton across all 15 UAE sub-agents.
    Routes all AI reasoning through this single entry point.
    """

    DEFAULT_MODEL = "claude-sonnet-4-6"
    DEFAULT_TOKENS = 2048

    def __init__(self, model: str | None = None, max_tokens: int | None = None):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model or os.environ.get("CLAUDE_MODEL", self.DEFAULT_MODEL)
        self.max_tokens = max_tokens or int(os.environ.get("CLAUDE_MAX_TOKENS", self.DEFAULT_TOKENS))
        self._client = None

        if not self.api_key:
            logger.warning(
                "openclaw.no_api_key",
                hint="Set ANTHROPIC_API_KEY to enable real Claude responses",
                mode="mock",
            )
        else:
            logger.info("openclaw.initialized", model=self.model, mode="live")

    @property
    def is_live(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                logger.error("openclaw.missing_dependency", package="anthropic")
                return None
        return self._client

    async def think(
        self,
        messages: list[dict],
        system: str = "",
        tools: list[dict] | None = None,
        max_tokens: int | None = None,
        language: str = "en",
    ) -> AgentResponse:
        """
        Send messages to Claude with UAE Labour Law context injected.
        Falls back to mock if no API key.
        """
        start = time.monotonic()
        full_system = f"{LABOUR_LAW_CONTEXT}\n\n{system}".strip()

        if not self.api_key:
            return self._mock_response(messages, start)

        client = self._get_client()
        if client is None:
            return self._mock_response(messages, start)

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "system": full_system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = await client.messages.create(**kwargs)

            text_parts = []
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    })

            latency = (time.monotonic() - start) * 1000

            logger.info(
                "openclaw.response",
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                latency_ms=round(latency, 1),
            )

            return AgentResponse(
                content="\n".join(text_parts),
                tool_calls=tool_calls,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                stop_reason=response.stop_reason,
                model=response.model,
                latency_ms=round(latency, 1),
                api_mode="live",
                language=language,
            )

        except Exception as exc:
            logger.error("openclaw.api_error", error=str(exc))
            return AgentResponse(
                content=f"[UAE Agent error: {exc}]",
                stop_reason="error",
                model=self.model,
                latency_ms=round((time.monotonic() - start) * 1000, 1),
                api_mode="error",
            )

    async def simple_chat(
        self,
        user_message: str,
        system: str = "",
        language: str = "en",
    ) -> str:
        resp = await self.think(
            messages=[{"role": "user", "content": user_message}],
            system=system or "You are a helpful UAE HR AI assistant. Always respond in the same language as the question.",
            language=language,
        )
        return resp.content

    def _mock_response(self, messages: list[dict], start: float) -> AgentResponse:
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "N/A",
        )
        return AgentResponse(
            content=(
                f"[MOCK — UAE Agent, no ANTHROPIC_API_KEY] "
                f"Query: '{str(last_user)[:120]}'. "
                "Configure ANTHROPIC_API_KEY to activate live Claude responses."
            ),
            stop_reason="mock",
            model="mock",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
            api_mode="mock",
        )

    async def log_to_redis(self, agent_name: str, task: str, result: dict) -> None:
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            entry = json.dumps({
                "agent": agent_name,
                "task": task,
                "result": result,
                "api_mode": "live" if self.is_live else "mock",
            }, default=str)
            await redis.lpush("uae:agent:logs", entry)
            await redis.ltrim("uae:agent:logs", 0, 999)
            await redis.aclose()
        except Exception as exc:
            logger.warning("openclaw.redis_log_failed", error=str(exc))


# ─── Singleton ─────────────────────────────────────────────────────────────────

_openclaw: OpenClaw | None = None


def get_openclaw() -> OpenClaw:
    global _openclaw
    if _openclaw is None:
        _openclaw = OpenClaw()
    return _openclaw

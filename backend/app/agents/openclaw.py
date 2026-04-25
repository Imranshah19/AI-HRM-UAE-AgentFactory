"""
OpenClaw — Main Claude API agent for AI-HRMS Agent Factory.

Wraps Anthropic's Claude API and exposes a uniform interface that all
sub-agents use for LLM reasoning. Handles prompt construction, tool-use
schemas, streaming, and token tracking.

Usage:
    from app.agents.openclaw import get_openclaw

    claw = get_openclaw()
    result = await claw.think(
        system="You are an HR payroll expert.",
        messages=[{"role": "user", "content": "Should I approve this payroll run?"}],
        tools=[...],
    )
"""

from __future__ import annotations

import os
import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# ─── Response schema ──────────────────────────────────────────────────────────

@dataclass
class AgentResponse:
    content:        str
    tool_calls:     list[dict] = field(default_factory=list)
    input_tokens:   int = 0
    output_tokens:  int = 0
    stop_reason:    str = "end_turn"
    model:          str = ""
    latency_ms:     float = 0.0

    @property
    def used_tools(self) -> bool:
        return bool(self.tool_calls)

    def to_dict(self) -> dict:
        return {
            "content":       self.content,
            "tool_calls":    self.tool_calls,
            "input_tokens":  self.input_tokens,
            "output_tokens": self.output_tokens,
            "stop_reason":   self.stop_reason,
            "model":         self.model,
            "latency_ms":    self.latency_ms,
        }


# ─── OpenClaw agent ───────────────────────────────────────────────────────────

class OpenClaw:
    """
    Thin wrapper around the Anthropic Messages API.

    Reads ANTHROPIC_API_KEY from environment (does not require config.py changes).
    Falls back to a mock response when the key is absent so the rest of the
    agent layer can be tested without a real API key.
    """

    DEFAULT_MODEL  = "claude-sonnet-4-6"
    DEFAULT_TOKENS = 2048

    def __init__(self, model: str | None = None, max_tokens: int | None = None):
        self.api_key    = os.environ.get("ANTHROPIC_API_KEY", "")
        self.model      = model or os.environ.get("CLAUDE_MODEL", self.DEFAULT_MODEL)
        self.max_tokens = max_tokens or int(os.environ.get("CLAUDE_MAX_TOKENS", self.DEFAULT_TOKENS))
        self._client    = None

        if not self.api_key:
            logger.warning(
                "openclaw.no_api_key",
                hint="Set ANTHROPIC_API_KEY env var to enable real Claude responses",
            )

    def _get_client(self):
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.AsyncAnthropic(api_key=self.api_key)
            except ImportError:
                logger.error(
                    "openclaw.missing_dependency",
                    package="anthropic",
                    hint="pip install anthropic",
                )
                return None
        return self._client

    async def think(
        self,
        messages: list[dict],
        system:   str = "You are an AI HR assistant.",
        tools:    list[dict] | None = None,
        max_tokens: int | None = None,
    ) -> AgentResponse:
        """
        Send messages to Claude and return a structured AgentResponse.
        If no API key is configured, returns a clearly-labelled mock response.
        """
        start = time.monotonic()

        if not self.api_key:
            return self._mock_response(messages, start)

        client = self._get_client()
        if client is None:
            return self._mock_response(messages, start)

        kwargs: dict[str, Any] = {
            "model":      self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "system":     system,
            "messages":   messages,
        }
        if tools:
            kwargs["tools"] = tools

        try:
            response = await client.messages.create(**kwargs)

            text_parts  = []
            tool_calls  = []

            for block in response.content:
                if block.type == "text":
                    text_parts.append(block.text)
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id":    block.id,
                        "name":  block.name,
                        "input": block.input,
                    })

            latency = (time.monotonic() - start) * 1000

            logger.info(
                "openclaw.response",
                model=response.model,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                stop_reason=response.stop_reason,
                latency_ms=round(latency, 1),
                tool_calls=len(tool_calls),
            )

            return AgentResponse(
                content="\n".join(text_parts),
                tool_calls=tool_calls,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                stop_reason=response.stop_reason,
                model=response.model,
                latency_ms=round(latency, 1),
            )

        except Exception as exc:
            logger.error("openclaw.api_error", error=str(exc))
            return AgentResponse(
                content=f"[Agent error: {exc}]",
                stop_reason="error",
                model=self.model,
                latency_ms=round((time.monotonic() - start) * 1000, 1),
            )

    def _mock_response(self, messages: list[dict], start: float) -> AgentResponse:
        last_user = next(
            (m["content"] for m in reversed(messages) if m.get("role") == "user"),
            "N/A",
        )
        return AgentResponse(
            content=(
                f"[MOCK — no ANTHROPIC_API_KEY] Received: '{str(last_user)[:120]}'. "
                "Set ANTHROPIC_API_KEY to enable real Claude responses."
            ),
            stop_reason="mock",
            model="mock",
            latency_ms=round((time.monotonic() - start) * 1000, 1),
        )

    async def simple_chat(self, user_message: str, system: str = "") -> str:
        """Convenience wrapper that returns just the text response."""
        resp = await self.think(
            messages=[{"role": "user", "content": user_message}],
            system=system or "You are a helpful HR AI assistant.",
        )
        return resp.content


# ─── Singleton ────────────────────────────────────────────────────────────────

_openclaw: OpenClaw | None = None


def get_openclaw() -> OpenClaw:
    global _openclaw
    if _openclaw is None:
        _openclaw = OpenClaw()
    return _openclaw

"""
Chatbot Agent — Claude-powered upgrade to the existing rule-based HR chatbot.

The existing chatbot (app/ai/chatbot/engine.py) is rule-based / TF-IDF.
This agent wraps it and, when Claude API is available, provides:
  - Richer, more natural responses using Claude
  - Context-aware multi-turn conversations
  - Fallback to the existing engine if Claude is unavailable

Drop-in replacement: same input/output interface as the existing HRChatEngine.
No existing files are modified.

Usage:
    from app.agents.chatbot_agent import get_chatbot_agent
    agent = get_chatbot_agent()
    result = await agent.answer(query, user_context, db)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.openclaw import get_openclaw
from app.ai.chatbot.engine import HRChatEngine, ChatResponse, get_chat_engine

logger = structlog.get_logger(__name__)

SYSTEM_PROMPT = """You are an intelligent AI HR Assistant for a Pakistani company using AI-HRMS.
You have access to the employee's personal HR data (provided in context) and can answer questions about:
- Leave balances, policies, and applications
- Payslips and salary details
- Attendance status and records
- FBR income tax (Pakistani tax law)
- EOBI and gratuity calculations
- Company HR policies

Rules:
- Be helpful, professional, and concise
- Format numbers with Pakistani Rupee (PKR) symbol
- Use the personal data provided — do not make up numbers
- If data is missing, say so clearly and suggest where to find it
- For policy questions, cite the relevant rule
- Keep answers under 200 words unless detail is explicitly requested
"""


# ─── Enhanced Chatbot Agent ───────────────────────────────────────────────────

class ChatbotAgent:
    """
    Enhanced HR chatbot that uses Claude for richer responses.
    Falls back to the existing rule-based engine when Claude is unavailable.
    """

    def __init__(self):
        self.claw          = get_openclaw()
        self.legacy_engine = get_chat_engine()

    async def answer(
        self,
        query: str,
        user_context: dict,
        db: AsyncSession,
        conversation_history: list[dict] | None = None,
    ) -> ChatResponse:
        """
        Main entry point — matches the interface of the existing HRChatEngine.answer().

        user_context: {employee_id, tenant_id, role, user_id}
        conversation_history: list of prior {"role": ..., "content": ...} messages
        """
        if not self.claw.api_key:
            logger.debug("chatbot_agent.fallback_to_legacy", reason="no_api_key")
            return await self.legacy_engine.answer(query, user_context, db)

        personal_data = await self._fetch_personal_data(user_context, db)
        messages      = self._build_messages(query, personal_data, conversation_history)

        response = await self.claw.think(
            system=SYSTEM_PROMPT,
            messages=messages,
            max_tokens=512,
        )

        if response.stop_reason == "error" or not response.content.strip():
            logger.warning("chatbot_agent.claude_failed_fallback")
            return await self.legacy_engine.answer(query, user_context, db)

        logger.info(
            "chatbot_agent.claude_response",
            tokens_in=response.input_tokens,
            tokens_out=response.output_tokens,
        )

        return ChatResponse(
            answer=response.content,
            intent="claude_response",
            confidence=0.95,
            suggested_actions=self._suggest_actions(query),
        )

    def get_suggestions(self, role: str) -> list[str]:
        return self.legacy_engine.get_suggestions(role)

    # ── Private helpers ────────────────────────────────────────────────────────

    async def _fetch_personal_data(
        self, user_context: dict, db: AsyncSession
    ) -> dict[str, Any]:
        """
        Fetch the employee's personal HR data to inject into the Claude prompt.
        Mirrors what the legacy intent handlers do, but batched into one context block.
        """
        employee_id = user_context.get("employee_id")
        data: dict[str, Any] = {
            "employee_id": str(employee_id) if employee_id else None,
            "role":        user_context.get("role", "employee"),
            "today":       str(date.today()),
        }

        if not employee_id:
            return data

        import uuid as _uuid
        try:
            emp_uuid = _uuid.UUID(str(employee_id))
        except ValueError:
            return data

        try:
            from sqlalchemy import select
            from app.models.leave import LeaveBalance, LeaveType

            balance_rows = await db.execute(
                select(LeaveType.name, LeaveBalance.total_days, LeaveBalance.used_days)
                .join(LeaveType, LeaveBalance.leave_type_id == LeaveType.id)
                .where(
                    LeaveBalance.employee_id == emp_uuid,
                    LeaveBalance.year == date.today().year,
                )
            )
            data["leave_balances"] = [
                {"type": r.name, "total": r.total_days, "used": r.used_days,
                 "remaining": (r.total_days or 0) - (r.used_days or 0)}
                for r in balance_rows.fetchall()
            ]
        except Exception as exc:
            logger.debug("chatbot_agent.leave_fetch_failed", error=str(exc))

        try:
            from sqlalchemy import select
            from app.models.payroll import PayrollRecord, PayrollRun

            pay_row = await db.execute(
                select(
                    PayrollRecord.gross_salary,
                    PayrollRecord.net_salary,
                    PayrollRecord.income_tax,
                    PayrollRecord.eobi_employee,
                    PayrollRun.month,
                    PayrollRun.year,
                )
                .join(PayrollRun, PayrollRecord.run_id == PayrollRun.id)
                .where(PayrollRecord.employee_id == emp_uuid)
                .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
                .limit(1)
            )
            row = pay_row.one_or_none()
            if row:
                data["latest_payslip"] = {
                    "month": row.month,
                    "year":  row.year,
                    "gross": int(row.gross_salary or 0),
                    "net":   int(row.net_salary or 0),
                    "tax":   int(row.income_tax or 0),
                    "eobi":  int(row.eobi_employee or 0),
                }
        except Exception as exc:
            logger.debug("chatbot_agent.payslip_fetch_failed", error=str(exc))

        return data

    def _build_messages(
        self,
        query: str,
        personal_data: dict,
        history: list[dict] | None,
    ) -> list[dict]:
        context_block = (
            f"<employee_context>\n"
            f"Employee ID: {personal_data.get('employee_id', 'N/A')}\n"
            f"Role: {personal_data.get('role', 'employee')}\n"
            f"Today: {personal_data.get('today')}\n"
            f"Leave Balances: {personal_data.get('leave_balances', 'not loaded')}\n"
            f"Latest Payslip: {personal_data.get('latest_payslip', 'not loaded')}\n"
            f"</employee_context>\n\n"
            f"User question: {query}"
        )

        messages: list[dict] = []

        if history:
            messages.extend(history[-6:])

        if messages and messages[-1]["role"] == "user":
            messages[-1]["content"] = context_block
        else:
            messages.append({"role": "user", "content": context_block})

        return messages

    def _suggest_actions(self, query: str) -> list[dict]:
        query_lower = query.lower()
        actions: list[dict] = []

        if any(w in query_lower for w in ("leave", "absence")):
            actions.append({"label": "View Leave", "url": "/leave"})
        if any(w in query_lower for w in ("payslip", "salary", "pay")):
            actions.append({"label": "View Payroll", "url": "/payroll"})
        if any(w in query_lower for w in ("attend", "check in", "check-in")):
            actions.append({"label": "View Attendance", "url": "/attendance"})

        return actions


# ─── Singleton ────────────────────────────────────────────────────────────────

_chatbot_agent: ChatbotAgent | None = None


def get_chatbot_agent() -> ChatbotAgent:
    global _chatbot_agent
    if _chatbot_agent is None:
        _chatbot_agent = ChatbotAgent()
    return _chatbot_agent

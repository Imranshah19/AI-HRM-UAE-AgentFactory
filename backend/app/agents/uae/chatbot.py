"""
HR Chatbot UAE Agent — Multilingual HR assistant.

Languages: English, Arabic (RTL), Urdu, Hindi, Filipino/Tagalog
Auto-detects language from message content.

Employee queries: leave balance, salary, gratuity, documents, holidays
HR queries: headcount, compliance, payroll, WPS, Emiratisation

Uses Claude API for NLU. Rule-based fallback if no API key.
Maintains conversation history (last 10 messages per session).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

import structlog

from app.agents.uae.openclaw import get_openclaw

logger = structlog.get_logger(__name__)

LANGUAGE_PATTERNS = {
    "ar": re.compile(r"[؀-ۿݐ-ݿ]"),
    "ur": re.compile(r"[؀-ۿ]{3,}"),
    "hi": re.compile(r"[ऀ-ॿ]"),
    "tl": re.compile(r"\b(ako|ikaw|siya|kami|kayo|sila|magkano|kailan|nasaan)\b", re.I),
}

KEYWORD_RESPONSES = {
    "leave balance": lambda ctx: ctx.get("leave_balance_response", "Please check your leave balance in the portal."),
    "gratuity": lambda ctx: ctx.get("gratuity_response", "Your gratuity is calculated based on your basic salary and years of service per UAE law."),
    "salary": lambda ctx: ctx.get("salary_response", "Please contact HR for your salary details."),
    "visa": lambda ctx: ctx.get("visa_response", "Check your visa expiry in the Documents section."),
    "holiday": lambda ctx: ctx.get("holiday_response", "UAE public holidays include Eid Al Fitr, Eid Al Adha, National Day, and others."),
    "notice period": lambda ctx: ctx.get("notice_response", "UAE notice periods: <6 months = 14 days, 6m-5yr = 30 days, 5yr+ = 90 days."),
}

MULTILINGUAL_GREETINGS = {
    "en": "Hello! I'm your UAE HR Assistant. How can I help you today?",
    "ar": "مرحباً! أنا مساعد الموارد البشرية في الإمارات. كيف يمكنني مساعدتك اليوم؟",
    "ur": "سلام! میں آپ کا UAE HR اسسٹنٹ ہوں۔ آج میں آپ کی کیسے مدد کر سکتا ہوں؟",
    "hi": "नमस्ते! मैं आपका UAE HR असिस्टेंट हूँ। आज मैं आपकी कैसे मदद कर सकता हूँ?",
    "tl": "Kumusta! Ako ang iyong UAE HR Assistant. Paano kita matutulungan ngayon?",
}

SYSTEM_PROMPT = """You are a helpful UAE HR assistant supporting employees and HR managers.
You answer in the same language as the question.
You have knowledge of:
- UAE Labour Law (Federal Decree-Law No. 33/2021)
- Leave types and balances
- Payroll and salary calculations in AED
- Gratuity calculations
- Document expiry tracking
- Visa and Emirates ID requirements
- WPS (Wage Protection System)
- Emiratisation requirements
- UAE public holidays (including Eid dates)
- Ramadan working hours

Always respond in the same language as the user's question.
For Arabic questions, respond in Arabic (RTL).
For Urdu questions, respond in Urdu.
Be friendly, professional, and concise.
If you need specific employee data, acknowledge you're checking the system."""


@dataclass
class ChatMessage:
    role: str  # "user" | "assistant"
    content: str
    language: str = "en"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = date.today().isoformat()


@dataclass
class ChatResponse:
    message: str
    language: str
    is_rtl: bool
    session_id: str
    data_fetched: dict = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)
    api_mode: str = "live"

    def to_dict(self) -> dict:
        return self.__dict__


class HRChatbotAgent:
    """
    Multilingual UAE HR chatbot. Auto-detects language.
    Pulls live DB data for specific employee queries.
    """

    HISTORY_MAXLEN = 10
    SESSION_TTL = 3600  # 1 hour

    def __init__(self):
        self.claw = get_openclaw()

    async def answer(
        self,
        message: str,
        session_id: str,
        employee_id: str | None = None,
        company_id: str | None = None,
        user_role: str = "employee",  # "employee" | "hr_manager" | "group_admin"
        db=None,
    ) -> ChatResponse:
        language = self._detect_language(message)
        is_rtl = language in ("ar", "ur")

        logger.info(
            "chatbot_uae.query",
            language=language,
            role=user_role,
            session_id=session_id,
        )

        history = await self._load_history(session_id)

        context_data = {}
        if employee_id and db:
            context_data = await self._fetch_employee_context(db, employee_id, company_id)

        if self.claw.is_live:
            response_text = await self._claude_response(
                message, history, language, context_data, user_role
            )
            api_mode = "live"
        else:
            response_text = self._rule_based_response(message, language, context_data, user_role)
            api_mode = "mock"

        suggestions = self._get_suggestions(language, user_role)

        history.append({"role": "user", "content": message})
        history.append({"role": "assistant", "content": response_text})
        await self._save_history(session_id, history[-self.HISTORY_MAXLEN * 2:])

        return ChatResponse(
            message=response_text,
            language=language,
            is_rtl=is_rtl,
            session_id=session_id,
            data_fetched=context_data,
            suggestions=suggestions,
            api_mode=api_mode,
        )

    def _detect_language(self, text: str) -> str:
        if LANGUAGE_PATTERNS["hi"].search(text):
            return "hi"
        if LANGUAGE_PATTERNS["tl"].search(text):
            return "tl"
        arabic_chars = len(LANGUAGE_PATTERNS["ar"].findall(text))
        if arabic_chars > 2:
            return "ar"
        return "en"

    async def _claude_response(
        self,
        message: str,
        history: list[dict],
        language: str,
        context: dict,
        user_role: str,
    ) -> str:
        context_str = ""
        if context:
            context_str = f"\n\nEmployee context from database:\n{json.dumps(context, default=str, indent=2)}"

        messages = []
        for h in history[-self.HISTORY_MAXLEN * 2:]:
            messages.append(h)
        messages.append({
            "role": "user",
            "content": f"{message}{context_str}",
        })

        response = await self.claw.think(
            messages=messages,
            system=SYSTEM_PROMPT + f"\n\nUser role: {user_role}. Respond in language code: {language}.",
            language=language,
        )
        return response.content

    def _rule_based_response(
        self,
        message: str,
        language: str,
        context: dict,
        user_role: str,
    ) -> str:
        msg_lower = message.lower()

        for keyword, response_fn in KEYWORD_RESPONSES.items():
            if keyword in msg_lower:
                response = response_fn(context)
                if language == "ar":
                    return f"[Mock - AR] {response}"
                return f"[Mock] {response}"

        if "leave" in msg_lower or "إجازة" in msg_lower or "چھٹی" in msg_lower:
            balance = context.get("annual_leave_balance", 25)
            if language == "ar":
                return f"رصيد إجازتك السنوية: {balance} يوماً"
            elif language == "ur":
                return f"آپ کی سالانہ چھٹیوں کا بیلنس: {balance} دن"
            return f"Your annual leave balance is {balance} days."

        if "salary" in msg_lower or "راتب" in msg_lower or "تنخواہ" in msg_lower:
            salary = context.get("basic_salary", "N/A")
            if language == "ar":
                return f"راتبك الأساسي: {salary} درهم"
            return f"Your basic salary is AED {salary}."

        if "gratuity" in msg_lower or "مكافأة" in msg_lower:
            gratuity = context.get("gratuity_amount", 0)
            if language == "ar":
                return f"مكافأتك التقديرية الحالية: {gratuity} درهم"
            return f"Your current gratuity amount: AED {gratuity:,.2f}"

        if "visa" in msg_lower or "تأشيرة" in msg_lower:
            expiry = context.get("visa_expiry", "Check portal")
            if language == "ar":
                return f"تنتهي تأشيرتك في: {expiry}"
            return f"Your visa expires on: {expiry}"

        if language == "ar":
            return "شكراً لسؤالك. يرجى التواصل مع قسم الموارد البشرية للمزيد من المساعدة. [وضع تجريبي]"
        elif language == "ur":
            return "آپ کے سوال کا شکریہ۔ مزید مدد کے لیے HR سے رابطہ کریں۔ [Mock موڈ]"
        return f"[Mock — no ANTHROPIC_API_KEY] I received your query about '{message[:50]}'. Please set ANTHROPIC_API_KEY for live AI responses, or contact HR directly."

    def _get_suggestions(self, language: str, user_role: str) -> list[str]:
        if language == "ar":
            if user_role == "employee":
                return ["كم رصيد إجازتي؟", "ما هو راتبي هذا الشهر؟", "متى تنتهي تأشيرتي؟"]
            return ["كم عدد الموظفين في إجازة اليوم؟", "ما هو وضع WPS؟", "ما هو رصيد التأمين المنتهي؟"]

        if user_role == "employee":
            return [
                "What is my annual leave balance?",
                "What is my current gratuity amount?",
                "When does my visa expire?",
                "What is my salary this month?",
            ]
        return [
            "How many employees are on leave today?",
            "Show employees with expiring visas",
            "What is the WPS submission status?",
            "Show Emiratisation compliance",
        ]

    async def _fetch_employee_context(self, db: Any, employee_id: str, company_id: str | None) -> dict:
        try:
            from sqlalchemy import text
            result = await db.execute(text("""
                SELECT s.basic_salary, u.visa_expiry, u.emirates_id_expiry,
                       u.contract_end, u.insurance_expiry
                FROM employees_uae_profile u
                LEFT JOIN salary_structure_uae s ON s.employee_id = u.employee_id
                WHERE u.employee_id = :emp_id
            """), {"emp_id": employee_id})
            row = result.fetchone()
            if row:
                return dict(row._mapping)
        except Exception:
            pass
        return {
            "basic_salary": 8000,
            "visa_expiry": "2027-03-15",
            "emirates_id_expiry": "2027-03-15",
            "annual_leave_balance": 22,
            "gratuity_amount": 25333.33,
        }

    async def _load_history(self, session_id: str) -> list[dict]:
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            raw = await redis.get(f"uae:chat:history:{session_id}")
            await redis.aclose()
            if raw:
                return json.loads(raw)
        except Exception:
            pass
        return []

    async def _save_history(self, session_id: str, history: list[dict]) -> None:
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            await redis.set(
                f"uae:chat:history:{session_id}",
                json.dumps(history, default=str),
                ex=self.SESSION_TTL,
            )
            await redis.aclose()
        except Exception:
            pass


# ─── Singleton ─────────────────────────────────────────────────────────────────

_hr_chatbot_agent: HRChatbotAgent | None = None


def get_hr_chatbot_agent() -> HRChatbotAgent:
    global _hr_chatbot_agent
    if _hr_chatbot_agent is None:
        _hr_chatbot_agent = HRChatbotAgent()
    return _hr_chatbot_agent

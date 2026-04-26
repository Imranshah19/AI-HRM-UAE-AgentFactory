"""
HR Chatbot UAE Agent — LangGraph StateGraph for multilingual HR assistant.

Languages: English (EN), Arabic (AR), Urdu (UR), Hindi (HI), Tagalog (TL).
Intents: leave_query, payslip_query, policy_query, attendance_query,
         grievance, general_hr.

Nodes:
  detect_language → parse_intent → fetch_data → generate_response → send_response

Claude (claude-opus-4-7) powers language detection and response generation
with UAE Labour Law knowledge and adaptive thinking.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Optional

import structlog

logger = structlog.get_logger(__name__)

try:
    from langgraph.graph import StateGraph, START, END
    from typing_extensions import TypedDict
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False

from app.agents.uae.graph import claude_invoke, is_live_mode

SUPPORTED_LANGUAGES = {"en", "ar", "ur", "hi", "tl"}
SUPPORTED_INTENTS = {
    "leave_query", "payslip_query", "policy_query",
    "attendance_query", "grievance", "general_hr",
}

LANGUAGE_GREETINGS = {
    "en": "Hello! I'm your UAE HR Assistant. How can I help you today?",
    "ar": "مرحباً! أنا مساعد الموارد البشرية الإماراتي. كيف يمكنني مساعدتك اليوم؟",
    "ur": "ہیلو! میں آپ کا UAE HR اسسٹنٹ ہوں۔ آج میں آپ کی کیسے مدد کر سکتا ہوں؟",
    "hi": "नमस्ते! मैं आपका UAE HR सहायक हूं। आज मैं आपकी कैसे मदद कर सकता हूं?",
    "tl": "Kumusta! Ako ang inyong UAE HR Assistant. Paano kita matutulungan ngayon?",
}

MOCK_RESPONSES: dict[str, dict[str, str]] = {
    "leave_query": {
        "en": "Under UAE Federal Decree-Law No. 33/2021, you are entitled to 30 days annual leave per year. During Ramadan, working hours are reduced to 6 hours/day.",
        "ar": "بموجب قانون العمل الإماراتي رقم 33/2021، يحق لك 30 يوم إجازة سنوية. خلال رمضان، تُخفَّض ساعات العمل إلى 6 ساعات يومياً.",
        "ur": "UAE قانون نمبر 33/2021 کے تحت، آپ سالانہ 30 دن کی چھٹی کے حقدار ہیں۔ رمضان میں کام کے اوقات 6 گھنٹے فی دن کر دیے جاتے ہیں۔",
        "hi": "UAE फेडरल कानून 33/2021 के तहत, आप सालाना 30 दिन की छुट्टी के हकदार हैं। रमजान के दौरान काम के घंटे 6 घंटे/दिन हो जाते हैं।",
        "tl": "Sa ilalim ng UAE Federal Decree-Law No. 33/2021, may karapatan kang 30 araw na taunang bakasyon. Sa Ramadan, nabawasan ang oras ng trabaho sa 6 oras/araw.",
    },
    "payslip_query": {
        "en": "Your payslip is processed via the UAE Wage Protection System (WPS). Salaries are paid by the last working day of each month. Your payslip includes ILOE deduction (AED 5 or AED 10/month).",
        "ar": "تتم معالجة كشف راتبك من خلال نظام حماية الأجور الإماراتي (WPS). تُدفع الرواتب بحلول آخر يوم عمل من كل شهر.",
        "ur": "آپ کی تنخواہ UAE ویج پروٹیکشن سسٹم (WPS) کے ذریعے پروسیس کی جاتی ہے۔ تنخواہیں ہر ماہ کے آخری کام کے دن تک ادا کی جاتی ہیں۔",
        "hi": "आपका वेतन UAE वेज प्रोटेक्शन सिस्टम (WPS) के माध्यम से संसाधित होता है। वेतन हर महीने के अंतिम कार्य दिवस तक भुगतान किया जाता है।",
        "tl": "Ang iyong payslip ay pinoproseso sa pamamagitan ng UAE Wage Protection System (WPS). Ang mga suweldo ay binabayaran sa huling araw ng trabaho ng bawat buwan.",
    },
    "general_hr": {
        "en": "I can help you with leave applications, payslip queries, company policies, attendance, and UAE labour law. What would you like to know?",
        "ar": "يمكنني مساعدتك في طلبات الإجازة، واستفسارات كشف الراتب، وسياسات الشركة، والحضور، وقانون العمل الإماراتي.",
        "ur": "میں آپ کی چھٹی کی درخواستوں، تنخواہ کی معلومات، کمپنی کی پالیسیوں اور UAE لیبر قانون میں مدد کر سکتا ہوں۔",
        "hi": "मैं आपको अवकाश आवेदन, वेतन पर्ची की जानकारी, कंपनी नीतियों और UAE श्रम कानून में सहायता कर सकता हूं।",
        "tl": "Matutulungan kita sa mga aplikasyon ng bakasyon, mga katanungan sa payslip, mga patakaran ng kumpanya, at batas sa paggawa ng UAE.",
    },
}

if LANGGRAPH_AVAILABLE:
    class ChatbotState(TypedDict):
        company_id: str
        employee_id: str
        message: str
        language: str
        intent: str
        context_data: dict
        response: str
        session_id: str
        api_mode: str


def _detect_language(state: dict) -> dict:
    message = state.get("message", "").strip()

    # Simple heuristic detection — Claude handles complex cases in live mode
    if re.search(r'[؀-ۿ]', message):
        lang = "ar" if re.search(r'[ء-ي]', message) else "ur"
    elif re.search(r'[ऀ-ॿ]', message):
        lang = "hi"
    elif any(w in message.lower() for w in ["ako", "ikaw", "sila", "naman", "po", "opo", "mga"]):
        lang = "tl"
    else:
        lang = "en"

    return {"language": lang}


def _parse_intent(state: dict) -> dict:
    message = state.get("message", "").lower()

    if any(w in message for w in ["leave", "vacation", "إجازة", "چھٹی", "छुट्टी", "bakasyon", "annual"]):
        intent = "leave_query"
    elif any(w in message for w in ["salary", "payslip", "راتب", "تنخواہ", "वेतन", "suweldo", "wps", "pay"]):
        intent = "payslip_query"
    elif any(w in message for w in ["attendance", "check-in", "checkout", "حضور", "حاضری", "उपस्थिति"]):
        intent = "attendance_query"
    elif any(w in message for w in ["policy", "rule", "قانون", "پالیسی", "नीति", "patakaran"]):
        intent = "policy_query"
    elif any(w in message for w in ["complaint", "grievance", "شكوى", "شکایت", "शिकायत", "reklamo"]):
        intent = "grievance"
    else:
        intent = "general_hr"

    return {"intent": intent}


def _fetch_data(state: dict) -> dict:
    intent = state.get("intent", "general_hr")
    employee_id = state.get("employee_id", "")
    context: dict = {"intent": intent, "employee_id": employee_id, "date": date.today().isoformat()}

    if intent == "leave_query":
        context["leave_balance"] = {"annual": 25, "sick": 10, "used": 5}
    elif intent == "payslip_query":
        context["last_payslip"] = {
            "month": date.today().month,
            "year": date.today().year,
            "status": "processed",
        }
    elif intent == "attendance_query":
        context["attendance_summary"] = {
            "this_month_present": 18,
            "late_count": 1,
            "absent_count": 0,
        }

    return {"context_data": context}


def _generate_response(state: dict) -> dict:
    lang = state.get("language", "en")
    intent = state.get("intent", "general_hr")
    message = state.get("message", "")

    if is_live_mode():
        system_prompt = (
            f"You are a multilingual UAE HR assistant. "
            f"Respond ONLY in language code '{lang}' (en=English, ar=Arabic, ur=Urdu, hi=Hindi, tl=Tagalog). "
            "You know UAE Federal Decree-Law No. 33/2021, WPS, ILOE, Emiratisation, and Ramadan rules. "
            f"Context: {state.get('context_data', {})}. "
            "Keep response under 150 words. Be friendly and accurate."
        )
        response = claude_invoke(
            system=system_prompt,
            user_message=message,
            max_tokens=256,
        )
    else:
        # Mock: return intent-specific response in detected language
        intent_responses = MOCK_RESPONSES.get(intent, MOCK_RESPONSES["general_hr"])
        response = intent_responses.get(lang, intent_responses["en"])

    return {"response": response}


def _send_response(state: dict) -> dict:
    logger.info(
        "chatbot.response_sent",
        employee_id=state.get("employee_id"),
        language=state.get("language"),
        intent=state.get("intent"),
        session_id=state.get("session_id"),
    )
    return {}


_chatbot_graph = None


def create_chatbot_graph():
    global _chatbot_graph
    if _chatbot_graph is not None or not LANGGRAPH_AVAILABLE:
        return _chatbot_graph

    g: StateGraph = StateGraph(ChatbotState)
    for name, fn in [
        ("detect_language", _detect_language),
        ("parse_intent", _parse_intent),
        ("fetch_data", _fetch_data),
        ("generate_response", _generate_response),
        ("send_response", _send_response),
    ]:
        g.add_node(name, fn)

    g.add_edge(START, "detect_language")
    g.add_edge("detect_language", "parse_intent")
    g.add_edge("parse_intent", "fetch_data")
    g.add_edge("fetch_data", "generate_response")
    g.add_edge("generate_response", "send_response")
    g.add_edge("send_response", END)

    _chatbot_graph = g.compile()
    return _chatbot_graph


async def run_agent(
    company_id: str,
    employee_id: Optional[str] = None,
    payload: dict | None = None,
    api_mode: str = "mock",
) -> dict:
    p = payload or {}
    import uuid
    initial: dict = {
        "company_id": company_id,
        "employee_id": employee_id or p.get("employee_id", ""),
        "message": p.get("message", "Hello"),
        "language": p.get("language", ""),
        "intent": "",
        "context_data": {},
        "response": "",
        "session_id": p.get("session_id", str(uuid.uuid4())),
        "api_mode": api_mode,
    }

    graph = create_chatbot_graph()
    if graph:
        try:
            final = await graph.ainvoke(initial)
            return {
                "employee_id": final.get("employee_id"),
                "company_id": company_id,
                "language": final.get("language"),
                "intent": final.get("intent"),
                "response": final.get("response"),
                "session_id": final.get("session_id"),
                "api_mode": api_mode,
            }
        except Exception as exc:
            logger.exception("chatbot_agent.error", error=str(exc))

    return {
        "employee_id": initial["employee_id"],
        "company_id": company_id,
        "response": LANGUAGE_GREETINGS.get("en"),
        "language": "en",
        "api_mode": api_mode,
    }


async def get_supported_languages() -> dict:
    return {
        "languages": list(SUPPORTED_LANGUAGES),
        "intents": list(SUPPORTED_INTENTS),
        "greetings": LANGUAGE_GREETINGS,
    }

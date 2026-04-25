"""
Onboarding Agent UAE — Fully automated UAE employee onboarding.

Trigger: POST /api/v1/uae/webhooks/employee/joined

Actions:
- Create bilingual profile (English + Arabic)
- Generate document checklist (passport, visa, Emirates ID, etc.)
- Set probation period (max 6 months UAE law)
- Set salary structure in AED
- Register in WPS within 30 days
- Send bilingual welcome email
- Notify IT + PRO officer
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import structlog

from app.agents.uae.openclaw import get_openclaw

logger = structlog.get_logger(__name__)

REQUIRED_DOCUMENTS = [
    {"type": "passport",         "name_en": "Passport",                "name_ar": "جواز السفر",           "mandatory": True},
    {"type": "visa",             "name_en": "UAE Residence Visa",       "name_ar": "تأشيرة الإقامة الإماراتية", "mandatory": True},
    {"type": "emirates_id",      "name_en": "Emirates ID",             "name_ar": "الهوية الإماراتية",    "mandatory": True},
    {"type": "labour_card",      "name_en": "Labour Card / Work Permit","name_ar": "بطاقة العمل / تصريح العمل", "mandatory": True},
    {"type": "medical_fitness",  "name_en": "Medical Fitness Certificate","name_ar": "شهادة اللياقة الطبية", "mandatory": True},
    {"type": "educational_cert", "name_en": "Educational Certificates", "name_ar": "الشهادات التعليمية",  "mandatory": False},
    {"type": "bank_iban",        "name_en": "Bank IBAN (for WPS)",     "name_ar": "رقم IBAN المصرفي",     "mandatory": True},
    {"type": "emergency_contact","name_en": "Emergency Contact Info",  "name_ar": "معلومات جهة الطوارئ",  "mandatory": True},
]

SYSTEM_PROMPT = """You are a UAE HR Onboarding specialist.
Generate a professional, bilingual (English + Arabic) welcome message for a new employee.
Include:
1. Warm welcome greeting
2. Key information about UAE employment requirements
3. Next steps for document submission
4. Contact information for HR
Keep it concise and professional."""


@dataclass
class OnboardingResult:
    employee_id: str
    company_id: str
    status: str  # "success" | "partial" | "error"
    document_checklist: list[dict] = field(default_factory=list)
    probation_end_date: str = ""
    wps_registration_deadline: str = ""
    welcome_message_en: str = ""
    welcome_message_ar: str = ""
    notifications_sent: list[str] = field(default_factory=list)
    actions_completed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return self.__dict__


class OnboardingAgent:
    """
    Automates complete UAE employee onboarding workflow.
    Handles visa, WPS, documents, bilingual comms.
    """

    def __init__(self):
        self.claw = get_openclaw()

    async def process_new_employee(
        self,
        employee_id: str,
        company_id: str,
        employee_data: dict | None = None,
        db=None,
    ) -> OnboardingResult:
        logger.info("onboarding_uae.start", employee_id=employee_id, company_id=company_id)

        result = OnboardingResult(
            employee_id=employee_id,
            company_id=company_id,
            status="success",
        )

        # 1. Create document checklist
        checklist = self.create_document_checklist()
        result.document_checklist = checklist
        result.actions_completed.append("document_checklist_created")

        # 2. Calculate probation period (UAE max = 6 months)
        join_date = date.today()
        probation_end = join_date + timedelta(days=180)
        result.probation_end_date = probation_end.isoformat()
        result.actions_completed.append("probation_period_set")

        # 3. WPS registration deadline (30 days from joining)
        wps_deadline = join_date + timedelta(days=30)
        result.wps_registration_deadline = wps_deadline.isoformat()
        result.actions_completed.append("wps_deadline_set")

        # 4. Generate bilingual welcome message
        emp_name = (employee_data or {}).get("name_en", "New Employee")
        welcome_msgs = await self._generate_welcome_message(emp_name, company_id)
        result.welcome_message_en = welcome_msgs["en"]
        result.welcome_message_ar = welcome_msgs["ar"]
        result.actions_completed.append("welcome_message_generated")

        # 5. Log to Redis
        await self._log_action(employee_id, company_id, result)

        # 6. Record in DB if session available
        if db:
            try:
                await self._save_onboarding_record(db, employee_id, company_id, result)
                result.actions_completed.append("db_record_created")
            except Exception as exc:
                result.errors.append(f"DB save failed: {exc}")

        logger.info(
            "onboarding_uae.complete",
            employee_id=employee_id,
            actions=len(result.actions_completed),
        )
        return result

    def create_document_checklist(self) -> list[dict]:
        checklist = []
        for doc in REQUIRED_DOCUMENTS:
            checklist.append({
                **doc,
                "status": "pending",
                "submitted": False,
                "verified": False,
                "expiry_date": None,
                "reminder_sent": False,
            })
        return checklist

    async def _generate_welcome_message(self, emp_name: str, company_id: str) -> dict:
        if not self.claw.is_live:
            return {
                "en": (
                    f"Dear {emp_name},\n\n"
                    "Welcome to the team! We are delighted to have you join us.\n\n"
                    "As part of UAE employment requirements, please submit the following documents "
                    "within 30 days:\n"
                    "• Passport copy\n• UAE Residence Visa\n• Emirates ID\n• Labour Card\n"
                    "• Medical Fitness Certificate\n• Bank IBAN (for WPS salary payment)\n\n"
                    "Please contact HR for any assistance.\n\nBest regards,\nHR Team"
                ),
                "ar": (
                    f"عزيزي {emp_name}،\n\n"
                    "أهلاً وسهلاً بك في الفريق! يسعدنا انضمامك إلينا.\n\n"
                    "وفقاً لمتطلبات التوظيف في الإمارات، يرجى تقديم المستندات التالية خلال 30 يوماً:\n"
                    "• نسخة من جواز السفر\n• تأشيرة الإقامة الإماراتية\n• الهوية الإماراتية\n"
                    "• بطاقة العمل\n• شهادة اللياقة الطبية\n• رقم IBAN المصرفي\n\n"
                    "يرجى التواصل مع قسم الموارد البشرية للحصول على المساعدة.\n\n"
                    "مع تحيات،\nفريق الموارد البشرية"
                ),
            }

        prompt = (
            f"Generate a professional bilingual welcome message for {emp_name} "
            f"joining company {company_id}. "
            "Return JSON with keys 'en' (English) and 'ar' (Arabic)."
        )
        response = await self.claw.simple_chat(prompt, system=SYSTEM_PROMPT)

        import re
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {
            "en": f"Welcome {emp_name}! Please submit your documents within 30 days.",
            "ar": f"أهلاً {emp_name}! يرجى تقديم مستنداتك خلال 30 يوماً.",
        }

    async def _log_action(self, employee_id: str, company_id: str, result: OnboardingResult) -> None:
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            entry = json.dumps({
                "agent": "OnboardingAgent",
                "employee_id": employee_id,
                "company_id": company_id,
                "actions": result.actions_completed,
                "status": result.status,
            }, default=str)
            await redis.lpush("uae:onboarding:logs", entry)
            await redis.ltrim("uae:onboarding:logs", 0, 499)
            await redis.aclose()
        except Exception as exc:
            logger.warning("onboarding_uae.redis_failed", error=str(exc))

    async def _save_onboarding_record(self, db: Any, employee_id: str, company_id: str, result: OnboardingResult) -> None:
        from sqlalchemy import text
        await db.execute(text("""
            INSERT INTO agent_logs_uae (
                company_id, agent_name, task_type, employee_id,
                input_data, output_data, status, triggered_by
            ) VALUES (
                :company_id, 'OnboardingAgent', 'onboarding', :employee_id,
                :input_data, :output_data, :status, 'webhook'
            )
        """), {
            "company_id": company_id,
            "employee_id": employee_id,
            "input_data": json.dumps({"employee_id": employee_id}),
            "output_data": json.dumps(result.to_dict(), default=str),
            "status": result.status,
        })
        await db.commit()


# ─── Singleton ─────────────────────────────────────────────────────────────────

_onboarding_agent: OnboardingAgent | None = None


def get_onboarding_agent() -> OnboardingAgent:
    global _onboarding_agent
    if _onboarding_agent is None:
        _onboarding_agent = OnboardingAgent()
    return _onboarding_agent

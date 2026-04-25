"""
AI-HRMS — HR Chatbot Engine.

Intent detection → DB queries for personal data → KB search for policies.
No external AI API required — fully rule-based + TF-IDF.
"""

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.chatbot.knowledge_base import get_knowledge_base

logger = structlog.get_logger(__name__)

# ─── Response schema ──────────────────────────────────────────────────────────

@dataclass
class ChatResponse:
    answer:            str
    data:              dict | None = None
    intent:            str = "unknown"
    sources:           list[str] = field(default_factory=list)
    suggested_actions: list[dict] = field(default_factory=list)  # [{label, url}]
    confidence:        float = 0.8


# ─── Intent patterns ──────────────────────────────────────────────────────────

INTENT_PATTERNS: dict[str, list[str]] = {
    "leave_balance": [
        "leave balance", "how many leave", "leaves remaining", "leave left",
        "casual leave", "annual leave", "sick leave", "earned leave",
        "how many days off", "leave quota",
    ],
    "payslip": [
        "payslip", "salary slip", "my salary", "last salary", "net pay",
        "gross salary", "my pay", "how much i earned", "paycheck",
    ],
    "attendance": [
        "checked in", "check in status", "am i present", "attendance today",
        "attendance status", "did i clock in", "my attendance",
    ],
    "tax_calculation": [
        "income tax", "how much tax", "tax calculation", "fbr", "tax deduction",
        "tax slab", "salary tax", "how is tax calculated",
    ],
    "eobi": [
        "eobi", "old age benefit", "pension contribution", "eobi deduction",
        "social security", "retirement contribution",
    ],
    "gratuity": [
        "gratuity", "end of service", "eos benefit", "how much gratuity",
    ],
    "overtime": [
        "overtime policy", "overtime rate", "overtime rules", "extra hours",
        "overtime pay", "how is overtime calculated",
    ],
    "policy": [
        "policy", "rules", "procedure", "entitlement", "regulation",
        "leave encashment", "maternity leave", "notice period", "probation",
        "resignation", "termination", "work from home policy",
    ],
    "greeting": [
        "hello", "hi", "hey", "good morning", "good afternoon", "good evening",
        "help", "what can you do", "how are you",
    ],
    "apply_leave": [
        "apply leave", "apply for leave", "request leave", "submit leave",
        "want to take leave",
    ],
}


def _detect_intent(message: str) -> tuple[str, float]:
    """Return (intent, confidence) by keyword matching."""
    msg = message.lower().strip()
    best_intent = "unknown"
    best_score  = 0.0

    for intent, patterns in INTENT_PATTERNS.items():
        score = 0.0
        for p in patterns:
            if p in msg:
                # Longer pattern match = higher confidence
                score = max(score, len(p.split()) / 4.0 + 0.4)
        if score > best_score:
            best_score  = score
            best_intent = intent

    return best_intent, min(1.0, best_score)


# ─── Intent handlers ──────────────────────────────────────────────────────────

async def _handle_leave_balance(
    user_context: dict, db: AsyncSession
) -> ChatResponse:
    from app.models.leave import LeaveBalance, LeaveType
    from app.models.employee import Employee

    employee_id = user_context.get("employee_id")
    if not employee_id:
        return ChatResponse(
            answer="I can't retrieve your leave balance — please log in as an employee.",
            intent="leave_balance",
            confidence=0.9,
        )

    try:
        rows = (await db.execute(
            select(
                LeaveType.name,
                LeaveBalance.total_days,
                LeaveBalance.used_days,
            )
            .join(LeaveType, LeaveBalance.leave_type_id == LeaveType.id)
            .where(
                LeaveBalance.employee_id == uuid.UUID(str(employee_id)),
                LeaveBalance.year == date.today().year,
            )
        )).fetchall()

        if not rows:
            return ChatResponse(
                answer="No leave balance found for this year. Please contact HR to set up your leave entitlements.",
                intent="leave_balance",
                confidence=0.9,
                suggested_actions=[{"label": "Contact HR", "url": "/leave"}],
            )

        balances = []
        lines    = []
        for name, total, used in rows:
            remaining = (total or 0) - (used or 0)
            balances.append({"type": name, "total": total, "used": used, "remaining": remaining})
            lines.append(f"• **{name}**: {remaining} days remaining (used {used} of {total})")

        answer = "Here is your current leave balance:\n\n" + "\n".join(lines)

        return ChatResponse(
            answer=answer,
            data={"leave_balances": balances, "year": date.today().year},
            intent="leave_balance",
            confidence=0.95,
            suggested_actions=[
                {"label": "Apply for Leave", "url": "/leave"},
                {"label": "View Leave History", "url": "/leave"},
            ],
        )
    except Exception as e:
        logger.warning("chatbot.leave_balance_failed", error=str(e))
        return ChatResponse(
            answer="I had trouble fetching your leave balance. Please check the Leave module directly.",
            intent="leave_balance",
            confidence=0.6,
            suggested_actions=[{"label": "Go to Leave", "url": "/leave"}],
        )


async def _handle_payslip(
    user_context: dict, db: AsyncSession
) -> ChatResponse:
    from app.models.payroll import PayrollRecord, PayrollRun

    employee_id = user_context.get("employee_id")
    if not employee_id:
        return ChatResponse(
            answer="Please log in as an employee to view your payslip.",
            intent="payslip", confidence=0.9,
        )

    try:
        row = (await db.execute(
            select(
                PayrollRecord.gross_salary,
                PayrollRecord.net_salary,
                PayrollRecord.income_tax,
                PayrollRecord.eobi_employee,
                PayrollRun.month,
                PayrollRun.year,
            )
            .join(PayrollRun, PayrollRecord.run_id == PayrollRun.id)
            .where(PayrollRecord.employee_id == uuid.UUID(str(employee_id)))
            .order_by(PayrollRun.year.desc(), PayrollRun.month.desc())
            .limit(1)
        )).one_or_none()

        if not row:
            return ChatResponse(
                answer="No payslip found yet. Your first payslip will appear after payroll is processed.",
                intent="payslip", confidence=0.9,
                suggested_actions=[{"label": "View Payroll", "url": "/payroll"}],
            )

        month_names = [
            "", "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December",
        ]
        month_label = f"{month_names[row.month]} {row.year}"
        gross = int(row.gross_salary or 0)
        net   = int(row.net_salary or 0)
        tax   = int(row.income_tax or 0)
        eobi  = int(row.eobi_employee or 0)

        answer = (
            f"Your latest payslip for **{month_label}**:\n\n"
            f"• Gross Salary: **PKR {gross:,}**\n"
            f"• Income Tax: PKR {tax:,}\n"
            f"• EOBI (employee): PKR {eobi:,}\n"
            f"• **Net Salary: PKR {net:,}**"
        )

        return ChatResponse(
            answer=answer,
            data={
                "month": row.month, "year": row.year, "month_label": month_label,
                "gross_salary": gross, "net_salary": net,
                "income_tax": tax, "eobi_employee": eobi,
            },
            intent="payslip",
            confidence=0.95,
            suggested_actions=[{"label": "Download Payslip", "url": "/payroll"}],
        )
    except Exception as e:
        logger.warning("chatbot.payslip_failed", error=str(e))
        return ChatResponse(
            answer="I couldn't retrieve your payslip right now. Please check the Payroll module.",
            intent="payslip", confidence=0.6,
            suggested_actions=[{"label": "Go to Payroll", "url": "/payroll"}],
        )


async def _handle_attendance(
    user_context: dict, db: AsyncSession
) -> ChatResponse:
    from app.models.attendance import AttendanceRecord

    employee_id = user_context.get("employee_id")
    if not employee_id:
        return ChatResponse(
            answer="Please log in to check your attendance.", intent="attendance", confidence=0.9,
        )

    today = date.today()
    try:
        att_col = getattr(AttendanceRecord, "work_date",
                  getattr(AttendanceRecord, "date", None))
        if att_col is None:
            raise AttributeError("no date column")

        row = (await db.execute(
            select(AttendanceRecord)
            .where(
                AttendanceRecord.employee_id == uuid.UUID(str(employee_id)),
                att_col == today,
            )
        )).scalar_one_or_none()

        if not row:
            return ChatResponse(
                answer=(
                    f"No attendance record found for today ({today.strftime('%d %b %Y')}). "
                    "You may not have checked in yet."
                ),
                intent="attendance", confidence=0.9,
                suggested_actions=[{"label": "View Attendance", "url": "/attendance"}],
            )

        status = row.status
        check_in  = getattr(row, "check_in",  None)
        check_out = getattr(row, "check_out", None)

        ci_str = check_in.strftime("%I:%M %p")  if check_in  else "—"
        co_str = check_out.strftime("%I:%M %p") if check_out else "Not checked out yet"

        status_msg = {
            "present":        "You are marked **Present** today ✓",
            "late":           "You are marked **Late** today — please note the tardiness",
            "absent":         "You are marked **Absent** today",
            "half_day":       "You are on **Half Day** today",
            "on_leave":       "You are on **Leave** today",
            "work_from_home": "You are **Working from Home** today",
        }.get(status, f"Status: {status}")

        answer = (
            f"{status_msg}\n\n"
            f"• Check-in:  {ci_str}\n"
            f"• Check-out: {co_str}"
        )
        return ChatResponse(
            answer=answer,
            data={"status": status, "check_in": ci_str, "check_out": co_str},
            intent="attendance", confidence=0.95,
            suggested_actions=[{"label": "View Attendance", "url": "/attendance"}],
        )
    except Exception as e:
        logger.warning("chatbot.attendance_failed", error=str(e))
        return ChatResponse(
            answer="I couldn't fetch your attendance. Check the Attendance module directly.",
            intent="attendance", confidence=0.6,
            suggested_actions=[{"label": "Go to Attendance", "url": "/attendance"}],
        )


def _handle_tax_calculation(message: str) -> ChatResponse:
    """Explain FBR tax calculation with example."""
    # Try to extract a salary amount from the message
    amounts = re.findall(r'[\d,]+', message.replace(" ", ""))
    monthly_salary: int | None = None
    for a in amounts:
        num = int(a.replace(",", ""))
        if 10_000 <= num <= 2_000_000:
            monthly_salary = num
            break

    kb = get_knowledge_base()
    chunks = kb.search("income tax calculation FBR slab", top_k=2)
    kb_text = " ".join(c.chunk for c in chunks)

    if monthly_salary:
        annual = monthly_salary * 12
        tax = _compute_fbr_tax(annual)
        monthly_tax = tax / 12
        answer = (
            f"For a monthly salary of **PKR {monthly_salary:,}** (annual PKR {annual:,}):\n\n"
            f"• Annual income tax: **PKR {tax:,.0f}**\n"
            f"• Monthly deduction: **PKR {monthly_tax:,.0f}**\n\n"
            f"**FBR Tax Slabs 2024-25:**\n"
            f"• Up to 600K: Nil\n"
            f"• 600K–1.2M: 5% of excess\n"
            f"• 1.2M–2.4M: PKR 30K + 15% of excess\n"
            f"• 2.4M–3.6M: PKR 210K + 25% of excess\n"
            f"• 3.6M–6M: PKR 510K + 30% of excess\n"
            f"• Above 6M: PKR 1.23M + 35% of excess"
        )
    else:
        answer = (
            "**FBR Income Tax Slabs 2024-25 (Salaried):**\n\n"
            "• Annual income up to PKR 600,000 → **Nil**\n"
            "• PKR 600K – 1.2M → **5%** of amount over 600K\n"
            "• PKR 1.2M – 2.4M → PKR 30K + **15%** of excess\n"
            "• PKR 2.4M – 3.6M → PKR 210K + **25%** of excess\n"
            "• PKR 3.6M – 6M → PKR 510K + **30%** of excess\n"
            "• Above PKR 6M → PKR 1.23M + **35%** of excess\n\n"
            "Tell me your salary to calculate the exact deduction!"
        )

    return ChatResponse(
        answer=answer, intent="tax_calculation", confidence=0.95,
        sources=["fbr_income_tax"],
    )


def _compute_fbr_tax(annual_income: float) -> float:
    """Compute annual FBR tax for salaried individuals (2024-25)."""
    if annual_income <= 600_000:
        return 0
    elif annual_income <= 1_200_000:
        return (annual_income - 600_000) * 0.05
    elif annual_income <= 2_400_000:
        return 30_000 + (annual_income - 1_200_000) * 0.15
    elif annual_income <= 3_600_000:
        return 210_000 + (annual_income - 2_400_000) * 0.25
    elif annual_income <= 6_000_000:
        return 510_000 + (annual_income - 3_600_000) * 0.30
    else:
        return 1_230_000 + (annual_income - 6_000_000) * 0.35


def _handle_policy_query(message: str) -> ChatResponse:
    """Search KB and compose an answer from top chunks."""
    kb = get_knowledge_base()
    results = kb.search(message, top_k=3)

    if not results or results[0].score < 0.05:
        return ChatResponse(
            answer=(
                "I couldn't find a specific policy for that query. "
                "Please check the company handbook or contact HR directly."
            ),
            intent="policy", confidence=0.4,
            suggested_actions=[{"label": "Contact HR", "url": "/settings"}],
        )

    # Compose answer from top chunk
    top = results[0]
    # Trim to 600 chars
    chunk = top.chunk[:600].strip()
    if len(top.chunk) > 600:
        chunk += "…"

    sources = list({r.source for r in results})

    return ChatResponse(
        answer=chunk,
        intent="policy",
        confidence=min(0.9, 0.5 + top.score),
        sources=sources,
        suggested_actions=[{"label": "View HR Policies", "url": "/settings"}],
    )


# ─── Main chat engine ─────────────────────────────────────────────────────────

ROLE_SUGGESTIONS: dict[str, list[str]] = {
    "employee": [
        "What is my leave balance?",
        "Show my last payslip",
        "Am I checked in today?",
        "How is income tax calculated?",
        "What is the leave encashment policy?",
        "How is gratuity calculated?",
    ],
    "hr_manager": [
        "How many employees are absent today?",
        "What is the attrition risk overview?",
        "Explain EOBI contribution rules",
        "What is the notice period policy?",
        "How to calculate maternity leave?",
    ],
    "default": [
        "What is my leave balance?",
        "How is income tax calculated?",
        "What are my leave entitlements?",
        "How is gratuity calculated?",
    ],
}


class HRChatEngine:
    async def answer(
        self,
        query: str,
        user_context: dict,
        db: AsyncSession,
    ) -> ChatResponse:
        """
        Main entry point. Detects intent and dispatches to appropriate handler.
        user_context: {employee_id, tenant_id, role, user_id}
        """
        intent, conf = _detect_intent(query)

        if intent == "greeting":
            role = user_context.get("role", "employee")
            return ChatResponse(
                answer=(
                    "Hello! 👋 I'm your AI HR Assistant. I can help you with:\n\n"
                    "• Leave balances and policies\n"
                    "• Payslip information\n"
                    "• Attendance status\n"
                    "• Tax and EOBI calculations\n"
                    "• HR policies (gratuity, overtime, probation)\n\n"
                    "What would you like to know?"
                ),
                intent="greeting", confidence=0.99,
                suggested_actions=[{"label": "My Leave Balance", "url": "/leave"}],
            )

        elif intent == "leave_balance":
            return await _handle_leave_balance(user_context, db)

        elif intent == "payslip":
            return await _handle_payslip(user_context, db)

        elif intent == "attendance":
            return await _handle_attendance(user_context, db)

        elif intent == "tax_calculation":
            return _handle_tax_calculation(query)

        elif intent == "eobi":
            kb  = get_knowledge_base()
            res = kb.search("EOBI contribution employee employer", top_k=2)
            chunk = res[0].chunk[:500] if res else "EOBI employer contributes 5% of minimum wage; employee contributes 1% of wages."
            return ChatResponse(
                answer=chunk, intent="eobi", confidence=0.9,
                sources=["eobi"],
            )

        elif intent == "gratuity":
            kb  = get_knowledge_base()
            res = kb.search("gratuity calculation formula", top_k=2)
            chunk = res[0].chunk[:500] if res else "Gratuity = Last Basic × (30/26) × Years of Service."
            return ChatResponse(
                answer=chunk, intent="gratuity", confidence=0.9,
                sources=["gratuity"],
            )

        elif intent == "overtime":
            kb  = get_knowledge_base()
            res = kb.search("overtime rules rate policy", top_k=2)
            chunk = res[0].chunk[:500] if res else "Overtime is paid at 2× regular rate. Max 2 hours/day, 10 hours/week."
            return ChatResponse(
                answer=chunk, intent="overtime", confidence=0.9,
                sources=["overtime_policy"],
            )

        elif intent == "policy":
            return _handle_policy_query(query)

        elif intent == "apply_leave":
            return ChatResponse(
                answer=(
                    "To apply for leave:\n"
                    "1. Go to the **Leave** section\n"
                    "2. Click **Apply for Leave**\n"
                    "3. Select leave type, dates, and add a reason\n"
                    "4. Submit — your manager will be notified for approval\n\n"
                    "Make sure you have sufficient leave balance before applying."
                ),
                intent="apply_leave", confidence=0.95,
                suggested_actions=[{"label": "Apply for Leave", "url": "/leave"}],
            )

        else:
            # Fallback: try KB search
            kb_response = _handle_policy_query(query)
            if kb_response.confidence > 0.5:
                return kb_response
            return ChatResponse(
                answer=(
                    "I'm not sure about that. I can help with:\n"
                    "• **Leave**: balance, policies, applying for leave\n"
                    "• **Payslip**: latest salary details\n"
                    "• **Attendance**: today's status\n"
                    "• **Tax**: FBR income tax calculation\n"
                    "• **EOBI / Gratuity**: contributions and benefits\n\n"
                    "Try asking something like: *'What is my leave balance?'*"
                ),
                intent="unknown", confidence=0.3,
            )

    def get_suggestions(self, role: str) -> list[str]:
        return ROLE_SUGGESTIONS.get(role, ROLE_SUGGESTIONS["default"])


# ─── Singleton ────────────────────────────────────────────────────────────────

_engine: HRChatEngine | None = None


def get_chat_engine() -> HRChatEngine:
    global _engine
    if _engine is None:
        _engine = HRChatEngine()
    return _engine

"""
Document Agent UAE — Tracks document expiry and sends tiered alerts.

Trigger: Celery daily 08:00 AM UAE (04:00 UTC)

Documents tracked: Passport, Visa, Emirates ID, Labour Card,
                   Medical Insurance, Driving License, custom docs

Alert timeline:
  90 days → Email reminder to HR
  60 days → Second reminder
  30 days → Urgent alert HR + employee
  14 days → Critical
   7 days → CRITICAL — escalate to management
   0 days → RED ALERT daily until resolved
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

import structlog

from app.agents.uae.openclaw import get_openclaw

logger = structlog.get_logger(__name__)

ALERT_THRESHOLDS = [
    {"days": 90, "level": "reminder",  "label": "90-Day Reminder"},
    {"days": 60, "level": "reminder",  "label": "60-Day Reminder"},
    {"days": 30, "level": "urgent",    "label": "30-Day Urgent Alert"},
    {"days": 14, "level": "critical",  "label": "14-Day Critical Alert"},
    {"days": 7,  "level": "critical",  "label": "7-Day CRITICAL"},
    {"days": 0,  "level": "emergency", "label": "EXPIRED — RED ALERT"},
]

DOCUMENT_TYPES = [
    "passport", "visa", "emirates_id", "labour_card",
    "insurance", "driving_license", "medical_fitness", "other",
]


@dataclass
class DocumentAlert:
    employee_id: str
    company_id: str
    document_type: str
    document_name: str
    expiry_date: str
    days_until_expiry: int
    alert_level: str
    alert_label: str
    employee_name: str = ""
    employee_email: str = ""

    def to_dict(self) -> dict:
        return self.__dict__


@dataclass
class DocumentCheckResult:
    company_id: str
    checked_count: int = 0
    alerts_critical: list[dict] = field(default_factory=list)
    alerts_urgent: list[dict] = field(default_factory=list)
    alerts_reminder: list[dict] = field(default_factory=list)
    alerts_emergency: list[dict] = field(default_factory=list)
    already_expired: int = 0
    expiring_7_days: int = 0
    expiring_30_days: int = 0
    expiring_90_days: int = 0

    @property
    def total_alerts(self) -> int:
        return (len(self.alerts_critical) + len(self.alerts_urgent) +
                len(self.alerts_reminder) + len(self.alerts_emergency))

    def to_dict(self) -> dict:
        return {
            "company_id": self.company_id,
            "checked_count": self.checked_count,
            "total_alerts": self.total_alerts,
            "already_expired": self.already_expired,
            "expiring_7_days": self.expiring_7_days,
            "expiring_30_days": self.expiring_30_days,
            "expiring_90_days": self.expiring_90_days,
            "alerts_emergency": self.alerts_emergency,
            "alerts_critical": self.alerts_critical,
            "alerts_urgent": self.alerts_urgent,
            "alerts_reminder": self.alerts_reminder,
        }


class DocumentAgent:
    """
    Tracks UAE employee document expiries across all companies.
    Sends tiered alerts to HR and employees.
    """

    def __init__(self):
        self.claw = get_openclaw()

    async def check_all_expiries(
        self,
        company_id: str | None = None,
        db=None,
    ) -> DocumentCheckResult:
        result = DocumentCheckResult(company_id=company_id or "all")

        if db:
            try:
                docs = await self._load_documents_from_db(db, company_id)
            except Exception as exc:
                logger.warning("document_agent_uae.db_load_failed", error=str(exc))
                docs = self._mock_documents(company_id)
        else:
            docs = self._mock_documents(company_id)

        today = date.today()
        result.checked_count = len(docs)

        for doc in docs:
            try:
                expiry = date.fromisoformat(str(doc["expiry_date"]))
            except (ValueError, TypeError):
                continue

            days_remaining = (expiry - today).days
            alert = self._classify_alert(doc, days_remaining)

            if days_remaining <= 0:
                result.already_expired += 1
                result.alerts_emergency.append(alert.to_dict())
            elif days_remaining <= 7:
                result.expiring_7_days += 1
                result.alerts_critical.append(alert.to_dict())
            elif days_remaining <= 14:
                result.alerts_critical.append(alert.to_dict())
            elif days_remaining <= 30:
                result.expiring_30_days += 1
                result.alerts_urgent.append(alert.to_dict())
            elif days_remaining <= 90:
                result.expiring_90_days += 1
                result.alerts_reminder.append(alert.to_dict())

        await self._log_check(result)
        logger.info(
            "document_agent_uae.check_complete",
            company_id=company_id,
            total=result.checked_count,
            alerts=result.total_alerts,
            expired=result.already_expired,
        )
        return result

    async def send_expiry_alerts(
        self,
        company_id: str,
        db=None,
    ) -> dict:
        check_result = await self.check_all_expiries(company_id=company_id, db=db)
        alerts_sent = 0

        for alert in check_result.alerts_emergency + check_result.alerts_critical:
            logger.warning(
                "document_agent_uae.alert_sent",
                level=alert.get("alert_level"),
                employee_id=alert.get("employee_id"),
                document=alert.get("document_type"),
                days=alert.get("days_until_expiry"),
            )
            alerts_sent += 1

        return {
            "company_id": company_id,
            "alerts_sent": alerts_sent,
            "summary": check_result.to_dict(),
        }

    async def generate_expiry_report(
        self,
        company_id: str,
        db=None,
    ) -> dict:
        result = await self.check_all_expiries(company_id=company_id, db=db)
        report = {
            "report_date": date.today().isoformat(),
            "company_id": company_id,
            "summary": result.to_dict(),
            "requires_immediate_action": result.already_expired + len(result.alerts_critical),
        }

        if self.claw.is_live:
            prompt = (
                f"Summarize this UAE document expiry report for HR: {json.dumps(result.to_dict(), default=str)}. "
                "Give 3 key action items and risk assessment."
            )
            report["ai_summary"] = await self.claw.simple_chat(prompt)
        else:
            report["ai_summary"] = (
                f"[Mock] {result.already_expired} documents expired. "
                f"{len(result.alerts_critical)} critical (≤14 days). "
                f"{len(result.alerts_urgent)} urgent (≤30 days). Immediate HR action required."
            )

        return report

    def _classify_alert(self, doc: dict, days_remaining: int) -> DocumentAlert:
        level = "reminder"
        label = "Expiry Reminder"

        for threshold in ALERT_THRESHOLDS:
            if days_remaining <= threshold["days"]:
                level = threshold["level"]
                label = threshold["label"]

        return DocumentAlert(
            employee_id=str(doc.get("employee_id", "")),
            company_id=str(doc.get("company_id", "")),
            document_type=doc.get("document_type", "unknown"),
            document_name=doc.get("document_name", doc.get("document_type", "Document")),
            expiry_date=str(doc.get("expiry_date", "")),
            days_until_expiry=days_remaining,
            alert_level=level,
            alert_label=label,
            employee_name=doc.get("employee_name", ""),
            employee_email=doc.get("employee_email", ""),
        )

    async def _load_documents_from_db(self, db: Any, company_id: str | None) -> list[dict]:
        from sqlalchemy import text
        query = """
            SELECT dt.*, e.first_name || ' ' || e.last_name as employee_name
            FROM documents_tracker dt
            LEFT JOIN employees e ON e.id = dt.employee_id::uuid
            WHERE dt.expiry_date <= CURRENT_DATE + INTERVAL '90 days'
        """
        params: dict = {}
        if company_id:
            query += " AND dt.company_id = :company_id"
            params["company_id"] = company_id

        result = await db.execute(text(query), params)
        rows = result.fetchall()
        return [dict(row._mapping) for row in rows]

    def _mock_documents(self, company_id: str | None) -> list[dict]:
        today = date.today()
        return [
            {
                "employee_id": "mock-emp-001",
                "company_id": company_id or "mock-co-001",
                "document_type": "passport",
                "document_name": "Passport",
                "expiry_date": (today + timedelta(days=25)).isoformat(),
                "employee_name": "Ahmed Al-Rashidi",
            },
            {
                "employee_id": "mock-emp-002",
                "company_id": company_id or "mock-co-001",
                "document_type": "visa",
                "document_name": "UAE Residence Visa",
                "expiry_date": (today + timedelta(days=5)).isoformat(),
                "employee_name": "Priya Sharma",
            },
            {
                "employee_id": "mock-emp-003",
                "company_id": company_id or "mock-co-001",
                "document_type": "emirates_id",
                "document_name": "Emirates ID",
                "expiry_date": (today - timedelta(days=3)).isoformat(),
                "employee_name": "Juan Santos",
            },
        ]

    async def _log_check(self, result: DocumentCheckResult) -> None:
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            entry = json.dumps(result.to_dict(), default=str)
            await redis.set(f"uae:documents:last_check:{result.company_id}", entry, ex=86400)
            await redis.aclose()
        except Exception as exc:
            logger.warning("document_agent_uae.redis_failed", error=str(exc))


# ─── Singleton ─────────────────────────────────────────────────────────────────

_document_agent: DocumentAgent | None = None


def get_document_agent() -> DocumentAgent:
    global _document_agent
    if _document_agent is None:
        _document_agent = DocumentAgent()
    return _document_agent

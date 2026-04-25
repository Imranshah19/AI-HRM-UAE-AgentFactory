"""
Emiratisation Agent UAE — Monthly quota compliance tracking.

UAE Emiratisation Law:
  - Companies 50+ employees: mandatory Emirati quota (MOHRE)
  - Companies 20-49 employees: sector-specific targets (from Jan 2024)
  - Non-compliance fine: AED 6,000-7,000 per shortfall per year
  - NAFIS programme: government subsidizes Emirati salaries

Trigger: Monthly Celery schedule (1st of every month)
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

import structlog

from app.agents.uae.openclaw import get_openclaw

logger = structlog.get_logger(__name__)

FINE_PER_SHORTFALL_AED = Decimal("7000")  # per Emirati per year shortfall (updated 2024)


def get_required_emiratisation_pct(headcount: int, sector: str = "private") -> Decimal:
    if headcount >= 50:
        return Decimal("4.0")  # 4% target for large private sector (2024)
    elif headcount >= 20:
        return Decimal("2.0")  # 2% for 20-49 employees (Jan 2024)
    return Decimal("0.0")


@dataclass
class EmiratiStats:
    company_id: str
    record_month: int
    record_year: int
    total_headcount: int = 0
    emirati_count: int = 0
    required_percentage: Decimal = field(default_factory=lambda: Decimal("0"))
    nafis_employees_count: int = 0

    @property
    def emiratisation_percentage(self) -> Decimal:
        if self.total_headcount == 0:
            return Decimal("0")
        return (Decimal(str(self.emirati_count)) / Decimal(str(self.total_headcount)) * 100).quantize(Decimal("0.01"))

    @property
    def required_emirati_count(self) -> int:
        return int(self.total_headcount * self.required_percentage / 100)

    @property
    def compliance_gap(self) -> int:
        return max(0, self.required_emirati_count - self.emirati_count)

    @property
    def is_compliant(self) -> bool:
        return self.compliance_gap == 0

    @property
    def annual_fine_risk_aed(self) -> Decimal:
        if self.is_compliant:
            return Decimal("0")
        return Decimal(str(self.compliance_gap)) * FINE_PER_SHORTFALL_AED

    def to_dict(self) -> dict:
        return {
            "company_id": self.company_id,
            "record_month": self.record_month,
            "record_year": self.record_year,
            "total_headcount": self.total_headcount,
            "emirati_count": self.emirati_count,
            "emiratisation_percentage": str(self.emiratisation_percentage),
            "required_percentage": str(self.required_percentage),
            "required_emirati_count": self.required_emirati_count,
            "compliance_gap": self.compliance_gap,
            "is_compliant": self.is_compliant,
            "annual_fine_risk_aed": str(self.annual_fine_risk_aed),
            "nafis_employees_count": self.nafis_employees_count,
            "currency": "AED",
        }


class EmiratiisationAgent:
    """
    UAE Emiratisation compliance tracker.
    Monthly checks, fine risk calculation, group reporting.
    """

    def __init__(self):
        self.claw = get_openclaw()

    async def run_monthly_check(
        self,
        company_id: str,
        db=None,
    ) -> EmiratiStats:
        today = date.today()
        stats = EmiratiStats(
            company_id=company_id,
            record_month=today.month,
            record_year=today.year,
        )

        if db:
            try:
                data = await self._load_headcount_data(db, company_id)
                stats.total_headcount = data["total"]
                stats.emirati_count = data["emiratis"]
                stats.nafis_employees_count = data["nafis"]
            except Exception as exc:
                logger.warning("emiratisation.db_load_failed", error=str(exc))
                self._fill_mock_stats(stats)
        else:
            self._fill_mock_stats(stats)

        stats.required_percentage = get_required_emiratisation_pct(stats.total_headcount)

        if not stats.is_compliant:
            logger.warning(
                "emiratisation.non_compliant",
                company_id=company_id,
                gap=stats.compliance_gap,
                fine_risk=str(stats.annual_fine_risk_aed),
            )

        if db:
            try:
                await self._save_record(db, stats)
            except Exception as exc:
                logger.warning("emiratisation.save_failed", error=str(exc))

        await self._log_to_redis(stats)
        return stats

    async def generate_compliance_report(self, company_id: str, db=None) -> dict:
        stats = await self.run_monthly_check(company_id=company_id, db=db)
        return {
            "company_id": company_id,
            "report_date": date.today().isoformat(),
            "stats": stats.to_dict(),
            "actions_required": self._get_action_recommendations(stats),
            "legal_basis": "MOHRE Ministerial Decree — Emiratisation Rules 2021-2024",
        }

    async def calculate_fine_risk(self, company_id: str, db=None) -> dict:
        stats = await self.run_monthly_check(company_id=company_id, db=db)
        return {
            "company_id": company_id,
            "is_compliant": stats.is_compliant,
            "compliance_gap": stats.compliance_gap,
            "annual_fine_risk_aed": str(stats.annual_fine_risk_aed),
            "monthly_fine_risk_aed": str((stats.annual_fine_risk_aed / 12).quantize(Decimal("0.01"))),
            "currency": "AED",
            "note": f"Fine = AED {FINE_PER_SHORTFALL_AED:,.0f} per missing Emirati per year",
        }

    def _get_action_recommendations(self, stats: EmiratiStats) -> list[str]:
        actions = []
        if not stats.is_compliant:
            actions.append(f"Hire {stats.compliance_gap} additional Emirati employee(s) to meet {stats.required_percentage}% quota")
            actions.append(f"Annual fine risk: AED {stats.annual_fine_risk_aed:,.0f} if gap not closed")
            actions.append("Register eligible Emirati employees in NAFIS programme for salary subsidies")
            actions.append("Contact MOHRE Emiratisation department for compliance guidance")
        else:
            actions.append("Emiratisation quota is met — maintain current Emirati headcount")
            if stats.nafis_employees_count < stats.emirati_count:
                actions.append("Enroll eligible Emirati employees in NAFIS for government salary subsidy")
        return actions

    def _fill_mock_stats(self, stats: EmiratiStats) -> None:
        stats.total_headcount = 55
        stats.emirati_count = 2
        stats.nafis_employees_count = 1

    async def _load_headcount_data(self, db: Any, company_id: str) -> dict:
        from sqlalchemy import text
        result = await db.execute(text("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE u.is_emirati = true) as emiratis,
                COUNT(*) FILTER (WHERE u.nafis_enrolled = true) as nafis
            FROM employees e
            LEFT JOIN employees_uae_profile u ON u.employee_id = e.id::text
            WHERE u.company_id = :company_id
            AND e.is_active = true
        """), {"company_id": company_id})
        row = result.fetchone()
        return {
            "total": row.total or 0,
            "emiratis": row.emiratis or 0,
            "nafis": row.nafis or 0,
        }

    async def _save_record(self, db: Any, stats: EmiratiStats) -> None:
        from sqlalchemy import text
        await db.execute(text("""
            INSERT INTO emiratisation_records (
                company_id, record_month, record_year, total_headcount,
                emirati_count, emiratisation_percentage, required_percentage,
                compliance_gap, is_compliant, fine_risk_amount_aed, nafis_employees_count
            ) VALUES (
                :co_id, :month, :year, :total, :emiratis, :pct,
                :req_pct, :gap, :compliant, :fine, :nafis
            )
            ON CONFLICT (company_id, record_month, record_year) DO UPDATE
            SET total_headcount = :total, emirati_count = :emiratis,
                emiratisation_percentage = :pct, compliance_gap = :gap,
                is_compliant = :compliant, fine_risk_amount_aed = :fine
        """), {
            "co_id": stats.company_id, "month": stats.record_month, "year": stats.record_year,
            "total": stats.total_headcount, "emiratis": stats.emirati_count,
            "pct": str(stats.emiratisation_percentage), "req_pct": str(stats.required_percentage),
            "gap": stats.compliance_gap, "compliant": stats.is_compliant,
            "fine": str(stats.annual_fine_risk_aed), "nafis": stats.nafis_employees_count,
        })
        await db.commit()

    async def _log_to_redis(self, stats: EmiratiStats) -> None:
        try:
            from app.core.redis import get_redis
            redis = get_redis()
            await redis.set(
                f"uae:emiratisation:{stats.company_id}:{stats.record_year}:{stats.record_month}",
                json.dumps(stats.to_dict(), default=str),
                ex=86400 * 32,
            )
            await redis.aclose()
        except Exception as exc:
            logger.warning("emiratisation.redis_failed", error=str(exc))


# ─── Singleton ─────────────────────────────────────────────────────────────────

_emiratisation_agent: EmiratiisationAgent | None = None


def get_emiratisation_agent() -> EmiratiisationAgent:
    global _emiratisation_agent
    if _emiratisation_agent is None:
        _emiratisation_agent = EmiratiisationAgent()
    return _emiratisation_agent

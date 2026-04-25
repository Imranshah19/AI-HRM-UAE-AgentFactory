"""
UAE Companies API — Group + Company management.

GET  /companies                    → list all companies in group
POST /companies                    → create new company
GET  /companies/{id}               → company details
PUT  /companies/{id}               → update company
GET  /companies/{id}/dashboard     → company HR dashboard
GET  /companies/{id}/compliance    → full compliance status
GET  /group/dashboard              → ALL companies consolidated
GET  /group/payroll-summary        → group total payroll (AED)
GET  /group/emiratisation          → group Emiratisation report
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Any
from decimal import Decimal
from datetime import date

import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/companies", tags=["UAE Companies"])
group_router = APIRouter(prefix="/group", tags=["UAE Group"])


# ─── Schemas ────────────────────────────────────────────────────────────────────

class CompanyCreate(BaseModel):
    group_name: str
    name_en: str
    name_ar: str = ""
    trade_license_number: str = ""
    mohre_establishment_id: str = ""
    emirate: str = "Dubai"
    industry_type: str = ""
    is_freezone: bool = False
    freezone_name: str = ""

class CompanyUpdate(BaseModel):
    name_en: str | None = None
    name_ar: str | None = None
    mohre_establishment_id: str | None = None
    emirate: str | None = None
    is_active: bool | None = None


# ─── Company routes ────────────────────────────────────────────────────────────

@router.get("", summary="List all companies in group")
async def list_companies() -> dict:
    return {
        "companies": [
            {
                "id": "co-001", "group_name": "Gulf Holdings",
                "name_en": "Gulf Holdings Company A", "name_ar": "شركة خليج هولدينج أ",
                "emirate": "Dubai", "industry_type": "Technology",
                "employee_count": 55, "is_active": True, "is_freezone": True,
                "freezone_name": "DMCC",
            },
            {
                "id": "co-002", "group_name": "Gulf Holdings",
                "name_en": "Gulf Holdings Company B", "name_ar": "شركة خليج هولدينج ب",
                "emirate": "Abu Dhabi", "industry_type": "Construction",
                "employee_count": 120, "is_active": True, "is_freezone": False,
            },
        ],
        "total": 2,
        "group_name": "Gulf Holdings",
    }


@router.post("", status_code=status.HTTP_201_CREATED, summary="Create new company")
async def create_company(payload: CompanyCreate) -> dict:
    logger.info("uae.company.create", name=payload.name_en, emirate=payload.emirate)
    return {
        "id": "co-new-001",
        "message": "Company created successfully",
        "company": payload.dict(),
        "note": "Connect to DB to persist — mock response",
    }


@router.get("/{company_id}", summary="Company details")
async def get_company(company_id: str) -> dict:
    return {
        "id": company_id,
        "group_name": "Gulf Holdings",
        "name_en": "Gulf Holdings Company A",
        "name_ar": "شركة خليج هولدينج أ",
        "emirate": "Dubai",
        "industry_type": "Technology",
        "mohre_establishment_id": "MOL-2024-12345",
        "trade_license_number": "DED-2024-98765",
        "is_freezone": True,
        "freezone_name": "DMCC",
        "employee_count": 55,
        "is_active": True,
    }


@router.put("/{company_id}", summary="Update company")
async def update_company(company_id: str, payload: CompanyUpdate) -> dict:
    return {"id": company_id, "updated": True, "fields": payload.dict(exclude_none=True)}


@router.get("/{company_id}/dashboard", summary="Company HR dashboard")
async def get_company_dashboard(company_id: str) -> dict:
    return {
        "company_id": company_id,
        "report_date": date.today().isoformat(),
        "stats": {
            "total_employees": 55,
            "on_leave_today": 3,
            "on_probation": 4,
            "expiring_documents_30d": 7,
            "expiring_contracts_30d": 2,
            "expiring_insurance_30d": 5,
        },
        "compliance": {
            "wps_status": "submitted",
            "wps_last_submission": "2026-03-28",
            "emiratisation_percentage": "3.64",
            "emiratisation_target": "4.00",
            "emiratisation_compliant": False,
            "emiratisation_gap": 1,
        },
        "payroll": {
            "last_run_month": 3,
            "last_run_year": 2026,
            "total_net_aed": "432750.00",
            "wps_submitted": True,
        },
        "alerts_count": {
            "critical": 2,
            "urgent": 5,
            "reminder": 8,
        },
        "currency": "AED",
    }


@router.get("/{company_id}/compliance", summary="Full company compliance status")
async def get_company_compliance(company_id: str) -> dict:
    from app.agents.uae.document import get_document_agent
    from app.agents.uae.emiratisation import get_emiratisation_agent
    from app.agents.uae.wps import get_wps_agent

    doc_agent = get_document_agent()
    doc_result = await doc_agent.check_all_expiries(company_id=company_id)

    emirat_agent = get_emiratisation_agent()
    emirat_result = await emirat_agent.run_monthly_check(company_id=company_id)

    wps_agent = get_wps_agent()
    wps_alerts = await wps_agent.send_deadline_alerts(company_id=company_id)

    return {
        "company_id": company_id,
        "report_date": date.today().isoformat(),
        "documents": doc_result.to_dict(),
        "emiratisation": emirat_result.to_dict(),
        "wps": wps_alerts,
    }


# ─── Group routes ──────────────────────────────────────────────────────────────

@group_router.get("/dashboard", summary="Group-level consolidated dashboard")
async def get_group_dashboard() -> dict:
    return {
        "report_date": date.today().isoformat(),
        "group_name": "Gulf Holdings",
        "total_companies": 2,
        "consolidated": {
            "total_employees": 175,
            "total_monthly_payroll_aed": "1850000.00",
            "total_critical_alerts": 7,
            "avg_emiratisation_pct": "3.2",
            "companies_wps_compliant": 2,
            "companies_emiratisation_compliant": 0,
        },
        "companies": [
            {"id": "co-001", "name_en": "Company A", "employee_count": 55,
             "wps_status": "submitted", "emiratisation_pct": "3.64", "alerts": 3},
            {"id": "co-002", "name_en": "Company B", "employee_count": 120,
             "wps_status": "submitted", "emiratisation_pct": "3.00", "alerts": 4},
        ],
        "currency": "AED",
    }


@group_router.get("/payroll-summary", summary="Group total payroll in AED")
async def get_group_payroll_summary(month: int | None = None, year: int | None = None) -> dict:
    today = date.today()
    return {
        "month": month or today.month,
        "year": year or today.year,
        "total_companies": 2,
        "total_employees": 175,
        "total_gross_aed": "1905000.00",
        "total_net_aed": "1850000.00",
        "total_iloe_aed": "1050.00",
        "companies": [
            {"id": "co-001", "name_en": "Company A", "net_aed": "432750.00", "employees": 55},
            {"id": "co-002", "name_en": "Company B", "net_aed": "1417250.00", "employees": 120},
        ],
        "currency": "AED",
    }


@group_router.get("/emiratisation", summary="Group Emiratisation compliance report")
async def get_group_emiratisation() -> dict:
    return {
        "report_date": date.today().isoformat(),
        "group_name": "Gulf Holdings",
        "companies": [
            {
                "id": "co-001", "name_en": "Company A",
                "total_headcount": 55, "emirati_count": 2,
                "pct": "3.64", "required_pct": "4.00",
                "is_compliant": False, "gap": 1,
                "annual_fine_risk_aed": "7000.00",
            },
            {
                "id": "co-002", "name_en": "Company B",
                "total_headcount": 120, "emirati_count": 4,
                "pct": "3.33", "required_pct": "4.00",
                "is_compliant": False, "gap": 1,
                "annual_fine_risk_aed": "7000.00",
            },
        ],
        "total_fine_risk_aed": "14000.00",
        "currency": "AED",
    }


# Include group router inside companies router
router.include_router(group_router)

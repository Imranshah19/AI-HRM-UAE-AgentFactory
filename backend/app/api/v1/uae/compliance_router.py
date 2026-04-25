"""
UAE Compliance API.

GET /compliance/wps/{company_id}               → WPS submission status
GET /compliance/emiratisation/{company_id}     → Emiratisation stats
GET /compliance/documents/expiring/{company_id} → expiring docs
GET /compliance/contracts/expiring/{company_id} → expiring contracts
GET /compliance/insurance/expiring/{company_id} → expiring insurance
GET /compliance/group-report                   → all companies report
"""

from __future__ import annotations

from fastapi import APIRouter
from datetime import date

router = APIRouter(prefix="/compliance", tags=["UAE Compliance"])


@router.get("/wps/{company_id}", summary="WPS submission status for company")
async def get_wps_status(company_id: str) -> dict:
    from app.agents.uae.wps import get_wps_agent
    agent = get_wps_agent()
    alerts = await agent.send_deadline_alerts(company_id=company_id)
    validation = await agent.validate_wps_submission(
        company_id=company_id,
        month=date.today().month,
        year=date.today().year,
    )
    return {
        "company_id": company_id,
        "current_month": {
            "month": date.today().month,
            "year": date.today().year,
            "due_date": alerts.get("due_date"),
            "days_to_due": alerts.get("days_to_due"),
            "status": "pending_submission",
            "validation": validation,
        },
        "alerts": alerts.get("alerts_sent", []),
    }


@router.get("/emiratisation/{company_id}", summary="Emiratisation stats for company")
async def get_emiratisation_status(company_id: str) -> dict:
    from app.agents.uae.emiratisation import get_emiratisation_agent
    agent = get_emiratisation_agent()
    result = await agent.run_monthly_check(company_id=company_id)
    return result.to_dict()


@router.get("/documents/expiring/{company_id}", summary="Expiring documents for company")
async def get_expiring_documents(company_id: str, days: int = 90) -> dict:
    from app.agents.uae.document import get_document_agent
    agent = get_document_agent()
    result = await agent.check_all_expiries(company_id=company_id)
    return {
        "company_id": company_id,
        "report_date": date.today().isoformat(),
        "expiring_in_days": days,
        "summary": result.to_dict(),
    }


@router.get("/contracts/expiring/{company_id}", summary="Expiring contracts for company")
async def get_expiring_contracts(company_id: str) -> dict:
    from app.agents.uae.contract import get_contract_agent
    agent = get_contract_agent()
    result = await agent.check_contract_expiries(company_id=company_id)
    return result.to_dict()


@router.get("/insurance/expiring/{company_id}", summary="Expiring insurance for company")
async def get_expiring_insurance(company_id: str) -> dict:
    from app.agents.uae.insurance import get_insurance_agent
    agent = get_insurance_agent()
    result = await agent.check_insurance_expiries(company_id=company_id)
    return result.to_dict()


@router.get("/group-report", summary="Full compliance report across all companies")
async def get_group_compliance_report() -> dict:
    return {
        "report_date": date.today().isoformat(),
        "group_name": "Gulf Holdings",
        "companies": [
            {
                "id": "co-001", "name_en": "Company A",
                "wps": {"status": "submitted", "compliant": True},
                "emiratisation": {"pct": "3.64", "compliant": False, "fine_risk_aed": "7000.00"},
                "documents_expiring_30d": 3,
                "contracts_expiring_90d": 1,
                "insurance_expiring_30d": 2,
            },
            {
                "id": "co-002", "name_en": "Company B",
                "wps": {"status": "submitted", "compliant": True},
                "emiratisation": {"pct": "3.33", "compliant": False, "fine_risk_aed": "7000.00"},
                "documents_expiring_30d": 8,
                "contracts_expiring_90d": 3,
                "insurance_expiring_30d": 4,
            },
        ],
        "group_totals": {
            "total_fine_risk_aed": "14000.00",
            "total_critical_documents": 11,
            "total_expiring_contracts": 4,
        },
        "currency": "AED",
    }

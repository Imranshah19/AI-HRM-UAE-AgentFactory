"""
UAE Employee Profile API.

GET  /employees/{id}/uae-profile       → full UAE profile
PUT  /employees/{id}/uae-profile       → update UAE profile
GET  /employees/{id}/documents         → all documents + expiry status
POST /employees/{id}/documents         → add new document
GET  /employees/{id}/gratuity          → real-time gratuity amount
GET  /employees/{id}/final-settlement  → full final settlement calc
GET  /employees/{id}/leave-balance     → all 9 leave types
GET  /employees/{id}/salary-structure  → current salary + allowances
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/employees", tags=["UAE Employees"])


class UAEProfileUpdate(BaseModel):
    name_ar: str | None = None
    visa_expiry: str | None = None
    emirates_id: str | None = None
    emirates_id_expiry: str | None = None
    bank_iban: str | None = None
    is_emirati: bool | None = None
    nafis_enrolled: bool | None = None
    iloe_enrolled: bool | None = None
    air_ticket_entitlement: bool | None = None

class DocumentCreate(BaseModel):
    document_type: str
    document_number: str
    expiry_date: str
    issue_date: str = ""
    file_url: str = ""


@router.get("/{employee_id}/uae-profile", summary="Full UAE employee profile")
async def get_uae_profile(employee_id: str) -> dict:
    return {
        "employee_id": employee_id,
        "name_en": "Ahmed Al-Rashidi",
        "name_ar": "أحمد الراشدي",
        "nationality": "UAE",
        "company_id": "co-001",
        "passport_number": "A1234567",
        "passport_expiry": "2028-05-15",
        "visa_number": "UAE-2024-987654",
        "visa_type": "Employment",
        "visa_expiry": "2026-06-30",
        "emirates_id": "784-1990-1234567-8",
        "emirates_id_expiry": "2026-06-30",
        "labour_card_number": "CN-12345678",
        "labour_card_expiry": "2026-06-30",
        "mohre_person_id": "12345678901234",
        "bank_name": "Emirates NBD",
        "bank_iban": "AE070331234567890123456",
        "contract_type": "full-time",
        "contract_start": "2023-01-01",
        "contract_end": "2025-12-31",
        "probation_end_date": "2023-06-30",
        "notice_period_days": 30,
        "insurance_provider": "Daman",
        "insurance_policy_number": "DAM-12345",
        "insurance_expiry": "2026-12-31",
        "iloe_enrolled": True,
        "air_ticket_entitlement": True,
        "air_ticket_value_aed": "3000.00",
        "is_emirati": False,
        "nafis_enrolled": False,
        "work_location": "Dubai",
    }


@router.put("/{employee_id}/uae-profile", summary="Update UAE employee profile")
async def update_uae_profile(employee_id: str, payload: UAEProfileUpdate) -> dict:
    return {
        "employee_id": employee_id,
        "updated": True,
        "fields": payload.dict(exclude_none=True),
        "updated_at": date.today().isoformat(),
    }


@router.get("/{employee_id}/documents", summary="All employee documents + expiry status")
async def get_employee_documents(employee_id: str) -> dict:
    today = date.today()
    return {
        "employee_id": employee_id,
        "documents": [
            {
                "type": "passport", "name_en": "Passport", "name_ar": "جواز السفر",
                "document_number": "A1234567", "expiry_date": "2028-05-15",
                "days_until_expiry": (date(2028, 5, 15) - today).days,
                "status": "valid", "status_color": "green",
            },
            {
                "type": "visa", "name_en": "UAE Residence Visa", "name_ar": "تأشيرة الإقامة",
                "document_number": "UAE-2024-987654", "expiry_date": "2026-06-30",
                "days_until_expiry": (date(2026, 6, 30) - today).days,
                "status": "valid", "status_color": "green",
            },
            {
                "type": "emirates_id", "name_en": "Emirates ID", "name_ar": "الهوية الإماراتية",
                "document_number": "784-1990-1234567-8", "expiry_date": "2026-06-30",
                "days_until_expiry": (date(2026, 6, 30) - today).days,
                "status": "valid", "status_color": "green",
            },
            {
                "type": "insurance", "name_en": "Medical Insurance", "name_ar": "التأمين الصحي",
                "document_number": "DAM-12345", "expiry_date": "2026-12-31",
                "days_until_expiry": (date(2026, 12, 31) - today).days,
                "status": "valid", "status_color": "green",
            },
        ],
        "total_documents": 4,
        "expired_count": 0,
        "expiring_30d_count": 0,
    }


@router.post("/{employee_id}/documents", status_code=status.HTTP_201_CREATED,
             summary="Add new document for employee")
async def add_employee_document(employee_id: str, payload: DocumentCreate) -> dict:
    return {
        "employee_id": employee_id,
        "document_type": payload.document_type,
        "document_number": payload.document_number,
        "expiry_date": payload.expiry_date,
        "created": True,
        "tracking_active": True,
    }


@router.get("/{employee_id}/gratuity", summary="Real-time gratuity amount")
async def get_employee_gratuity(
    employee_id: str,
    basic_salary: float = 10000.0,
    join_date: str = "2022-01-01",
) -> dict:
    from app.agents.uae.gratuity import get_gratuity_agent
    agent = get_gratuity_agent()
    result = await agent.calculate_gratuity(
        employee_id=employee_id,
        company_id="",
        basic_salary_aed=basic_salary,
        join_date=join_date,
        exit_reason="accrual",
    )
    return result.to_dict()


@router.get("/{employee_id}/final-settlement", summary="Full final settlement calculation")
async def get_final_settlement(
    employee_id: str,
    exit_type: str = "resignation",
    company_id: str = "",
) -> dict:
    from app.agents.uae.offboarding import get_offboarding_agent
    agent = get_offboarding_agent()
    result = await agent.calculate_final_settlement(
        employee_id=employee_id,
        company_id=company_id or "co-001",
        exit_type=exit_type,
    )
    return result


@router.get("/{employee_id}/leave-balance", summary="All UAE leave type balances")
async def get_leave_balance(employee_id: str, company_id: str = "co-001") -> dict:
    from app.agents.uae.leave import get_leave_agent
    agent = get_leave_agent()
    result = await agent.get_leave_balance(employee_id=employee_id, company_id=company_id)
    return result.to_dict()


@router.get("/{employee_id}/salary-structure", summary="Current salary + allowances in AED")
async def get_salary_structure(employee_id: str) -> dict:
    return {
        "employee_id": employee_id,
        "basic_salary": "12000.00",
        "housing_allowance": "3000.00",
        "transport_allowance": "800.00",
        "food_allowance": "500.00",
        "phone_allowance": "200.00",
        "other_allowances": "0.00",
        "total_package": "16500.00",
        "iloe_deduction": "10.00",
        "net_estimated": "16490.00",
        "currency": "AED",
        "effective_from": "2024-01-01",
    }

"""UAE Attendance API — working hours, check-in/out, Ramadan mode."""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/attendance", tags=["UAE Attendance"])


class CheckInRequest(BaseModel):
    employee_id: str
    company_id: str
    verification_method: str = "manual"
    location_data: dict = {}


class CheckOutRequest(BaseModel):
    employee_id: str
    company_id: str


@router.get("/{company_id}/today", summary="Today's attendance summary")
async def get_attendance_today(company_id: str) -> dict:
    from app.agents.uae.attendance import get_attendance_agent
    agent = get_attendance_agent()
    result = await agent.generate_daily_report(company_id=company_id)
    return result.to_dict()


@router.get("/{employee_id}/report/{month}", summary="Monthly attendance report for employee")
async def get_monthly_report(employee_id: str, month: int, year: int = 0) -> dict:
    y = year or date.today().year
    return {
        "employee_id": employee_id,
        "month": month,
        "year": y,
        "total_working_days": 26,
        "present_days": 24,
        "absent_days": 1,
        "late_arrivals": 3,
        "total_overtime_hours": "8.5",
        "attendance_rate": "92.3%",
        "ramadan_month": False,
    }


@router.post("/checkin", summary="Employee check-in (UAE)")
async def checkin(payload: CheckInRequest) -> dict:
    from app.agents.uae.attendance import get_attendance_agent
    agent = get_attendance_agent()
    result = await agent.process_checkin(
        employee_id=payload.employee_id,
        company_id=payload.company_id,
        verification_method=payload.verification_method,
        location_data=payload.location_data,
    )
    return result.to_dict()


@router.post("/checkout", summary="Employee check-out (UAE)")
async def checkout(payload: CheckOutRequest) -> dict:
    from app.agents.uae.attendance import get_attendance_agent
    agent = get_attendance_agent()
    result = await agent.process_checkout(
        employee_id=payload.employee_id,
        company_id=payload.company_id,
    )
    return result.to_dict()

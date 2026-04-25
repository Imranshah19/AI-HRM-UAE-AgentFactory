"""UAE Leave API — 9 leave types per Federal Decree-Law 33/2021."""
from __future__ import annotations
from fastapi import APIRouter
from pydantic import BaseModel
from datetime import date

router = APIRouter(prefix="/leaves", tags=["UAE Leave"])


class LeaveApplicationRequest(BaseModel):
    employee_id: str
    company_id: str
    leave_type: str
    start_date: str
    end_date: str
    reason: str = ""


class LeaveActionRequest(BaseModel):
    actioned_by: str = ""
    reason: str = ""


@router.get("/{company_id}/today", summary="Employees on leave today")
async def get_leave_today(company_id: str) -> dict:
    return {
        "company_id": company_id,
        "date": date.today().isoformat(),
        "employees_on_leave": [
            {"employee_id": "001", "name": "Ahmed Al-Rashidi", "leave_type": "annual",
             "return_date": (date.today().replace(day=date.today().day + 3)).isoformat()},
            {"employee_id": "002", "name": "Priya Sharma", "leave_type": "sick",
             "return_date": (date.today().replace(day=date.today().day + 1)).isoformat()},
        ],
        "count": 2,
    }


@router.post("/apply", summary="Apply for leave (UAE law validation)")
async def apply_leave(payload: LeaveApplicationRequest) -> dict:
    from app.agents.uae.leave import get_leave_agent
    agent = get_leave_agent()
    result = await agent.process_leave_application(
        employee_id=payload.employee_id,
        company_id=payload.company_id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reason=payload.reason,
    )
    return result.to_dict()


@router.put("/{leave_id}/approve", summary="Manually approve leave")
async def approve_leave(leave_id: str, payload: LeaveActionRequest) -> dict:
    return {"leave_id": leave_id, "status": "approved", "actioned_by": payload.actioned_by}


@router.put("/{leave_id}/reject", summary="Manually reject leave")
async def reject_leave(leave_id: str, payload: LeaveActionRequest) -> dict:
    return {"leave_id": leave_id, "status": "rejected", "reason": payload.reason}


@router.get("/calendar/{company_id}", summary="Team leave calendar")
async def get_leave_calendar(company_id: str) -> dict:
    from app.agents.uae.leave import get_leave_agent
    agent = get_leave_agent()
    return await agent.get_team_calendar(company_id=company_id)

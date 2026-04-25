"""
AI-HRMS — Leave Management Pydantic v2 schemas.
"""

from __future__ import annotations

import enum
from datetime import date, datetime
from typing   import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class LeaveStatus(str, enum.Enum):
    pending   = "pending"
    approved  = "approved"
    rejected  = "rejected"
    cancelled = "cancelled"


# ─── Leave Type ───────────────────────────────────────────────────────────────

class LeaveTypeCreate(BaseModel):
    name:                   str   = Field(..., min_length=2, max_length=100)
    days_allowed:           int   = Field(..., ge=1, le=365)
    is_paid:                bool  = True
    carry_forward:          bool  = False
    max_carry_forward_days: int   = Field(0, ge=0, le=365)
    requires_document:      bool  = False
    color:                  str   = Field("#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    is_active:              bool  = True


class LeaveTypeUpdate(BaseModel):
    name:                   Optional[str]  = Field(None, min_length=2, max_length=100)
    days_allowed:           Optional[int]  = Field(None, ge=1, le=365)
    is_paid:                Optional[bool] = None
    carry_forward:          Optional[bool] = None
    max_carry_forward_days: Optional[int]  = Field(None, ge=0, le=365)
    requires_document:      Optional[bool] = None
    color:                  Optional[str]  = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    is_active:              Optional[bool] = None


class LeaveTypeResponse(BaseModel):
    id:                     str
    name:                   str
    days_allowed:           int
    is_paid:                bool
    carry_forward:          bool
    max_carry_forward_days: int
    requires_document:      bool
    color:                  str
    is_active:              bool

    model_config = {"from_attributes": True}


# ─── Leave Request ────────────────────────────────────────────────────────────

class LeaveRequestCreate(BaseModel):
    leave_type_id: str
    start_date:    date
    end_date:      date
    reason:        str   = Field(..., min_length=10, max_length=1000)
    document_url:  Optional[str] = None
    # HR/manager may apply on behalf of another employee
    employee_id:   Optional[str] = None

    @field_validator("end_date")
    @classmethod
    def end_must_be_gte_start(cls, v: date, info) -> date:
        start = info.data.get("start_date")
        if start and v < start:
            raise ValueError("end_date must be on or after start_date")
        return v


class LeaveRequestUpdate(BaseModel):
    """Only allowed while status=pending."""
    start_date:   Optional[date] = None
    end_date:     Optional[date] = None
    reason:       Optional[str]  = Field(None, min_length=10, max_length=1000)
    document_url: Optional[str]  = None

    @model_validator(mode="after")
    def check_dates(self) -> "LeaveRequestUpdate":
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class EmployeeMinimal(BaseModel):
    id:         str
    full_name:  str
    employee_code: str
    photo_url:  Optional[str] = None
    department_name:   Optional[str] = None
    designation_title: Optional[str] = None

    model_config = {"from_attributes": True}


class LeaveRequestResponse(BaseModel):
    id:               str
    leave_type_id:    str
    leave_type:       LeaveTypeResponse
    employee_id:      str
    employee:         EmployeeMinimal
    start_date:       date
    end_date:         date
    days:             int
    reason:           str
    document_url:     Optional[str]
    status:           LeaveStatus
    approved_by:      Optional[str]
    approved_by_name: Optional[str]
    approved_at:      Optional[datetime]
    rejection_reason: Optional[str]
    cancelled_at:     Optional[datetime]
    created_at:       datetime
    updated_at:       datetime

    model_config = {"from_attributes": True}


class LeaveRequestListItem(BaseModel):
    id:             str
    leave_type_id:  str
    leave_type_name: str
    leave_type_color: str
    employee_id:    str
    employee_name:  str
    employee_code:  str
    department_name: Optional[str]
    start_date:     date
    end_date:       date
    days:           int
    reason:         str
    status:         LeaveStatus
    approved_by_name: Optional[str]
    rejection_reason: Optional[str]
    created_at:     datetime

    model_config = {"from_attributes": True}


class LeaveRequestListResponse(BaseModel):
    count:   int
    results: list[LeaveRequestListItem]


# ─── Approval ─────────────────────────────────────────────────────────────────

class LeaveApprovalRequest(BaseModel):
    action:           str  = Field(..., pattern="^(approve|reject)$")
    rejection_reason: Optional[str] = Field(None, min_length=20, max_length=500)

    @model_validator(mode="after")
    def reason_required_for_reject(self) -> "LeaveApprovalRequest":
        if self.action == "reject" and not self.rejection_reason:
            raise ValueError("rejection_reason is required when rejecting a request")
        return self


# ─── Balance ──────────────────────────────────────────────────────────────────

class LeaveBalanceItem(BaseModel):
    leave_type_id:   str
    leave_type_name: str
    leave_type_color: str
    is_paid:         bool
    total_days:      int
    used_days:       int
    remaining_days:  int
    carried_forward: int

    model_config = {"from_attributes": True}


class LeaveBalanceResponse(BaseModel):
    employee_id:   str
    employee_name: str
    year:          int
    balances:      list[LeaveBalanceItem]


# ─── Calendar ─────────────────────────────────────────────────────────────────

class LeaveCalendarEntry(BaseModel):
    date:           date
    employee_id:    str
    employee_name:  str
    employee_code:  str
    photo_url:      Optional[str]
    leave_type_id:  str
    leave_type_name: str
    leave_type_color: str
    status:         LeaveStatus

    model_config = {"from_attributes": True}


# ─── Filters ──────────────────────────────────────────────────────────────────

class LeaveFilterParams(BaseModel):
    employee_id:    Optional[str]  = None
    department_id:  Optional[str]  = None
    leave_type_id:  Optional[str]  = None
    status:         Optional[LeaveStatus] = None
    start_date:     Optional[date] = None
    end_date:       Optional[date] = None
    page:           int = Field(1, ge=1)
    page_size:      int = Field(25, ge=1, le=100)


# ─── Public Holiday ───────────────────────────────────────────────────────────

class PublicHolidayCreate(BaseModel):
    date:         date
    name:         str = Field(..., min_length=2, max_length=200)
    is_recurring: bool = False  # repeat same date each year


class PublicHolidayResponse(BaseModel):
    id:           str
    date:         date
    name:         str
    is_recurring: bool

    model_config = {"from_attributes": True}

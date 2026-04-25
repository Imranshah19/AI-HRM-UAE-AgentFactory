"""
AI-HRMS — Payroll module Pydantic schemas.
"""

from __future__ import annotations

from datetime import datetime
from typing   import Optional
from enum     import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class PayrollRunStatus(str, Enum):
    draft      = "draft"
    processing = "processing"
    processed  = "processed"
    approved   = "approved"
    paid       = "paid"
    cancelled  = "cancelled"
    rejected   = "rejected"


class PayrollRecordStatus(str, Enum):
    pending   = "pending"
    processed = "processed"
    paid      = "paid"
    on_hold   = "on_hold"


class ApprovalAction(str, Enum):
    approve = "approve"
    reject  = "reject"


# ─── Tax Slabs ────────────────────────────────────────────────────────────────

class TaxSlabCreate(BaseModel):
    year:        int   = Field(..., ge=2020, le=2100)
    min_income:  int   = Field(..., ge=0)
    max_income:  Optional[int] = Field(None, ge=0)
    tax_rate:    float = Field(..., ge=0.0, le=1.0)
    fixed_tax:   int   = Field(0, ge=0)
    description: Optional[str] = Field(None, max_length=200)
    is_active:   bool  = True

    @model_validator(mode="after")
    def max_must_exceed_min(self) -> "TaxSlabCreate":
        if self.max_income is not None and self.max_income <= self.min_income:
            raise ValueError("max_income must be greater than min_income")
        return self


class TaxSlabUpdate(BaseModel):
    min_income:  Optional[int]   = None
    max_income:  Optional[int]   = None
    tax_rate:    Optional[float] = Field(None, ge=0.0, le=1.0)
    fixed_tax:   Optional[int]   = None
    description: Optional[str]   = None
    is_active:   Optional[bool]  = None


class TaxSlabResponse(BaseModel):
    id:          str
    year:        int
    min_income:  int
    max_income:  Optional[int]
    tax_rate:    float
    fixed_tax:   int
    description: Optional[str]
    is_active:   bool
    created_at:  datetime
    updated_at:  datetime

    model_config = {"from_attributes": True}


# ─── Employee Minimal ─────────────────────────────────────────────────────────

class EmployeeMinimal(BaseModel):
    id:               str
    employee_code:    str
    full_name:        str
    department_name:  Optional[str] = None
    designation_title: Optional[str] = None
    photo_url:        Optional[str] = None

    model_config = {"from_attributes": True}


# ─── Payroll Run ──────────────────────────────────────────────────────────────

class PayrollRunCreate(BaseModel):
    month:          int  = Field(..., ge=1, le=12)
    year:           int  = Field(..., ge=2020, le=2100)
    department_ids: Optional[list[str]] = Field(
        None, description="If provided, only process employees from these departments"
    )
    notes: Optional[str] = Field(None, max_length=500)


class PayrollRunResponse(BaseModel):
    id:                str
    month:             int
    year:              int
    label:             Optional[str]
    status:            str
    total_employees:   int
    total_gross:       int
    total_net:         int
    total_deductions:  int
    total_eobi_employee: int
    total_eobi_employer: int
    total_income_tax:  int
    processed_by:      Optional[str]
    approved_by:       Optional[str]
    run_at:            Optional[datetime]
    approved_at:       Optional[datetime]
    paid_at:           Optional[datetime]
    notes:             Optional[str]
    celery_task_id:    Optional[str]
    created_at:        datetime
    updated_at:        datetime

    model_config = {"from_attributes": True}


class PayrollRunListResponse(BaseModel):
    count:   int
    results: list[PayrollRunResponse]


# ─── Payroll Record ───────────────────────────────────────────────────────────

class PayrollRecordResponse(BaseModel):
    id:                  str
    payroll_run_id:      str
    employee_id:         str
    employee:            EmployeeMinimal

    # Earnings
    basic_salary:        int
    house_rent_allowance: int
    medical_allowance:   int
    transport_allowance: int
    fuel_allowance:      int
    other_allowances:    Optional[dict]
    total_allowances:    int
    gross_salary:        int

    # Deductions
    eobi_employee:       int
    eobi_employer:       int
    sessi:               int
    income_tax:          int
    loan_deduction:      int
    advance_deduction:   int
    other_deductions:    Optional[dict]
    total_deductions:    int
    net_salary:          int

    # Attendance
    working_days:        int
    present_days:        int
    absent_days:         int
    late_days:           int
    overtime_hours:      Optional[float]
    paid_leave_days:     float
    unpaid_leave_days:   float
    is_prorated:         bool

    payslip_url:         Optional[str]
    status:              str
    created_at:          datetime
    updated_at:          datetime

    model_config = {"from_attributes": True}


class PayrollRunDetailResponse(PayrollRunResponse):
    records: list[PayrollRecordResponse] = []


# ─── Payslip Data ─────────────────────────────────────────────────────────────

class AllowanceItem(BaseModel):
    name:   str
    amount: int


class DeductionItem(BaseModel):
    name:   str
    amount: int


class PayslipData(BaseModel):
    """Full data structure used for PDF generation."""
    record_id:      str
    payroll_run_id: str
    month:          int
    year:           int

    # Employee info
    employee_id:    str
    employee_code:  str
    full_name:      str
    designation:    Optional[str]
    department:     Optional[str]
    cnic:           Optional[str]
    joining_date:   Optional[str]

    # Bank
    bank_name:      Optional[str]
    account_number: Optional[str]
    iban:           Optional[str]

    # Earnings breakdown
    basic_salary:   int
    allowances:     list[AllowanceItem]
    total_allowances: int
    gross_salary:   int

    # Deductions breakdown
    deductions:     list[DeductionItem]
    total_deductions: int
    net_salary:     int

    # Attendance summary
    working_days:   int
    present_days:   int
    absent_days:    int
    paid_leave_days: float
    overtime_hours: Optional[float]
    overtime_amount: int

    # Generated
    generated_at:   datetime
    payslip_url:    Optional[str]


# ─── Salary Preview ───────────────────────────────────────────────────────────

class SalaryCalculationPreview(BaseModel):
    """Calculate salary without saving — what-if preview."""
    employee_id:     str
    employee_name:   str
    month:           int
    year:            int

    basic_salary:    int
    total_allowances: int
    gross_salary:    int

    eobi_employee:   int
    eobi_employer:   int
    income_tax:      int
    loan_deduction:  int
    advance_deduction: int
    other_deductions_total: int
    total_deductions: int
    net_salary:      int

    working_days:    int
    present_days:    int
    absent_days:     int
    overtime_hours:  float
    overtime_amount: int

    effective_tax_rate:  float
    annual_gross:        int
    annual_tax:          int


# ─── Filters ─────────────────────────────────────────────────────────────────

class PayrollFilterParams(BaseModel):
    month:       Optional[int]  = Field(None, ge=1, le=12)
    year:        Optional[int]  = Field(None, ge=2020, le=2100)
    department_id: Optional[str] = None
    status:      Optional[str]  = None
    employee_id: Optional[str]  = None
    page:        int = Field(1, ge=1)
    page_size:   int = Field(25, ge=1, le=100)


# ─── Approval ────────────────────────────────────────────────────────────────

class PayrollApprovalRequest(BaseModel):
    action: ApprovalAction
    notes:  Optional[str] = Field(None, max_length=500)

    @field_validator("notes")
    @classmethod
    def notes_required_for_reject(cls, v, info) -> Optional[str]:
        # Validation is done in service layer with full context
        return v


# ─── Bank File ───────────────────────────────────────────────────────────────

class BankFileEntry(BaseModel):
    employee_code:  str
    employee_name:  str
    bank_name:      str
    account_number: str
    iban:           Optional[str]
    net_salary:     int
    reference:      str

"""
AI-HRMS — Employee API Pydantic v2 schemas.

Covers all 5 wizard steps plus list/detail/filter output schemas.
"""

import uuid
from datetime import date
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


# ─── Nested / shared schemas ──────────────────────────────────────────────────

class AddressSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    line1:       str  = Field(..., max_length=200)
    line2:       str | None = Field(None, max_length=200)
    city:        str  = Field(..., max_length=100)
    state:       str | None = Field(None, max_length=100)
    postal_code: str | None = Field(None, max_length=20)
    country:     str  = Field("Pakistan", max_length=100)


class EmergencyContactSchema(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name:     str        = Field(..., max_length=200)
    relation: str        = Field(..., max_length=100)
    phone:    str        = Field(..., max_length=20)
    email:    str | None = Field(None, max_length=255)


# ─── Create / Update ──────────────────────────────────────────────────────────

class EmployeeCreateRequest(BaseModel):
    """
    Single payload that the 5-step Add Employee wizard POSTs on final submission.
    Steps 1–3 and Step 5 fields are all present; Step 4 (documents) is handled
    via a separate multipart endpoint.
    """
    model_config = ConfigDict(str_strip_whitespace=True)

    # ── Step 1: Personal ──────────────────────────────────────────────────────
    first_name:      str           = Field(..., min_length=1, max_length=100)
    last_name:       str           = Field(..., min_length=1, max_length=100)
    father_name:     str | None    = Field(None, max_length=200)
    cnic:            str | None    = Field(None, max_length=20,
                                           description="13-digit National ID, e.g. 42101-1234567-1")
    personal_email:  EmailStr | None = None
    phone:           str | None    = Field(None, max_length=20)
    gender:          Literal["male", "female", "other", "prefer_not_to_say"] | None = None
    dob:             date | None   = None
    marital_status:  Literal["single", "married", "divorced", "widowed"] | None = None
    nationality:     str | None    = Field(None, max_length=100)
    address:         AddressSchema | None = None
    emergency_contact: EmergencyContactSchema | None = None

    @field_validator("cnic")
    @classmethod
    def validate_cnic(cls, v: str | None) -> str | None:
        if v is None:
            return v
        # Accept with or without dashes; store normalised
        normalised = v.replace("-", "").replace(" ", "")
        if not normalised.isdigit() or len(normalised) != 13:
            raise ValueError("CNIC must be 13 digits (dashes optional), e.g. 42101-1234567-1")
        return f"{normalised[:5]}-{normalised[5:12]}-{normalised[12]}"

    # ── Step 2: Employment ────────────────────────────────────────────────────
    employee_code:       str | None    = Field(None, max_length=30,
                                               description="Leave blank to auto-generate")
    department_id:       uuid.UUID | None = None
    designation_id:      uuid.UUID | None = None
    manager_id:          uuid.UUID | None = None
    contract_type:       Literal["permanent", "contract", "probation", "intern", "consultant"] = "permanent"
    work_schedule:       Literal["full_time", "part_time", "remote", "hybrid"] = "full_time"
    join_date:           date | None   = None
    probation_end_date:  date | None   = None
    confirmation_date:   date | None   = None
    shift_id:            uuid.UUID | None = None
    timezone:            str           = Field("Asia/Karachi", max_length=50)
    branch_location:     str | None    = Field(None, max_length=200)
    cost_center:         str | None    = Field(None, max_length=50)
    grade_level:         str | None    = Field(None, max_length=50)

    # ── Step 3: Compensation ──────────────────────────────────────────────────
    basic_salary:          int        = Field(0, ge=0)
    house_rent_allowance:  int        = Field(0, ge=0)
    medical_allowance:     int        = Field(0, ge=0)
    transport_allowance:   int        = Field(0, ge=0)
    other_allowances:      dict[str, int] | None = Field(
        None,
        description='e.g. {"special_allowance": 5000, "phone_allowance": 2000}',
    )
    eobi_applicable:       bool       = True
    sessi_applicable:      bool       = False
    income_tax_applicable: bool       = True
    # Bank details
    bank_name:       str | None = Field(None, max_length=200)
    account_title:   str | None = Field(None, max_length=200)
    account_number:  str | None = Field(None, max_length=30)
    iban:            str | None = Field(None, max_length=34)

    # ── Step 5: Access & Onboarding ───────────────────────────────────────────
    role_id:           uuid.UUID | None = None
    it_assets:         dict[str, Any] | None = Field(
        None,
        description='{"laptop": true, "mobile": false, "access_card": true}',
    )
    onboarding_notes:  str | None = Field(None, max_length=2000)
    hr_notes:          str | None = Field(None, max_length=2000)


class EmployeeUpdateRequest(BaseModel):
    """Partial update — all fields optional (PATCH semantics)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    first_name:         str | None = Field(None, max_length=100)
    last_name:          str | None = Field(None, max_length=100)
    father_name:        str | None = Field(None, max_length=200)
    phone:              str | None = Field(None, max_length=20)
    personal_email:     EmailStr | None = None
    gender:             Literal["male", "female", "other", "prefer_not_to_say"] | None = None
    dob:                date | None = None
    marital_status:     Literal["single", "married", "divorced", "widowed"] | None = None
    nationality:        str | None = Field(None, max_length=100)
    address:            AddressSchema | None = None
    emergency_contact:  EmergencyContactSchema | None = None

    department_id:      uuid.UUID | None = None
    designation_id:     uuid.UUID | None = None
    manager_id:         uuid.UUID | None = None
    contract_type:      Literal["permanent", "contract", "probation", "intern", "consultant"] | None = None
    work_schedule:      Literal["full_time", "part_time", "remote", "hybrid"] | None = None
    join_date:          date | None = None
    probation_end_date: date | None = None
    confirmation_date:  date | None = None
    shift_id:           uuid.UUID | None = None
    timezone:           str | None = Field(None, max_length=50)
    branch_location:    str | None = Field(None, max_length=200)
    cost_center:        str | None = Field(None, max_length=50)
    grade_level:        str | None = Field(None, max_length=50)
    profile_photo_url:  str | None = Field(None, max_length=500)
    hr_notes:           str | None = Field(None, max_length=2000)


class EmployeeSalaryUpdateRequest(BaseModel):
    """Updates the active salary structure (closes old, creates new)."""
    model_config = ConfigDict(str_strip_whitespace=True)

    basic_salary:          int        = Field(..., ge=0)
    house_rent_allowance:  int        = Field(0, ge=0)
    medical_allowance:     int        = Field(0, ge=0)
    transport_allowance:   int        = Field(0, ge=0)
    other_allowances:      dict[str, int] | None = None
    eobi_applicable:       bool       = True
    sessi_applicable:      bool       = False
    income_tax_applicable: bool       = True
    effective_from:        date       = Field(..., description="Date the new salary takes effect")
    revision_note:         str | None = Field(None, max_length=500)


class EmployeeStatusUpdateRequest(BaseModel):
    employment_status: Literal[
        "active", "inactive", "terminated", "resigned", "on_leave", "suspended"
    ]
    reason:           str | None = Field(None, max_length=1000)
    effective_date:   date | None = None


# ─── Filter / Query params ────────────────────────────────────────────────────

class EmployeeFilterParams(BaseModel):
    """Query-string parameters for the employee list endpoint."""
    model_config = ConfigDict(str_strip_whitespace=True)

    department_id:  uuid.UUID | None = None
    designation_id: uuid.UUID | None = None
    manager_id:     uuid.UUID | None = None
    status:         Literal[
        "active", "inactive", "terminated", "resigned", "on_leave", "suspended"
    ] | None = None
    contract_type:  Literal[
        "permanent", "contract", "probation", "intern", "consultant"
    ] | None = None
    search:         str | None = Field(
        None,
        max_length=100,
        description="Full-text search across name, email, CNIC, employee_code",
    )
    page:      Annotated[int, Field(ge=1)]  = 1
    page_size: Annotated[int, Field(ge=1, le=100)] = 20


# ─── Response schemas ─────────────────────────────────────────────────────────

class DepartmentMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:   uuid.UUID
    name: str
    code: str | None = None


class DesignationMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:   uuid.UUID
    name: str


class ManagerMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:           uuid.UUID
    employee_code: str
    full_name:    str
    profile_photo_url: str | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:               uuid.UUID
    doc_type:         str
    doc_name:         str
    file_url:         str
    file_name:        str
    file_size_bytes:  int | None = None
    mime_type:        str | None = None
    expiry_date:      date | None = None
    is_verified:      bool
    is_deleted:       bool


class SalaryStructureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                    uuid.UUID
    basic_salary:          int
    house_rent_allowance:  int
    medical_allowance:     int
    transport_allowance:   int
    other_allowances:      dict | None = None
    eobi_applicable:       bool
    sessi_applicable:      bool
    income_tax_applicable: bool
    effective_from:        date
    effective_to:          date | None = None
    # Computed
    total_allowances: int = 0
    gross_salary:     int = 0

    @model_validator(mode="after")
    def compute_totals(self) -> "SalaryStructureOut":
        fixed = (
            self.house_rent_allowance
            + self.medical_allowance
            + self.transport_allowance
        )
        other = sum(self.other_allowances.values()) if self.other_allowances else 0
        self.total_allowances = fixed + other
        self.gross_salary = self.basic_salary + self.total_allowances
        return self


class BankDetailsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:             uuid.UUID
    bank_name:      str
    account_title:  str
    account_number: str
    iban:           str | None = None
    payment_method: str
    is_primary:     bool


class RoleMini(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:   uuid.UUID
    name: str


class EmployeeListItem(BaseModel):
    """Lightweight row for the employee table / list view."""
    model_config = ConfigDict(from_attributes=True)

    id:                uuid.UUID
    employee_code:     str
    full_name:         str
    work_email:        str | None
    department:        DepartmentMini | None = None
    designation:       DesignationMini | None = None
    employment_status: str
    contract_type:     str
    join_date:         date | None = None
    profile_photo_url: str | None = None


class EmployeeDetail(BaseModel):
    """Full employee record — returned by GET /employees/{id}."""
    model_config = ConfigDict(from_attributes=True)

    # Identity
    id:            uuid.UUID
    employee_code: str
    first_name:    str
    last_name:     str
    full_name:     str
    father_name:   str | None = None
    cnic:          str | None = None
    personal_email: str | None = None
    work_email:    str | None = None
    phone:         str | None = None
    gender:        str | None = None
    dob:           date | None = None
    marital_status: str | None = None
    nationality:   str | None = None
    address:       dict | None = None
    emergency_contact: dict | None = None
    profile_photo_url: str | None = None

    # Employment
    department:        DepartmentMini | None = None
    designation:       DesignationMini | None = None
    manager:           ManagerMini | None = None
    contract_type:     str
    work_schedule:     str
    employment_status: str
    join_date:         date | None = None
    probation_end_date: date | None = None
    confirmation_date:  date | None = None
    termination_date:   date | None = None
    termination_reason: str | None = None
    branch_location:    str | None = None
    cost_center:        str | None = None
    grade_level:        str | None = None
    timezone:           str

    # Compensation (active record only — null for employees with no salary set)
    salary:      SalaryStructureOut | None = None
    bank_details: list[BankDetailsOut] = []

    # Documents (non-deleted)
    documents: list[DocumentOut] = []

    # Access
    roles: list[RoleMini] = []

    hr_notes: str | None = None


class EmployeeCreatedResponse(BaseModel):
    """Minimal payload returned after POST /employees — used by the success modal."""
    id:            uuid.UUID
    employee_code: str
    work_email:    str | None
    full_name:     str


class EmployeeListResponse(BaseModel):
    """Paginated list wrapper."""
    items:      list[EmployeeListItem]
    total:      int
    page:       int
    page_size:  int
    pages:      int


class SalaryWithBankResponse(BaseModel):
    """Response for GET /employees/{id}/salary"""
    salary:       SalaryStructureOut | None
    bank_details: list[BankDetailsOut]

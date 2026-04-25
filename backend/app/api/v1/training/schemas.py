"""
AI-HRMS — Training Management Pydantic v2 schemas.
"""

from __future__ import annotations

from datetime  import date, datetime
from typing    import Any, Optional
from uuid      import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─── Enums (string literals) ──────────────────────────────────────────────────

TrainingMode       = str   # online | in_person | hybrid | self_paced
TrainingStatus     = str   # planned | registration_open | ongoing | completed | cancelled
EnrollmentStatus   = str   # enrolled | in_progress | completed | failed | absent | dropped


# ─── Nested ───────────────────────────────────────────────────────────────────

class EmployeeMinimal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            str
    employee_code: str
    full_name:     str
    department:    Optional[str] = None
    designation:   Optional[str] = None


# ─── Training Program ─────────────────────────────────────────────────────────

class TrainingProgramCreate(BaseModel):
    title:                       str   = Field(..., min_length=2, max_length=300)
    description:                 Optional[str]  = None
    category:                    Optional[str]  = Field(None, max_length=100)
    skills_covered:              Optional[list[str]] = None
    trainer:                     Optional[str]  = Field(None, max_length=200)
    trainer_id:                  Optional[UUID] = None
    mode:                        str            = "in_person"
    venue:                       Optional[str]  = Field(None, max_length=300)
    meeting_link:                Optional[str]  = Field(None, max_length=500)
    start_date:                  Optional[date] = None
    end_date:                    Optional[date] = None
    duration_hours:              Optional[float]= Field(None, ge=0.5)
    max_participants:            Optional[int]  = Field(None, ge=1)
    min_participants:            Optional[int]  = Field(None, ge=1)
    cost_per_participant:        Optional[int]  = Field(None, ge=0)
    currency:                    str            = "PKR"
    is_mandatory:                bool           = False
    issues_certificate:          bool           = False
    certificate_validity_months: Optional[int]  = Field(None, ge=1)
    material_url:                Optional[str]  = Field(None, max_length=500)
    external_url:                Optional[str]  = Field(None, max_length=500)

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        allowed = ("online", "in_person", "hybrid", "self_paced")
        if v not in allowed:
            raise ValueError(f"mode must be one of {allowed}")
        return v


class TrainingProgramUpdate(BaseModel):
    title:                       Optional[str]  = Field(None, min_length=2, max_length=300)
    description:                 Optional[str]  = None
    category:                    Optional[str]  = None
    skills_covered:              Optional[list[str]] = None
    trainer:                     Optional[str]  = None
    trainer_id:                  Optional[UUID] = None
    mode:                        Optional[str]  = None
    venue:                       Optional[str]  = None
    meeting_link:                Optional[str]  = None
    start_date:                  Optional[date] = None
    end_date:                    Optional[date] = None
    duration_hours:              Optional[float]= None
    max_participants:            Optional[int]  = None
    cost_per_participant:        Optional[int]  = None
    is_mandatory:                Optional[bool] = None
    issues_certificate:          Optional[bool] = None
    material_url:                Optional[str]  = None
    external_url:                Optional[str]  = None
    status:                      Optional[str]  = None


class TrainingProgramResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                          str
    tenant_id:                   str
    title:                       str
    description:                 Optional[str]  = None
    category:                    Optional[str]  = None
    skills_covered:              Optional[list[str]] = None
    trainer:                     Optional[str]  = None
    trainer_id:                  Optional[str]  = None
    mode:                        str
    venue:                       Optional[str]  = None
    meeting_link:                Optional[str]  = None
    start_date:                  Optional[date] = None
    end_date:                    Optional[date] = None
    duration_hours:              Optional[float]= None
    max_participants:            Optional[int]  = None
    min_participants:            Optional[int]  = None
    cost_per_participant:        Optional[int]  = None
    currency:                    str
    is_mandatory:                bool
    issues_certificate:          bool
    certificate_validity_months: Optional[int]  = None
    material_url:                Optional[str]  = None
    external_url:                Optional[str]  = None
    status:                      str
    enrolled_count:              int            = 0
    created_at:                  datetime
    updated_at:                  datetime


class TrainingProgramListResponse(BaseModel):
    count:   int
    results: list[TrainingProgramResponse]


class TrainingFilterParams(BaseModel):
    status:      Optional[str]  = None
    category:    Optional[str]  = None
    is_mandatory:Optional[bool] = None
    search:      Optional[str]  = None
    page:        int            = Field(1, ge=1)
    page_size:   int            = Field(20, ge=1, le=100)


# ─── Enrollment ───────────────────────────────────────────────────────────────

class EnrollmentCreate(BaseModel):
    """Enroll one or more employees in a training program."""
    employee_ids: list[UUID] = Field(..., min_length=1)
    nominated_by: Optional[UUID] = None


class EnrollmentUpdate(BaseModel):
    status:                 Optional[str]  = None
    score:                  Optional[float]= Field(None, ge=0, le=100)
    pass_score:             Optional[float]= Field(None, ge=0, le=100)
    attendance_percentage:  Optional[float]= Field(None, ge=0, le=100)
    feedback:               Optional[str]  = None
    certificate_url:        Optional[str]  = None
    certificate_issued_at:  Optional[date] = None
    certificate_expires_at: Optional[date] = None
    completed_at:           Optional[datetime] = None


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                     str
    program_id:             str
    employee_id:            str
    employee:               Optional[EmployeeMinimal] = None
    status:                 str
    score:                  Optional[float] = None
    pass_score:             Optional[float] = None
    attendance_percentage:  Optional[float] = None
    feedback:               Optional[str]   = None
    certificate_url:        Optional[str]   = None
    certificate_issued_at:  Optional[date]  = None
    certificate_expires_at: Optional[date]  = None
    enrolled_at:            datetime
    completed_at:           Optional[datetime] = None
    nominated_by:           Optional[str]   = None
    created_at:             datetime
    updated_at:             datetime


# ─── My training (employee portal) ───────────────────────────────────────────

class MyTrainingItem(BaseModel):
    program:    TrainingProgramResponse
    enrollment: EnrollmentResponse


# ─── Stats ────────────────────────────────────────────────────────────────────

class TrainingStats(BaseModel):
    total_programs:   int
    active_programs:  int    # ongoing
    completed:        int
    total_enrollments: int
    completion_rate:  float  # pct of enrollments with status=completed
    mandatory_pending: int   # mandatory programs with registration_open/ongoing that user hasn't completed

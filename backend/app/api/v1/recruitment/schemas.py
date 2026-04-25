"""
AI-HRMS — Recruitment / ATS module Pydantic schemas.
"""

from __future__ import annotations

from datetime import date, datetime
from enum     import Enum
from typing   import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ─── Enums ────────────────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    draft   = "draft"
    open    = "open"
    closed  = "closed"
    on_hold = "on_hold"
    filled  = "filled"


class EmploymentType(str, Enum):
    full_time   = "full_time"
    part_time   = "part_time"
    contract    = "contract"
    internship  = "internship"
    remote      = "remote"


class ApplicationStatus(str, Enum):
    applied     = "applied"
    screening   = "screening"
    shortlisted = "shortlisted"
    interview   = "interview"
    offered     = "offered"
    hired       = "hired"
    rejected    = "rejected"
    withdrawn   = "withdrawn"


class ApplicationSource(str, Enum):
    portal   = "portal"
    linkedin = "linkedin"
    indeed   = "indeed"
    referral = "referral"
    direct   = "direct"
    agency   = "agency"
    campus   = "campus"
    other    = "other"


class InterviewMode(str, Enum):
    online    = "online"
    in_person = "in_person"
    phone     = "phone"


class InterviewRecommendation(str, Enum):
    proceed = "proceed"
    reject  = "reject"
    hold    = "hold"


# ─── Nested objects ───────────────────────────────────────────────────────────

class DepartmentMinimal(BaseModel):
    id:   str
    name: str
    model_config = {"from_attributes": True}


class DesignationMinimal(BaseModel):
    id:    str
    title: str
    model_config = {"from_attributes": True}


class EmployeeMinimal(BaseModel):
    id:            str
    employee_code: str
    full_name:     str
    photo_url:     Optional[str] = None
    model_config = {"from_attributes": True}


# ─── Job Posting ──────────────────────────────────────────────────────────────

class JobPostingCreate(BaseModel):
    title:                str            = Field(..., min_length=3, max_length=200)
    department_id:        Optional[str]  = None
    designation_id:       Optional[str]  = None
    location:             Optional[str]  = Field(None, max_length=200)
    description:          Optional[str]  = None
    requirements:         list[str]      = Field(default_factory=list)
    responsibilities:     list[str]      = Field(default_factory=list)
    benefits:             Optional[str]  = None
    vacancies:            int            = Field(1, ge=1, le=500)
    employment_type:      EmploymentType = EmploymentType.full_time
    experience_years_min: int            = Field(0, ge=0, le=50)
    experience_years_max: Optional[int]  = Field(None, ge=0, le=50)
    salary_range_min:     Optional[int]  = Field(None, ge=0)
    salary_range_max:     Optional[int]  = Field(None, ge=0)
    salary_visible:       bool           = False
    skills_required:      list[str]      = Field(default_factory=list)
    closing_date:         Optional[date] = None
    is_internal:          bool           = False

    @model_validator(mode="after")
    def validate_experience_range(self) -> "JobPostingCreate":
        if self.experience_years_max is not None:
            if self.experience_years_max < self.experience_years_min:
                raise ValueError("experience_years_max must be >= experience_years_min")
        return self

    @model_validator(mode="after")
    def validate_salary_range(self) -> "JobPostingCreate":
        if self.salary_range_min is not None and self.salary_range_max is not None:
            if self.salary_range_max < self.salary_range_min:
                raise ValueError("salary_range_max must be >= salary_range_min")
        return self

    @field_validator("skills_required", "requirements", "responsibilities", mode="before")
    @classmethod
    def clean_list(cls, v) -> list:
        if isinstance(v, list):
            return [str(i).strip() for i in v if str(i).strip()]
        return []


class JobPostingUpdate(BaseModel):
    title:                Optional[str]           = None
    department_id:        Optional[str]           = None
    designation_id:       Optional[str]           = None
    location:             Optional[str]           = None
    description:          Optional[str]           = None
    requirements:         Optional[list[str]]     = None
    responsibilities:     Optional[list[str]]     = None
    benefits:             Optional[str]           = None
    vacancies:            Optional[int]           = Field(None, ge=1)
    employment_type:      Optional[EmploymentType]= None
    experience_years_min: Optional[int]           = Field(None, ge=0)
    experience_years_max: Optional[int]           = Field(None, ge=0)
    salary_range_min:     Optional[int]           = Field(None, ge=0)
    salary_range_max:     Optional[int]           = Field(None, ge=0)
    salary_visible:       Optional[bool]          = None
    skills_required:      Optional[list[str]]     = None
    closing_date:         Optional[date]          = None
    is_internal:          Optional[bool]          = None


class StageCounts(BaseModel):
    applied:     int = 0
    screening:   int = 0
    shortlisted: int = 0
    interview:   int = 0
    offered:     int = 0
    hired:       int = 0
    rejected:    int = 0
    withdrawn:   int = 0


class JobPostingResponse(BaseModel):
    id:                   str
    title:                str
    location:             Optional[str]
    description:          Optional[str]
    requirements:         Optional[list]
    responsibilities:     Optional[list]
    benefits:             Optional[str]
    vacancies:            int
    employment_type:      str
    experience_years_min: int
    experience_years_max: Optional[int]
    salary_min:           Optional[int]
    salary_max:           Optional[int]
    is_salary_visible:    bool
    required_skills:      Optional[list]
    status:               str
    is_internal:          Optional[bool] = False
    posted_at:            Optional[datetime]
    closing_date:         Optional[date]
    department:           Optional[DepartmentMinimal]
    designation:          Optional[DesignationMinimal]
    application_count:    int = 0
    stage_counts:         StageCounts = Field(default_factory=StageCounts)
    created_at:           datetime
    updated_at:           datetime

    model_config = {"from_attributes": True}


class JobPostingListItem(BaseModel):
    id:               str
    title:            str
    location:         Optional[str]
    employment_type:  str
    vacancies:        int
    status:           str
    closing_date:     Optional[date]
    department_name:  Optional[str]
    application_count: int = 0
    created_at:       datetime

    model_config = {"from_attributes": True}


class JobPostingListResponse(BaseModel):
    count:   int
    results: list[JobPostingListItem]


# ─── Application ──────────────────────────────────────────────────────────────

class JobApplicationCreate(BaseModel):
    job_posting_id:          str
    candidate_name:          str  = Field(..., min_length=2, max_length=200)
    candidate_email:         str  = Field(..., min_length=5)
    candidate_phone:         Optional[str] = Field(None, max_length=20)
    candidate_location:      Optional[str] = Field(None, max_length=200)
    cv_url:                  Optional[str] = None
    cover_letter:            Optional[str] = None
    portfolio_url:           Optional[str] = None
    linkedin_url:            Optional[str] = None
    source:                  ApplicationSource = ApplicationSource.portal
    referred_by_employee_id: Optional[str] = None
    expected_salary:         Optional[int] = Field(None, ge=0)
    notice_period_days:      Optional[int] = Field(None, ge=0, le=365)


class ApplicationStageUpdate(BaseModel):
    new_status:       ApplicationStatus
    notes:            Optional[str] = Field(None, max_length=1000)
    rejection_reason: Optional[str] = Field(None, max_length=500)


class StageHistoryItem(BaseModel):
    from_status: Optional[str]
    to_status:   str
    changed_by:  Optional[str]
    notes:       Optional[str]
    changed_at:  datetime


class JobApplicationResponse(BaseModel):
    id:                str
    job_posting_id:    str
    job_posting:       Optional[JobPostingListItem]
    candidate_name:    str
    candidate_email:   str
    candidate_phone:   Optional[str]
    candidate_location: Optional[str]
    cv_url:            Optional[str]
    cover_letter:      Optional[str]
    portfolio_url:     Optional[str]
    linkedin_url:      Optional[str]
    source:            str
    referred_by:       Optional[str]
    applied_at:        datetime
    status:            str
    rejection_reason:  Optional[str]
    is_archived:       bool
    ai_score:          Optional[float]
    ai_explanation:    Optional[dict]
    ai_scored_at:      Optional[datetime]
    hr_notes:          Optional[str]
    offer_letter_url:  Optional[str]
    offer_sent_at:     Optional[datetime]
    offer_deadline:    Optional[date]
    hired_employee_id: Optional[str]
    stage_history:     list[StageHistoryItem] = []
    interviews:        list["InterviewResponse"] = []
    created_at:        datetime
    updated_at:        datetime

    model_config = {"from_attributes": True}


class JobApplicationListItem(BaseModel):
    id:              str
    job_posting_id:  str
    job_title:       Optional[str]
    candidate_name:  str
    candidate_email: str
    source:          str
    status:          str
    ai_score:        Optional[float]
    applied_at:      datetime
    created_at:      datetime

    model_config = {"from_attributes": True}


class ApplicationListResponse(BaseModel):
    count:   int
    results: list[JobApplicationListItem]


class ApplicationFilterParams(BaseModel):
    job_posting_id: Optional[str]  = None
    status:         Optional[str]  = None
    source:         Optional[str]  = None
    date_from:      Optional[date] = None
    date_to:        Optional[date] = None
    min_ai_score:   Optional[float] = Field(None, ge=0, le=100)
    search:         Optional[str]  = None
    page:           int = Field(1, ge=1)
    page_size:      int = Field(25, ge=1, le=100)


# ─── Interview ────────────────────────────────────────────────────────────────

class InterviewScheduleRequest(BaseModel):
    application_id:       str
    interviewer_ids:      list[str] = Field(..., min_length=1)
    scheduled_at:         datetime
    duration_minutes:     int = Field(60, ge=15, le=480)
    mode:                 InterviewMode = InterviewMode.online
    location_or_link:     Optional[str] = Field(None, max_length=500)
    notes_for_candidate:  Optional[str] = Field(None, max_length=1000)
    title:                Optional[str] = Field(None, max_length=200)


class InterviewFeedbackRequest(BaseModel):
    rating:         float  = Field(..., ge=1.0, le=5.0)
    feedback:       str    = Field(..., min_length=10, max_length=5000)
    recommendation: InterviewRecommendation


class InterviewResponse(BaseModel):
    id:               str
    application_id:   str
    round_number:     int
    title:            Optional[str]
    interviewer_id:   Optional[str]
    interviewer:      Optional[EmployeeMinimal]
    scheduled_at:     Optional[datetime]
    duration_minutes: int
    mode:             str
    meeting_link:     Optional[str]
    location:         Optional[str]
    status:           str
    feedback:         Optional[str]
    rating:           Optional[float]
    recommendation:   Optional[str]
    completed_at:     Optional[datetime]
    created_at:       datetime

    model_config = {"from_attributes": True}


# ─── Offer Letter ─────────────────────────────────────────────────────────────

class OfferLetterRequest(BaseModel):
    application_id:   str
    offered_salary:   int   = Field(..., ge=0)
    joining_date:     date
    offer_expiry_date: date
    additional_terms: Optional[str] = Field(None, max_length=2000)

    @model_validator(mode="after")
    def expiry_after_joining(self) -> "OfferLetterRequest":
        if self.offer_expiry_date <= self.joining_date:
            pass  # offer expiry is independent of joining
        return self


# ─── Pipeline / Kanban ────────────────────────────────────────────────────────

class PipelineColumnData(BaseModel):
    status:       str
    count:        int
    applications: list[JobApplicationListItem]


class PipelineStats(BaseModel):
    job_posting_id: str
    job_title:      str
    total:          int
    columns:        list[PipelineColumnData]


# ─── CV Upload ────────────────────────────────────────────────────────────────

class CVUploadResponse(BaseModel):
    cv_url:    str
    filename:  str
    file_size: int


# ─── AI Scoring (internal, also exposed via application) ──────────────────────

class ScoringResult(BaseModel):
    score:            float
    skills_matched:   list[str]
    skills_missing:   list[str]
    skills_score:     float
    experience_score: float
    title_relevance:  float
    education_score:  float
    explanation:      str
    bias_flags:       list[str]
    scored_at:        datetime


# ─── Public endpoints ─────────────────────────────────────────────────────────

class PublicJobPostingResponse(BaseModel):
    id:                   str
    title:                str
    location:             Optional[str]
    description:          Optional[str]
    requirements:         Optional[list]
    responsibilities:     Optional[list]
    employment_type:      str
    experience_years_min: int
    experience_years_max: Optional[int]
    salary_min:           Optional[int]
    salary_max:           Optional[int]
    is_salary_visible:    bool
    required_skills:      Optional[list]
    vacancies:            int
    closing_date:         Optional[date]
    department_name:      Optional[str]
    posted_at:            Optional[datetime]

    model_config = {"from_attributes": True}

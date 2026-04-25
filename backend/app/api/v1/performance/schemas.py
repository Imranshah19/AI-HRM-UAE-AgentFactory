"""
AI-HRMS — Performance Management Pydantic v2 schemas.
"""

from __future__ import annotations

from datetime  import date, datetime
from typing    import Any, Optional
from uuid      import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ─── Enums (string literals) ──────────────────────────────────────────────────

CycleStatus     = str   # upcoming | active | self_review | manager_review | calibration | completed | archived
AppraisalStatus = str   # not_started | self_review_pending | self_review_submitted | ...
GoalStatus      = str   # active | completed | missed | cancelled | on_hold
GoalCategory    = str   # performance | learning | behavioral | project | other
PIPStatus       = str   # active | completed | cancelled

COMPETENCIES = ("communication", "teamwork", "leadership", "problem_solving", "initiative")


# ─── Nested ───────────────────────────────────────────────────────────────────

class EmployeeMinimal(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:            str
    employee_code: str
    full_name:     str
    photo_url:     Optional[str] = None
    department:    Optional[str] = None
    designation:   Optional[str] = None


class KPIScoreEntry(BaseModel):
    goal_id:    str
    goal_title: str
    weight:     float
    self_score: Optional[float] = None
    mgr_score:  Optional[float] = None


class PIPActionItem(BaseModel):
    action:   str = Field(..., min_length=3)
    deadline: date
    metric:   str = Field(..., min_length=1)


# ─── Appraisal Cycle ──────────────────────────────────────────────────────────

class AppraisalCycleCreate(BaseModel):
    name:                         str   = Field(..., min_length=2, max_length=200)
    year:                         int   = Field(..., ge=2020, le=2099)
    quarter:                      Optional[int]  = Field(None, ge=1, le=4)
    period_label:                 Optional[str]  = Field(None, max_length=50)
    start_date:                   date
    end_date:                     date
    self_review_deadline:         Optional[date] = None
    manager_review_deadline:      Optional[date] = None
    rating_scale_min:             float = Field(1.0, ge=0)
    rating_scale_max:             float = Field(5.0, ge=1)
    self_review_instructions:     Optional[str]  = None
    manager_review_instructions:  Optional[str]  = None

    @model_validator(mode='after')
    def check_dates(self) -> 'AppraisalCycleCreate':
        if self.end_date <= self.start_date:
            raise ValueError("end_date must be after start_date")
        if self.rating_scale_max <= self.rating_scale_min:
            raise ValueError("rating_scale_max must be greater than rating_scale_min")
        return self


class AppraisalCycleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                          str
    name:                        str
    year:                        int
    quarter:                     Optional[int]  = None
    period_label:                Optional[str]  = None
    start_date:                  date
    end_date:                    date
    self_review_deadline:        Optional[date] = None
    manager_review_deadline:     Optional[date] = None
    status:                      str
    rating_scale_min:            float
    rating_scale_max:            float
    self_review_instructions:    Optional[str]  = None
    manager_review_instructions: Optional[str]  = None
    total_employees:             int            = 0
    reviews_completed:           int            = 0
    created_at:                  datetime
    updated_at:                  datetime


class AppraisalCycleListResponse(BaseModel):
    count:   int
    results: list[AppraisalCycleResponse]


# ─── Goal ─────────────────────────────────────────────────────────────────────

class GoalCreate(BaseModel):
    employee_id:   UUID
    cycle_id:      Optional[UUID] = None
    title:         str            = Field(..., min_length=2, max_length=300)
    description:   Optional[str]  = None
    category:      str            = "performance"
    target:        Optional[str]  = Field(None, max_length=500)
    target_value:  Optional[float]= None
    weight:        float          = Field(..., ge=0, le=100)
    due_date:      Optional[date] = None
    set_by:        Optional[str]  = "self"


class GoalsBulkSet(BaseModel):
    """Replace all goals for an employee+cycle atomically."""
    employee_id: UUID
    cycle_id:    UUID
    goals:       list[GoalCreate]

    @field_validator('goals')
    @classmethod
    def weights_must_sum_to_100(cls, goals: list[GoalCreate]) -> list[GoalCreate]:
        total = sum(g.weight for g in goals)
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Goal weights must sum to 100 (got {total:.1f})")
        return goals


class GoalUpdate(BaseModel):
    achievement:       Optional[str]   = None
    achievement_value: Optional[float] = None
    status:            Optional[str]   = None
    title:             Optional[str]   = None
    description:       Optional[str]   = None
    weight:            Optional[float] = Field(None, ge=0, le=100)


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                str
    employee_id:       str
    cycle_id:          Optional[str] = None
    title:             str
    description:       Optional[str]  = None
    category:          str
    target:            Optional[str]  = None
    target_value:      Optional[float]= None
    achievement:       Optional[str]  = None
    achievement_value: Optional[float]= None
    weight:            float
    due_date:          Optional[date] = None
    status:            str
    set_by:            Optional[str]  = None
    created_at:        datetime
    updated_at:        datetime


# ─── Self Review ──────────────────────────────────────────────────────────────

class SelfReviewSubmit(BaseModel):
    kpi_scores:         dict[str, float]  # goal_id → score (within scale)
    competency_scores:  dict[str, float]  # competency → score 1-5
    self_achievements:  str = Field(..., min_length=20)
    self_improvements:  str = Field(..., min_length=20)
    self_strengths:     str = Field(..., min_length=20)

    @field_validator('competency_scores')
    @classmethod
    def validate_competencies(cls, v: dict) -> dict:
        missing = set(COMPETENCIES) - set(v.keys())
        if missing:
            raise ValueError(f"Missing competency scores: {missing}")
        for key, score in v.items():
            if not (1 <= score <= 5):
                raise ValueError(f"Competency score for {key!r} must be 1–5, got {score}")
        return v


# ─── Manager Review ───────────────────────────────────────────────────────────

class ManagerReviewSubmit(BaseModel):
    kpi_scores:               dict[str, float]
    competency_scores:        dict[str, float]
    manager_feedback:         str   = Field(..., min_length=50)
    final_rating:             float
    increment_recommended:    bool  = False
    increment_percentage:     Optional[float] = Field(None, ge=0, le=100)
    promotion_recommended:    bool  = False
    promotion_to_designation: Optional[str]   = None
    pip_recommended:          bool  = False
    # Inline PIP fields — required when pip_recommended=True
    pip_improvement_areas:    list[str]       = []
    pip_action_items:         list[PIPActionItem] = []
    pip_review_date:          Optional[date]  = None

    @field_validator('competency_scores')
    @classmethod
    def validate_competencies(cls, v: dict) -> dict:
        missing = set(COMPETENCIES) - set(v.keys())
        if missing:
            raise ValueError(f"Missing competency scores: {missing}")
        return v

    @model_validator(mode='after')
    def pip_fields_required(self) -> 'ManagerReviewSubmit':
        if self.pip_recommended:
            if not self.pip_improvement_areas:
                raise ValueError("pip_improvement_areas required when pip_recommended=True")
            if not self.pip_review_date:
                raise ValueError("pip_review_date required when pip_recommended=True")
        return self


# ─── Appraisal ────────────────────────────────────────────────────────────────

class AppraisalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                       str
    cycle_id:                 str
    cycle:                    Optional[dict[str, Any]] = None
    employee_id:              str
    employee:                 Optional[EmployeeMinimal] = None
    reviewer_id:              Optional[str] = None
    reviewer:                 Optional[EmployeeMinimal] = None
    self_rating:              Optional[float] = None
    manager_rating:           Optional[float] = None
    final_rating:             Optional[float] = None
    kpi_scores:               Optional[list[KPIScoreEntry]] = None
    self_strengths:           Optional[str] = None
    self_improvements:        Optional[str] = None
    self_achievements:        Optional[str] = None
    manager_feedback:         Optional[str] = None
    hr_comments:              Optional[str] = None
    increment_recommended:    bool
    increment_percentage:     Optional[float] = None
    promotion_recommended:    bool
    promotion_to_designation: Optional[str] = None
    status:                   str
    self_submitted_at:        Optional[datetime] = None
    manager_submitted_at:     Optional[datetime] = None
    finalized_at:             Optional[datetime] = None
    employee_acknowledged:    bool
    acknowledged_at:          Optional[datetime] = None
    created_at:               datetime
    updated_at:               datetime


class AppraisalListResponse(BaseModel):
    count:   int
    results: list[AppraisalResponse]


class AppraisalFilterParams(BaseModel):
    cycle_id:    Optional[str] = None
    employee_id: Optional[str] = None
    status:      Optional[str] = None
    page:        int           = Field(1, ge=1)
    page_size:   int           = Field(20, ge=1, le=100)


# ─── PIP ─────────────────────────────────────────────────────────────────────

class PIPCreate(BaseModel):
    employee_id:       UUID
    cycle_id:          Optional[UUID] = None
    improvement_areas: list[str] = Field(..., min_length=1)
    action_items:      list[PIPActionItem] = Field(..., min_length=1)
    review_date:       date
    supervisor_id:     Optional[UUID] = None
    notes:             Optional[str]  = None


class PIPUpdate(BaseModel):
    status:            Optional[str]         = None
    notes:             Optional[str]         = None
    action_items:      Optional[list[PIPActionItem]] = None
    review_date:       Optional[date]        = None


class PIPResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id:                str
    employee_id:       str
    employee:          Optional[EmployeeMinimal] = None
    cycle_id:          Optional[str]       = None
    improvement_areas: list[str]
    action_items:      list[dict[str, Any]]
    review_date:       date
    supervisor_id:     Optional[str]       = None
    supervisor:        Optional[EmployeeMinimal] = None
    status:            str
    notes:             Optional[str]       = None
    created_at:        datetime
    updated_at:        datetime


# ─── Bell Curve ───────────────────────────────────────────────────────────────

class BellCurveBucket(BaseModel):
    rating:     float
    label:      str
    count:      int
    percentage: float
    employees:  list[EmployeeMinimal]


class BellCurveData(BaseModel):
    cycle_id:  str
    total:     int
    buckets:   list[BellCurveBucket]
    is_skewed: bool
    skew_note: Optional[str] = None


# ─── Team Summary ─────────────────────────────────────────────────────────────

class TeamMemberSummary(BaseModel):
    employee:             EmployeeMinimal
    appraisal_id:         Optional[str]   = None
    status:               Optional[str]   = None
    self_rating:          Optional[float] = None
    manager_rating:       Optional[float] = None
    final_rating:         Optional[float] = None
    self_submitted_at:    Optional[datetime] = None
    manager_submitted_at: Optional[datetime] = None


class TeamPerformanceSummary(BaseModel):
    cycle_id:   str
    cycle_name: str
    members:    list[TeamMemberSummary]
    avg_rating: Optional[float] = None
    top_count:  int = 0
    pip_count:  int = 0

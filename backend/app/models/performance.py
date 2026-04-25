"""
AI-HRMS — AppraisalCycle, Appraisal, Goal models (Performance module)
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.tenant import Tenant


# ─── ENUMs ────────────────────────────────────────────────────────────────────

CycleStatusEnum = Enum(
    "upcoming", "active", "self_review", "manager_review",
    "calibration", "completed", "archived",
    name="cycle_status_enum",
)

AppraisalStatusEnum = Enum(
    "not_started", "self_review_pending", "self_review_submitted",
    "manager_review_pending", "manager_review_submitted",
    "hr_review", "completed",
    name="appraisal_status_enum",
)

GoalStatusEnum = Enum(
    "active", "completed", "missed", "cancelled", "on_hold",
    name="goal_status_enum",
)

GoalCategoryEnum = Enum(
    "performance", "learning", "behavioral", "project", "other",
    name="goal_category_enum",
)


# ─── Appraisal Cycle ──────────────────────────────────────────────────────────

class AppraisalCycle(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A review cycle (annual, bi-annual, quarterly).
    All appraisals in a period are linked to one cycle.
    """
    __tablename__ = "appraisal_cycles"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    quarter: Mapped[int | None] = mapped_column(Integer, nullable=True)   # 1–4 or NULL for annual
    period_label: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "H1 2026"

    # Timeline
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    self_review_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    manager_review_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)

    status: Mapped[str] = mapped_column(
        CycleStatusEnum, nullable=False, server_default="upcoming", index=True,
    )

    # Rating scale (e.g. 1–5 or 1–10)
    rating_scale_min: Mapped[float] = mapped_column(Numeric(3, 1), server_default=text("1.0"), nullable=False)
    rating_scale_max: Mapped[float] = mapped_column(Numeric(3, 1), server_default=text("5.0"), nullable=False)

    # Instructions shown to employees
    self_review_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_review_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    appraisals: Mapped[list["Appraisal"]] = relationship(
        "Appraisal", back_populates="cycle", cascade="all, delete-orphan",
    )
    goals: Mapped[list["Goal"]] = relationship(
        "Goal", back_populates="cycle", lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<AppraisalCycle name={self.name!r} year={self.year!r} status={self.status!r}>"


# ─── Appraisal ────────────────────────────────────────────────────────────────

class Appraisal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual appraisal record for one employee in one cycle.
    Contains self-rating, manager rating, and final HR-calibrated rating.
    """
    __tablename__ = "appraisals"

    cycle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appraisal_cycles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── Ratings ───────────────────────────────────────────────────────────────
    self_rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    manager_rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    final_rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)

    # KPI breakdown — stores individual KPI scores as JSONB
    # e.g. [{"kpi": "Code Quality", "weight": 30, "self_score": 4, "mgr_score": 3.5}]
    kpi_scores: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # ── Qualitative Feedback ──────────────────────────────────────────────────
    self_strengths: Mapped[str | None] = mapped_column(Text, nullable=True)
    self_improvements: Mapped[str | None] = mapped_column(Text, nullable=True)
    self_achievements: Mapped[str | None] = mapped_column(Text, nullable=True)
    manager_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    hr_comments: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── AI Prediction ─────────────────────────────────────────────────────────
    predicted_rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)
    attrition_risk_score: Mapped[float | None] = mapped_column(Numeric(5, 4), nullable=True)  # 0.0–1.0
    ai_insights: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Promotion / Increment Recommendation ─────────────────────────────────
    increment_recommended: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    increment_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    promotion_recommended: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    promotion_to_designation: Mapped[str | None] = mapped_column(String(200), nullable=True)

    status: Mapped[str] = mapped_column(
        AppraisalStatusEnum, nullable=False, server_default="not_started", index=True,
    )

    # Submission timestamps
    self_submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    manager_submitted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finalized_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Whether the employee acknowledged the final review
    employee_acknowledged: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    cycle: Mapped["AppraisalCycle"] = relationship("AppraisalCycle", back_populates="appraisals")
    employee: Mapped["Employee"] = relationship(
        "Employee", foreign_keys=[employee_id], back_populates="appraisals",
    )
    reviewer: Mapped["Employee | None"] = relationship(
        "Employee", foreign_keys=[reviewer_id], lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<Appraisal cycle_id={self.cycle_id!r} "
            f"employee_id={self.employee_id!r} final_rating={self.final_rating!r}>"
        )


# ─── Goal ─────────────────────────────────────────────────────────────────────

class Goal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual performance goal linked to an employee and optionally a cycle.
    Supports OKR-style target/achievement tracking.
    """
    __tablename__ = "goals"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    cycle_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("appraisal_cycles.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(
        GoalCategoryEnum, nullable=False, server_default="performance",
    )

    # Measurable target
    target: Mapped[str | None] = mapped_column(String(500), nullable=True)     # "Complete 5 modules"
    target_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)  # Numeric target
    achievement: Mapped[str | None] = mapped_column(String(500), nullable=True)
    achievement_value: Mapped[float | None] = mapped_column(Numeric(10, 2), nullable=True)

    # Weight as % of total performance score
    weight: Mapped[float] = mapped_column(Numeric(5, 2), server_default=text("100"), nullable=False)

    due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(
        GoalStatusEnum, nullable=False, server_default="active", index=True,
    )

    # Whether the manager set this goal or the employee set it (self)
    set_by: Mapped[str | None] = mapped_column(String(10), nullable=True)   # "manager" or "self"
    is_shared: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="goals")
    cycle: Mapped["AppraisalCycle | None"] = relationship("AppraisalCycle", back_populates="goals")

    def __repr__(self) -> str:
        return f"<Goal title={self.title!r} status={self.status!r} weight={self.weight!r}>"

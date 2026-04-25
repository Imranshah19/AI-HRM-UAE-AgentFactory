"""
AI-HRMS — JobPosting, JobApplication, Interview models (ATS module)
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee, Department, Designation
    from app.models.tenant import Tenant, User


# ─── ENUMs ────────────────────────────────────────────────────────────────────

JobStatusEnum = Enum(
    "draft", "open", "closed", "on_hold", "filled",
    name="job_status_enum",
)

EmploymentTypeEnum = Enum(
    "full_time", "part_time", "contract", "internship", "remote",
    name="employment_type_enum",
)

ApplicationStatusEnum = Enum(
    "applied", "screening", "shortlisted", "interview",
    "offered", "hired", "rejected", "withdrawn",
    name="application_status_enum",
)

ApplicationSourceEnum = Enum(
    "portal", "linkedin", "indeed", "referral", "direct",
    "agency", "campus", "other",
    name="application_source_enum",
)

InterviewModeEnum = Enum(
    "online", "in_person", "phone",
    name="interview_mode_enum",
)

InterviewStatusEnum = Enum(
    "scheduled", "completed", "cancelled", "no_show", "rescheduled",
    name="interview_status_enum",
)


# ─── Job Posting ──────────────────────────────────────────────────────────────

class JobPosting(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    An open position posted by HR / Recruiter.
    Can be published to an internal portal or external job boards.
    """
    __tablename__ = "job_postings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    designation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("designations.id", ondelete="SET NULL"),
        nullable=True,
    )
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Content
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    responsibilities: Mapped[str | None] = mapped_column(Text, nullable=True)
    benefits: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Criteria
    vacancies: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    employment_type: Mapped[str] = mapped_column(
        EmploymentTypeEnum, nullable=False, server_default="full_time",
    )
    experience_years_min: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    experience_years_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_salary_visible: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)

    # AI fields — job embedding for CV matching
    embedding_vector: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    required_skills: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # ["Python", "FastAPI"]

    # Status & workflow
    status: Mapped[str] = mapped_column(
        JobStatusEnum, nullable=False, server_default="draft", index=True,
    )
    posted_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    posted_at: Mapped[datetime | None] = mapped_column(nullable=True)
    closing_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    department: Mapped["Department | None"] = relationship("Department", lazy="noload")
    designation: Mapped["Designation | None"] = relationship("Designation", lazy="noload")
    applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication", back_populates="job_posting", cascade="all, delete-orphan",
    )
    posted_by_user: Mapped["User | None"] = relationship("User", lazy="noload")

    def __repr__(self) -> str:
        return f"<JobPosting title={self.title!r} status={self.status!r}>"


# ─── Job Application ──────────────────────────────────────────────────────────

class JobApplication(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A candidate's application for a specific job posting.
    Tracks the full ATS pipeline from applied → hired/rejected.
    """
    __tablename__ = "job_applications"

    job_posting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Candidate Info ────────────────────────────────────────────────────────
    candidate_name: Mapped[str] = mapped_column(String(200), nullable=False)
    candidate_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    candidate_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    candidate_location: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # ── Documents ─────────────────────────────────────────────────────────────
    cv_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_letter: Mapped[str | None] = mapped_column(Text, nullable=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    linkedin_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── Application ───────────────────────────────────────────────────────────
    source: Mapped[str] = mapped_column(
        ApplicationSourceEnum, nullable=False, server_default="portal", index=True,
    )
    referred_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True,
    )
    applied_at: Mapped[datetime] = mapped_column(
        server_default=text("NOW()"), nullable=False, index=True,
    )

    # ── Status ────────────────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        ApplicationStatusEnum, nullable=False, server_default="applied", index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)

    # ── AI Scoring ────────────────────────────────────────────────────────────
    # Score 0–100 from the CV Shortlisting Engine
    ai_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True, index=True)
    ai_explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. {"match_reasons": [...], "gaps": [...], "skills_matched": [...], "shap_values": {...}}
    ai_scored_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # HR notes
    hr_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Offer letter
    offer_letter_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    offer_sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    offer_deadline: Mapped[date | None] = mapped_column(Date, nullable=True)

    # If hired — links to the created employee record
    hired_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True,
    )

    # Relationships
    job_posting: Mapped["JobPosting"] = relationship("JobPosting", back_populates="applications")
    interviews: Mapped[list["Interview"]] = relationship(
        "Interview", back_populates="application", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<JobApplication candidate={self.candidate_email!r} status={self.status!r}>"


# ─── Interview ────────────────────────────────────────────────────────────────

class Interview(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A scheduled interview round for a job application.
    One application may have multiple interview rounds.
    """
    __tablename__ = "interviews"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    round_number: Mapped[int] = mapped_column(Integer, server_default=text("1"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)  # "Technical Round 1"

    interviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True,
    )
    scheduled_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    scheduled_at: Mapped[datetime | None] = mapped_column(nullable=True, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, server_default=text("60"), nullable=False)
    mode: Mapped[str] = mapped_column(InterviewModeEnum, nullable=False, server_default="online")
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)

    status: Mapped[str] = mapped_column(
        InterviewStatusEnum, nullable=False, server_default="scheduled", index=True,
    )

    # Post-interview
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 1), nullable=True)  # 1.0–5.0
    recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)  # proceed / reject
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    application: Mapped["JobApplication"] = relationship("JobApplication", back_populates="interviews")
    interviewer: Mapped["Employee | None"] = relationship("Employee", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<Interview application_id={self.application_id!r} "
            f"round={self.round_number!r} status={self.status!r}>"
        )

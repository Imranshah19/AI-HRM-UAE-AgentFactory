"""
AI-HRMS — TrainingProgram, TrainingEnrollment models
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

TrainingModeEnum = Enum(
    "online", "in_person", "hybrid", "self_paced",
    name="training_mode_enum",
)

TrainingStatusEnum = Enum(
    "planned", "registration_open", "ongoing", "completed", "cancelled",
    name="training_status_enum",
)

EnrollmentStatusEnum = Enum(
    "enrolled", "in_progress", "completed", "failed", "absent", "dropped",
    name="enrollment_status_enum",
)


# ─── Training Program ─────────────────────────────────────────────────────────

class TrainingProgram(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A training course or program offered to employees.
    Includes both internal (company-run) and external programs.
    """
    __tablename__ = "training_programs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)   # Technical, Soft Skills, Compliance
    skills_covered: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # ["Python", "Leadership"]

    # Delivery
    trainer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    trainer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("employees.id", ondelete="SET NULL"), nullable=True,
    )
    mode: Mapped[str] = mapped_column(TrainingModeEnum, nullable=False, server_default="in_person")
    venue: Mapped[str | None] = mapped_column(String(300), nullable=True)
    meeting_link: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Schedule
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    duration_hours: Mapped[float | None] = mapped_column(Numeric(6, 1), nullable=True)

    # Capacity
    max_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Cost
    cost_per_participant: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), server_default="PKR", nullable=False)

    # Compliance / certification
    is_mandatory: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    issues_certificate: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    certificate_validity_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Attachments
    material_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(
        TrainingStatusEnum, nullable=False, server_default="planned", index=True,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    trainer_employee: Mapped["Employee | None"] = relationship(
        "Employee", foreign_keys=[trainer_id], lazy="noload",
    )
    enrollments: Mapped[list["TrainingEnrollment"]] = relationship(
        "TrainingEnrollment", back_populates="program", cascade="all, delete-orphan",
    )

    @property
    def enrolled_count(self) -> int:
        return len([e for e in self.enrollments if e.status not in ("dropped",)])

    def __repr__(self) -> str:
        return f"<TrainingProgram title={self.title!r} status={self.status!r}>"


# ─── Training Enrollment ──────────────────────────────────────────────────────

class TrainingEnrollment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    An employee's enrollment in a training program.
    One record per (program_id, employee_id).
    """
    __tablename__ = "training_enrollments"

    program_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("training_programs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        EnrollmentStatusEnum, nullable=False, server_default="enrolled", index=True,
    )

    # Results
    score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)        # Test/assessment score
    pass_score: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)   # Min passing score
    attendance_percentage: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)  # Employee's feedback on program

    # Certificate
    certificate_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    certificate_issued_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    certificate_expires_at: Mapped[date | None] = mapped_column(Date, nullable=True)

    enrolled_at: Mapped[datetime] = mapped_column(server_default=text("NOW()"), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Approved by (for mandatory trainings that need HR approval)
    nominated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True,
    )

    # Relationships
    program: Mapped["TrainingProgram"] = relationship("TrainingProgram", back_populates="enrollments")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="training_enrollments")

    def __repr__(self) -> str:
        return (
            f"<TrainingEnrollment program_id={self.program_id!r} "
            f"employee_id={self.employee_id!r} status={self.status!r}>"
        )

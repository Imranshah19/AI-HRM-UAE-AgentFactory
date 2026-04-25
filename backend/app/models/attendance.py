"""
AI-HRMS — Shift, AttendanceRecord, AttendanceAdjustment models
"""

import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Date, Enum, ForeignKey, Integer, Numeric,
    String, Text, Time, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ARRAY as SA_ARRAY
from sqlalchemy import String as SA_String

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.tenant import User


# ─── ENUMs ────────────────────────────────────────────────────────────────────

CheckInSourceEnum = Enum(
    "manual", "biometric", "mobile", "geo", "web",
    name="check_in_source_enum",
)

AttendanceStatusEnum = Enum(
    "present", "absent", "late", "half_day", "holiday",
    "on_leave", "work_from_home", "weekly_off",
    name="attendance_status_enum",
)

AdjustmentStatusEnum = Enum(
    "pending", "approved", "rejected",
    name="adjustment_status_enum",
)


# ─── Shift ────────────────────────────────────────────────────────────────────

class Shift(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Work shift definition. Employees are assigned to shifts.
    working_days stores day numbers 0=Monday … 6=Sunday.
    """
    __tablename__ = "shifts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    break_minutes: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("60"))
    # Array of integers: [0,1,2,3,4] = Mon-Fri
    working_days: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), nullable=False, server_default=text("'{0,1,2,3,4}'::integer[]"),
    )
    is_night_shift: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    # Grace period before marking late (in minutes)
    late_threshold_minutes: Mapped[int] = mapped_column(Integer, server_default=text("15"), nullable=False)
    # Half-day threshold (hours of work = half day)
    half_day_hours: Mapped[float] = mapped_column(Numeric(4, 2), server_default=text("4.0"), nullable=False)
    # Overtime starts after this many hours
    overtime_threshold_hours: Mapped[float] = mapped_column(Numeric(4, 2), server_default=text("8.0"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    # Relationships
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="shift", lazy="noload")
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="shift", lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Shift name={self.name!r} {self.start_time}–{self.end_time}>"


# ─── Attendance Record ────────────────────────────────────────────────────────

class AttendanceRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    One attendance record per employee per date.
    The UNIQUE constraint on (employee_id, date) enforces this.
    """
    __tablename__ = "attendance_records"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shifts.id", ondelete="SET NULL"),
        nullable=True,
    )

    # ── Check-in ──────────────────────────────────────────────────────────────
    check_in: Mapped[datetime | None] = mapped_column(nullable=True)
    check_in_source: Mapped[str | None] = mapped_column(CheckInSourceEnum, nullable=True)
    check_in_location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. {"latitude": 24.86, "longitude": 67.01, "address": "...", "accuracy_meters": 10}

    # ── Check-out ─────────────────────────────────────────────────────────────
    check_out: Mapped[datetime | None] = mapped_column(nullable=True)
    check_out_source: Mapped[str | None] = mapped_column(CheckInSourceEnum, nullable=True)
    check_out_location: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Computed Metrics ──────────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        AttendanceStatusEnum, nullable=False, server_default="absent", index=True,
    )
    working_hours: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    overtime_hours: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    late_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    early_out_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_manual_entry: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    entered_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="attendance_records")
    shift: Mapped["Shift | None"] = relationship("Shift", back_populates="attendance_records")
    adjustments: Mapped[list["AttendanceAdjustment"]] = relationship(
        "AttendanceAdjustment", back_populates="attendance_record", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AttendanceRecord employee_id={self.employee_id!r} date={self.date!r} status={self.status!r}>"


# ─── Attendance Adjustment ────────────────────────────────────────────────────

class AttendanceAdjustment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Request to correct an attendance record (e.g., employee forgot to check out).
    Requires manager/HR approval.
    """
    __tablename__ = "attendance_adjustments"

    attendance_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("attendance_records.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # What is being requested
    requested_check_in: Mapped[datetime | None] = mapped_column(nullable=True)
    requested_check_out: Mapped[datetime | None] = mapped_column(nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(
        AdjustmentStatusEnum, nullable=False, server_default="pending", index=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Relationships
    attendance_record: Mapped["AttendanceRecord"] = relationship(
        "AttendanceRecord", back_populates="adjustments",
    )

    def __repr__(self) -> str:
        return f"<AttendanceAdjustment attendance_id={self.attendance_id!r} status={self.status!r}>"

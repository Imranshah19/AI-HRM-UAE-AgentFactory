"""
AI-HRMS — LeaveType, LeaveBalance, LeaveRequest models
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.tenant import Tenant, User


# ─── ENUMs ────────────────────────────────────────────────────────────────────

LeaveStatusEnum = Enum(
    "pending", "approved", "rejected", "cancelled", "recalled",
    name="leave_status_enum",
)

LeaveGenderEnum = Enum(
    "all", "male", "female",
    name="leave_gender_enum",
)


# ─── Leave Type ───────────────────────────────────────────────────────────────

class LeaveType(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Configuration of leave types (Annual, Sick, Maternity, etc.).
    Per-tenant — each company configures their own leave policies.
    """
    __tablename__ = "leave_types"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str | None] = mapped_column(String(10), nullable=True)   # AL, SL, ML
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)   # hex colour for calendar UI

    days_allowed: Mapped[int] = mapped_column(Integer, nullable=False)
    carry_forward: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    max_carry_forward_days: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    # Policy restrictions
    applicable_gender: Mapped[str] = mapped_column(
        LeaveGenderEnum, nullable=False, server_default="all",
    )
    requires_document: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    min_service_months: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    max_consecutive_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Minimum notice required before leave starts (in days)
    advance_notice_days: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    # Can employee apply in half-day increments?
    allow_half_day: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    leave_balances: Mapped[list["LeaveBalance"]] = relationship(
        "LeaveBalance", back_populates="leave_type", lazy="noload",
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest", back_populates="leave_type", lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<LeaveType name={self.name!r} days={self.days_allowed!r}>"


# ─── Leave Balance ────────────────────────────────────────────────────────────

class LeaveBalance(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Annual leave entitlement and usage tracker per employee per leave type.
    One record per (employee_id, leave_type_id, year).
    """
    __tablename__ = "leave_balances"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leave_types.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    total_days: Mapped[float] = mapped_column(nullable=False)       # Allocated
    used_days: Mapped[float] = mapped_column(nullable=False, server_default=text("0"))
    pending_days: Mapped[float] = mapped_column(nullable=False, server_default=text("0"))  # Awaiting approval
    carried_days: Mapped[float] = mapped_column(nullable=False, server_default=text("0"))  # From previous year

    @property
    def available_days(self) -> float:
        return self.total_days + self.carried_days - self.used_days - self.pending_days

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="leave_balances")
    leave_type: Mapped["LeaveType"] = relationship("LeaveType", back_populates="leave_balances")

    def __repr__(self) -> str:
        return (
            f"<LeaveBalance employee_id={self.employee_id!r} "
            f"type={self.leave_type_id!r} year={self.year!r}>"
        )


# ─── Leave Request ────────────────────────────────────────────────────────────

class LeaveRequest(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A leave application submitted by an employee.
    Approval workflow: pending → approved/rejected → (optionally) recalled.
    """
    __tablename__ = "leave_requests"

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
    leave_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leave_types.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    start_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_days: Mapped[float] = mapped_column(nullable=False)
    is_half_day: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    # morning or afternoon for half-day leaves
    half_day_period: Mapped[str | None] = mapped_column(String(10), nullable=True)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    status: Mapped[str] = mapped_column(
        LeaveStatusEnum, nullable=False, server_default="pending", index=True,
    )

    # Approval chain
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Contact during leave
    contact_during_leave: Mapped[str | None] = mapped_column(String(20), nullable=True)
    substitute_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    employee: Mapped["Employee"] = relationship(
        "Employee",
        foreign_keys=[employee_id],
        back_populates="leave_requests",
    )
    leave_type: Mapped["LeaveType"] = relationship("LeaveType", back_populates="leave_requests")
    approved_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[approved_by], lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<LeaveRequest employee_id={self.employee_id!r} "
            f"dates={self.start_date}→{self.end_date} status={self.status!r}>"
        )


# ─── Public Holiday ───────────────────────────────────────────────────────────

class PublicHoliday(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Company / tenant-level public holidays.
    Used by leave calculations to skip non-working days.
    """
    __tablename__ = "public_holidays"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_optional: Mapped[bool] = mapped_column(
        Boolean, server_default=text("false"), nullable=False,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")

    def __repr__(self) -> str:
        return f"<PublicHoliday name={self.name!r} date={self.date!r}>"

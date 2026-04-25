"""
AI-HRMS — PayrollRun, PayrollRecord, TaxSlab models
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.tenant import Tenant, User


# ─── ENUMs ────────────────────────────────────────────────────────────────────

PayrollRunStatusEnum = Enum(
    "draft", "processing", "approved", "paid", "cancelled",
    name="payroll_run_status_enum",
)

PayrollRecordStatusEnum = Enum(
    "pending", "processed", "paid", "on_hold",
    name="payroll_record_status_enum",
)


# ─── Payroll Run ──────────────────────────────────────────────────────────────

class PayrollRun(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A monthly payroll batch. One run per (tenant, month, year).
    All individual PayrollRecords are linked to a run.
    """
    __tablename__ = "payroll_runs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    month: Mapped[int] = mapped_column(Integer, nullable=False)   # 1–12
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)  # e.g. "March 2026 Payroll"

    status: Mapped[str] = mapped_column(
        PayrollRunStatusEnum, nullable=False, server_default="draft", index=True,
    )

    # Aggregates (computed and stored for fast reporting)
    total_employees: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    total_gross: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    total_net: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    total_deductions: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    total_eobi_employee: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    total_eobi_employer: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    total_income_tax: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)

    # Workflow
    processed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    run_at: Mapped[datetime | None] = mapped_column(nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Celery task ID for async processing
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    records: Mapped[list["PayrollRecord"]] = relationship(
        "PayrollRecord", back_populates="payroll_run", cascade="all, delete-orphan",
    )
    processed_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[processed_by], lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<PayrollRun {self.year}-{self.month:02d} status={self.status!r}>"


# ─── Payroll Record ───────────────────────────────────────────────────────────

class PayrollRecord(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Individual payroll calculation for one employee in one payroll run.
    One record per (payroll_run_id, employee_id).
    """
    __tablename__ = "payroll_records"

    payroll_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("payroll_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Earnings ──────────────────────────────────────────────────────────────
    basic_salary: Mapped[int] = mapped_column(Integer, nullable=False)
    house_rent_allowance: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    medical_allowance: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    transport_allowance: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    fuel_allowance: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    other_allowances: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_allowances: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    gross_salary: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Deductions ────────────────────────────────────────────────────────────
    eobi_employee: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    eobi_employer: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    sessi: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    income_tax: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    loan_deduction: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    advance_deduction: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    # Flexible additional deductions (e.g. penalties)
    other_deductions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    total_deductions: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)

    net_salary: Mapped[int] = mapped_column(Integer, nullable=False)

    # ── Attendance Summary ────────────────────────────────────────────────────
    working_days: Mapped[int] = mapped_column(Integer, nullable=False)
    present_days: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    absent_days: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    late_days: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    overtime_hours: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)

    # Leave summary for this pay period
    paid_leave_days: Mapped[float] = mapped_column(Numeric(4, 1), server_default=text("0"), nullable=False)
    unpaid_leave_days: Mapped[float] = mapped_column(Numeric(4, 1), server_default=text("0"), nullable=False)

    # Prorated salary flag (for joiners/leavers mid-month)
    is_prorated: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)

    # ── Output ────────────────────────────────────────────────────────────────
    payslip_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        PayrollRecordStatusEnum, nullable=False, server_default="pending", index=True,
    )

    # Relationships
    payroll_run: Mapped["PayrollRun"] = relationship("PayrollRun", back_populates="records")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="payroll_records")

    def __repr__(self) -> str:
        return (
            f"<PayrollRecord run_id={self.payroll_run_id!r} "
            f"employee_id={self.employee_id!r} net={self.net_salary!r}>"
        )


# ─── Tax Slab ─────────────────────────────────────────────────────────────────

class TaxSlab(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Income tax slabs for a given fiscal year (Pakistan FBR).
    Stored in DB so HR can update them without a code deploy.
    """
    __tablename__ = "tax_slabs"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False, index=True)  # Fiscal year e.g. 2026
    min_income: Mapped[int] = mapped_column(Integer, nullable=False)         # Annual income lower bound
    max_income: Mapped[int | None] = mapped_column(Integer, nullable=True)   # NULL = no upper limit
    tax_rate: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)   # e.g. 0.2500 = 25%
    fixed_tax: Mapped[int] = mapped_column(Integer, server_default=text("0"), nullable=False)
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    def __repr__(self) -> str:
        return (
            f"<TaxSlab year={self.year!r} "
            f"range={self.min_income}–{self.max_income or '∞'} rate={self.tax_rate!r}>"
        )

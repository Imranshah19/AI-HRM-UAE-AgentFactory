"""
AI-HRMS — SalaryStructure and BankDetails models (Compensation module)
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.tenant import User


# ─── ENUMs ────────────────────────────────────────────────────────────────────

PaymentMethodEnum = Enum(
    "bank_transfer", "cash", "cheque",
    name="payment_method_enum",
)

CurrencyEnum = Enum(
    "PKR", "USD", "AED", "SAR", "GBP", "EUR", "INR", "BDT",
    name="currency_enum",
)


# ─── Salary Structure ─────────────────────────────────────────────────────────

class SalaryStructure(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    A point-in-time salary record for an employee.
    Multiple records are kept for full salary history (effective_from / effective_to).
    The active structure is the one where effective_to IS NULL.
    """
    __tablename__ = "salary_structures"

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

    currency: Mapped[str] = mapped_column(CurrencyEnum, nullable=False, server_default="PKR")

    # ── Earnings ──────────────────────────────────────────────────────────────
    basic_salary: Mapped[int] = mapped_column(nullable=False)
    house_rent_allowance: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    medical_allowance: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    transport_allowance: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    fuel_allowance: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    utility_allowance: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    # Flexible additional allowances stored as JSONB
    # e.g. {"special_allowance": 5000, "phone_allowance": 2000}
    other_allowances: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # ── Deduction flags ───────────────────────────────────────────────────────
    eobi_applicable: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    sessi_applicable: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    income_tax_applicable: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    loan_deduction: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    advance_deduction: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))

    # ── Validity Period ───────────────────────────────────────────────────────
    effective_from: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)   # NULL = currently active

    # ── Metadata ──────────────────────────────────────────────────────────────
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    revision_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="salary_structures")
    created_by_user: Mapped["User | None"] = relationship("User", lazy="noload")

    @property
    def total_allowances(self) -> int:
        fixed = (
            self.house_rent_allowance
            + self.medical_allowance
            + self.transport_allowance
            + self.fuel_allowance
            + self.utility_allowance
        )
        other = sum(self.other_allowances.values()) if self.other_allowances else 0
        return fixed + other

    @property
    def gross_salary(self) -> int:
        return self.basic_salary + self.total_allowances

    @property
    def is_active(self) -> bool:
        return self.effective_to is None

    def __repr__(self) -> str:
        return (
            f"<SalaryStructure employee_id={self.employee_id!r} "
            f"basic={self.basic_salary!r} from={self.effective_from!r}>"
        )


# ─── Bank Details ─────────────────────────────────────────────────────────────

class BankDetails(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Employee bank account for salary disbursement.
    An employee may have multiple accounts; is_primary marks the active one.
    """
    __tablename__ = "bank_details"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_title: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(30), nullable=False)
    iban: Mapped[str | None] = mapped_column(String(34), nullable=True)
    branch_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    branch_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    swift_code: Mapped[str | None] = mapped_column(String(11), nullable=True)

    payment_method: Mapped[str] = mapped_column(
        PaymentMethodEnum, nullable=False, server_default="bank_transfer",
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="bank_details")

    def __repr__(self) -> str:
        return f"<BankDetails bank={self.bank_name!r} account={self.account_number!r}>"

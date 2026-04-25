"""
AI-HRMS — Employee, Department, Designation, EmployeeDocument models
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Date, Enum, ForeignKey, String, Text,
    UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant, User
    from app.models.compensation import SalaryStructure, BankDetails
    from app.models.attendance import AttendanceRecord, Shift
    from app.models.leave import LeaveBalance, LeaveRequest
    from app.models.payroll import PayrollRecord
    from app.models.performance import Appraisal, Goal
    from app.models.training import TrainingEnrollment
    from app.models.asset import AssetAssignment
    from app.models.recruitment import JobApplication


# ─── ENUMs ────────────────────────────────────────────────────────────────────

GenderEnum = Enum(
    "male", "female", "other", "prefer_not_to_say",
    name="gender_enum",
)

MaritalStatusEnum = Enum(
    "single", "married", "divorced", "widowed",
    name="marital_status_enum",
)

ContractTypeEnum = Enum(
    "permanent", "contract", "probation", "intern", "consultant",
    name="contract_type_enum",
)

EmploymentStatusEnum = Enum(
    "active", "inactive", "terminated", "resigned", "on_leave", "suspended",
    name="employment_status_enum",
)

WorkScheduleEnum = Enum(
    "full_time", "part_time", "remote", "hybrid",
    name="work_schedule_enum",
)

DocumentTypeEnum = Enum(
    "cnic_front", "cnic_back", "passport", "degree_certificate",
    "experience_letter", "cv_resume", "offer_letter", "contract",
    "medical_certificate", "visa", "work_permit", "noc", "other",
    name="document_type_enum",
)


# ─── Department ───────────────────────────────────────────────────────────────

class Department(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Hierarchical department tree (self-referential via parent_id)."""
    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_departments_tenant_name"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Self-referential hierarchy
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Department head (set after employees exist)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    parent: Mapped["Department | None"] = relationship(
        "Department", remote_side="Department.id", foreign_keys=[parent_id], lazy="noload",
    )
    children: Mapped[list["Department"]] = relationship(
        "Department", foreign_keys=[parent_id], back_populates="parent", lazy="noload",
    )
    manager: Mapped["Employee | None"] = relationship(
        "Employee", foreign_keys=[manager_id], lazy="noload",
    )
    employees: Mapped[list["Employee"]] = relationship(
        "Employee",
        primaryjoin="Employee.department_id == Department.id",
        foreign_keys="Employee.department_id",
        back_populates="department",
        lazy="noload",
    )
    designations: Mapped[list["Designation"]] = relationship(
        "Designation", back_populates="department", lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Department name={self.name!r}>"


# ─── Designation ──────────────────────────────────────────────────────────────

class Designation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Job title / designation within a department."""
    __tablename__ = "designations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    department_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    level: Mapped[str | None] = mapped_column(String(50), nullable=True)   # L1, L2, Senior, etc.
    grade: Mapped[str | None] = mapped_column(String(20), nullable=True)
    min_salary: Mapped[int | None] = mapped_column(nullable=True)
    max_salary: Mapped[int | None] = mapped_column(nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    department: Mapped["Department | None"] = relationship("Department", back_populates="designations")
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="designation", lazy="noload")

    def __repr__(self) -> str:
        return f"<Designation name={self.name!r}>"


# ─── Employee ─────────────────────────────────────────────────────────────────

class Employee(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Core employee record. One employee may have one User account (user_id).
    Some employees (e.g. labour workers) may not have system access.
    """
    __tablename__ = "employees"
    __table_args__ = (
        UniqueConstraint("tenant_id", "employee_code", name="uq_employees_tenant_code"),
        UniqueConstraint("tenant_id", "cnic", name="uq_employees_tenant_cnic"),
        UniqueConstraint("tenant_id", "work_email", name="uq_employees_tenant_work_email"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # System account link (optional)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
    )

    # ── Identity ──────────────────────────────────────────────────────────────
    employee_code: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    middle_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    father_name: Mapped[str | None] = mapped_column(String(200), nullable=True)

    cnic: Mapped[str | None] = mapped_column(String(20), nullable=True)
    cnic_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)

    # ── Contact ───────────────────────────────────────────────────────────────
    personal_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    work_email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone_secondary: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # ── Demographics ──────────────────────────────────────────────────────────
    gender: Mapped[str | None] = mapped_column(GenderEnum, nullable=True)
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    marital_status: Mapped[str | None] = mapped_column(MaritalStatusEnum, nullable=True)
    nationality: Mapped[str | None] = mapped_column(String(100), nullable=True)
    religion: Mapped[str | None] = mapped_column(String(100), nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)

    # ── Address & Emergency Contact (JSONB for flexibility) ───────────────────
    address: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. {"line1": "...", "line2": "...", "city": "...", "state": "...", "postal_code": "...", "country": "..."}

    emergency_contact: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. {"name": "...", "relation": "...", "phone": "...", "email": "..."}

    # ── Employment ────────────────────────────────────────────────────────────
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
        index=True,
    )
    # Reporting manager (self-referential)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    branch_location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    cost_center: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    contract_type: Mapped[str] = mapped_column(
        ContractTypeEnum, nullable=False, server_default="permanent", index=True,
    )
    employment_status: Mapped[str] = mapped_column(
        EmploymentStatusEnum, nullable=False, server_default="active", index=True,
    )
    work_schedule: Mapped[str] = mapped_column(
        WorkScheduleEnum, nullable=False, server_default="full_time",
    )

    join_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    probation_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmation_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    termination_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    notice_period_days: Mapped[int] = mapped_column(nullable=False, server_default=text("30"))

    shift_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shifts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, server_default="Asia/Karachi")
    profile_photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # HR Notes (internal)
    hr_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Soft delete
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # ── Relationships ─────────────────────────────────────────────────────────
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="employees")
    user: Mapped["User | None"] = relationship("User", lazy="joined")
    department: Mapped["Department | None"] = relationship(
        "Department",
        back_populates="employees",
        foreign_keys=[department_id],
    )
    designation: Mapped["Designation | None"] = relationship(
        "Designation", back_populates="employees",
    )
    manager: Mapped["Employee | None"] = relationship(
        "Employee",
        remote_side="Employee.id",
        foreign_keys=[manager_id],
        lazy="noload",
    )
    direct_reports: Mapped[list["Employee"]] = relationship(
        "Employee",
        foreign_keys=[manager_id],
        lazy="noload",
    )
    shift: Mapped["Shift | None"] = relationship("Shift", lazy="noload")
    documents: Mapped[list["EmployeeDocument"]] = relationship(
        "EmployeeDocument", back_populates="employee", cascade="all, delete-orphan",
    )
    salary_structures: Mapped[list["SalaryStructure"]] = relationship(
        "SalaryStructure", back_populates="employee", lazy="noload",
    )
    bank_details: Mapped[list["BankDetails"]] = relationship(
        "BankDetails", back_populates="employee", lazy="noload",
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="employee", lazy="noload",
    )
    leave_balances: Mapped[list["LeaveBalance"]] = relationship(
        "LeaveBalance", back_populates="employee", lazy="noload",
    )
    leave_requests: Mapped[list["LeaveRequest"]] = relationship(
        "LeaveRequest", back_populates="employee", foreign_keys="[LeaveRequest.employee_id]", lazy="noload",
    )
    payroll_records: Mapped[list["PayrollRecord"]] = relationship(
        "PayrollRecord", back_populates="employee", lazy="noload",
    )
    appraisals: Mapped[list["Appraisal"]] = relationship(
        "Appraisal",
        primaryjoin="Appraisal.employee_id == Employee.id",
        foreign_keys="Appraisal.employee_id",
        back_populates="employee",
        lazy="noload",
    )
    goals: Mapped[list["Goal"]] = relationship(
        "Goal", back_populates="employee", lazy="noload",
    )
    training_enrollments: Mapped[list["TrainingEnrollment"]] = relationship(
        "TrainingEnrollment", back_populates="employee", lazy="noload",
    )
    asset_assignments: Mapped[list["AssetAssignment"]] = relationship(
        "AssetAssignment", back_populates="employee", lazy="noload",
    )

    @property
    def full_name(self) -> str:
        parts = [self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        parts.append(self.last_name)
        return " ".join(parts)

    def __repr__(self) -> str:
        return f"<Employee code={self.employee_code!r} name={self.full_name!r}>"


# ─── Employee Document ────────────────────────────────────────────────────────

class EmployeeDocument(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Uploaded documents attached to an employee (CNIC, passport, degree, etc.)."""
    __tablename__ = "employee_documents"

    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    doc_type: Mapped[str] = mapped_column(DocumentTypeEnum, nullable=False, index=True)
    doc_name: Mapped[str] = mapped_column(String(200), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    expiry_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    verified_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    verified_at: Mapped[datetime | None] = mapped_column(nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Soft delete — never hard-delete documents for compliance
    is_deleted: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)

    # Relationships
    employee: Mapped["Employee"] = relationship("Employee", back_populates="documents")

    def __repr__(self) -> str:
        return f"<EmployeeDocument type={self.doc_type!r} employee_id={self.employee_id!r}>"

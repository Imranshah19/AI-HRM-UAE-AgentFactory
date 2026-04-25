"""
AI-HRMS — Models Package

Import all ORM models here so that:
1. Alembic's env.py can discover all tables via Base.metadata
2. SQLAlchemy can resolve all relationships at startup
3. Application code can do: from app.models import Employee, User, ...

Import ORDER matters for SQLAlchemy relationship resolution:
base → tenant (no FKs to domain models) → employee → everything else
"""

# ── Base ─────────────────────────────────────────────────────────────────────
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin, TenantScopeMixin

# ── Core / Auth ───────────────────────────────────────────────────────────────
from app.models.tenant import (
    Tenant,
    User,
    Role,
    Permission,
    RolePermission,
    UserRole,
)

# ── Employee ──────────────────────────────────────────────────────────────────
from app.models.employee import (
    Department,
    Designation,
    Employee,
    EmployeeDocument,
)

# ── Compensation ──────────────────────────────────────────────────────────────
from app.models.compensation import (
    SalaryStructure,
    BankDetails,
)

# ── Attendance ────────────────────────────────────────────────────────────────
from app.models.attendance import (
    Shift,
    AttendanceRecord,
    AttendanceAdjustment,
)

# ── Leave ─────────────────────────────────────────────────────────────────────
from app.models.leave import (
    LeaveType,
    LeaveBalance,
    LeaveRequest,
    PublicHoliday,
)

# ── Payroll ───────────────────────────────────────────────────────────────────
from app.models.payroll import (
    PayrollRun,
    PayrollRecord,
    TaxSlab,
)

# ── Recruitment ───────────────────────────────────────────────────────────────
from app.models.recruitment import (
    JobPosting,
    JobApplication,
    Interview,
)

# ── Performance ───────────────────────────────────────────────────────────────
from app.models.performance import (
    AppraisalCycle,
    Appraisal,
    Goal,
)

# ── Training ──────────────────────────────────────────────────────────────────
from app.models.training import (
    TrainingProgram,
    TrainingEnrollment,
)

# ── Assets ────────────────────────────────────────────────────────────────────
from app.models.asset import (
    Asset,
    AssetAssignment,
)

# ── Notifications ─────────────────────────────────────────────────────────────
from app.models.notification import Notification

# ── Audit ─────────────────────────────────────────────────────────────────────
from app.models.audit import AuditLog

# ── Agent Factory ─────────────────────────────────────────────────────────────
from app.models.agent_log import AgentLog


# ── Public API ────────────────────────────────────────────────────────────────
# Explicit __all__ lets IDEs, linters, and Alembic know what's exported.

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "TenantScopeMixin",

    # Core / Auth
    "Tenant",
    "User",
    "Role",
    "Permission",
    "RolePermission",
    "UserRole",

    # Employee
    "Department",
    "Designation",
    "Employee",
    "EmployeeDocument",

    # Compensation
    "SalaryStructure",
    "BankDetails",

    # Attendance
    "Shift",
    "AttendanceRecord",
    "AttendanceAdjustment",

    # Leave
    "LeaveType",
    "LeaveBalance",
    "LeaveRequest",
    "PublicHoliday",

    # Payroll
    "PayrollRun",
    "PayrollRecord",
    "TaxSlab",

    # Recruitment
    "JobPosting",
    "JobApplication",
    "Interview",

    # Performance
    "AppraisalCycle",
    "Appraisal",
    "Goal",

    # Training
    "TrainingProgram",
    "TrainingEnrollment",

    # Assets
    "Asset",
    "AssetAssignment",

    # Notifications
    "Notification",

    # Audit
    "AuditLog",

    # Agent Factory
    "AgentLog",
]

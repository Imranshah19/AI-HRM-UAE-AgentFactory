"""
AI-HRMS — Tenant, User, Role, Permission models (Core / Auth module)
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean, Enum, ForeignKey, String, Text,
    UniqueConstraint, text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.audit import AuditLog
    from app.models.notification import Notification


# ─── ENUMs ────────────────────────────────────────────────────────────────────

TenantPlanEnum = Enum(
    "starter", "professional", "enterprise",
    name="tenant_plan_enum",
)

PermissionActionEnum = Enum(
    "create", "read", "update", "delete", "approve", "export",
    name="permission_action_enum",
)

ModuleNameEnum = Enum(
    "employee_management", "attendance", "payroll", "leave",
    "performance", "recruitment", "training", "self_service",
    "assets", "offboarding", "compliance", "notifications",
    "analytics", "mobile", "system",
    name="module_name_enum",
)


# ─── Tenant ───────────────────────────────────────────────────────────────────

class Tenant(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Top-level tenant (organisation) for multi-tenancy.
    Every data record is scoped to a tenant_id.
    """
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    plan: Mapped[str] = mapped_column(
        TenantPlanEnum, nullable=False, server_default="starter",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    # Flexible per-tenant configuration (branding, modules enabled, etc.)
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(7), nullable=True)  # e.g. #2563eb
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, server_default="Asia/Karachi")
    country: Mapped[str] = mapped_column(String(100), nullable=False, server_default="Pakistan")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="PKR")

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="tenant", lazy="noload")
    roles: Mapped[list["Role"]] = relationship("Role", back_populates="tenant", lazy="noload")
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="tenant", lazy="noload")

    def __repr__(self) -> str:
        return f"<Tenant slug={self.slug!r} plan={self.plan!r}>"


# ─── User (auth account) ──────────────────────────────────────────────────────

class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Authentication account. Every employee who can log in has a User record.
    A user always belongs to exactly one tenant.
    """
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    is_superadmin: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))

    # Profile
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, server_default="Asia/Karachi")

    # Security tracking
    last_login: Mapped[datetime | None] = mapped_column(nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(nullable=False, server_default=text("0"))
    locked_until: Mapped[datetime | None] = mapped_column(nullable=True)
    password_changed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Password reset
    reset_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reset_token_expires: Mapped[datetime | None] = mapped_column(nullable=True)

    # Refresh token (stored hashed for rotation)
    refresh_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="users")
    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan", foreign_keys="[UserRole.user_id]")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user", lazy="noload")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user", foreign_keys="[Notification.user_id]", lazy="noload")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __repr__(self) -> str:
        return f"<User email={self.email!r} tenant_id={self.tenant_id!r}>"


# ─── Role ─────────────────────────────────────────────────────────────────────

class Role(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    RBAC Role. System roles (is_system_role=True) are pre-seeded and cannot
    be deleted. Tenants can also create custom roles.
    """
    __tablename__ = "roles"
    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_roles_tenant_name"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system_role: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    # JSON config for UI-level restrictions
    ui_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", back_populates="roles")
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan",
    )
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole", back_populates="role", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Role name={self.name!r}>"


# ─── Permission ───────────────────────────────────────────────────────────────

class Permission(Base, UUIDPrimaryKeyMixin):
    """
    Atomic permission entry. Seeded at startup; not tenant-specific.
    e.g. module_name=payroll, action=approve
    """
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("module_name", "action", name="uq_permissions_module_action"),
    )

    module_name: Mapped[str] = mapped_column(ModuleNameEnum, nullable=False, index=True)
    action: Mapped[str] = mapped_column(PermissionActionEnum, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="permission",
    )

    def __repr__(self) -> str:
        return f"<Permission {self.module_name}.{self.action}>"


# ─── Role ↔ Permission (many-to-many) ────────────────────────────────────────

class RolePermission(Base):
    """Junction table between Role and Permission."""
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    permission_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    )
    granted_at: Mapped[datetime] = mapped_column(
        server_default=text("NOW()"), nullable=False,
    )

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship("Permission", back_populates="role_permissions")


# ─── User ↔ Role (many-to-many) ───────────────────────────────────────────────

class UserRole(Base):
    """Junction table between User and Role."""
    __tablename__ = "user_roles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    assigned_at: Mapped[datetime] = mapped_column(
        server_default=text("NOW()"), nullable=False,
    )
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    user: Mapped["User"] = relationship("User", back_populates="user_roles", foreign_keys=[user_id])
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")

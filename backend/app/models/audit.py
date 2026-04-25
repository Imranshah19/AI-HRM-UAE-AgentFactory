"""
AI-HRMS — AuditLog model
Immutable audit trail of every data change in the system.
Records are NEVER updated or deleted — insert-only by design.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant, User


# ─── AuditLog ─────────────────────────────────────────────────────────────────

class AuditLog(Base, UUIDPrimaryKeyMixin):
    """
    Immutable audit log. One record per data mutation.

    Design notes:
    - No updated_at — records are write-once.
    - old_values / new_values store the full before/after JSON snapshot.
    - ip_address and user_agent are logged for security investigations.
    - Indexed heavily for fast filtering by tenant, user, resource, and date.

    Compliance:
    - GDPR: on right-to-erasure requests, anonymise user_id but keep the log.
    - Retention: configure a pg_partman partition strategy for this table
      to auto-drop records older than your retention policy.
    """
    __tablename__ = "audit_logs"

    # Tenant scope
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Actor — who performed the action (NULL for system-triggered events)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    # Denormalise actor email so it survives user deletion
    user_email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # What happened
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # e.g. "create", "update", "delete", "login", "logout", "export",
    #       "approve", "reject", "password_reset"

    # What was affected
    resource: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # e.g. "employee", "payroll_run", "leave_request"
    resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True,
    )
    resource_label: Mapped[str | None] = mapped_column(String(300), nullable=True)
    # Human-readable label e.g. "Ahmed Khan (EMP-001)"

    # Before / after snapshot (NULL for creates and deletes respectively)
    old_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Changed fields list for quick diffing (avoids parsing full JSONB)
    changed_fields: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    # Request context
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True, index=True)   # IPv4 or IPv6
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)  # X-Request-ID
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Timestamp — indexed for time-range queries
    created_at: Mapped[datetime] = mapped_column(
        server_default=text("NOW()"),
        nullable=False,
        index=True,
    )

    # Additional context (module-specific data)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    user: Mapped["User | None"] = relationship("User", back_populates="audit_logs", lazy="noload")

    def __repr__(self) -> str:
        return (
            f"<AuditLog action={self.action!r} resource={self.resource!r}"
            f" resource_id={self.resource_id!r} user={self.user_email!r}>"
        )

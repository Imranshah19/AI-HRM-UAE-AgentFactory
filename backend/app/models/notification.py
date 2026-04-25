"""
AI-HRMS — Notification model
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.tenant import Tenant, User


# ─── ENUMs ────────────────────────────────────────────────────────────────────

NotificationTypeEnum = Enum(
    "info", "success", "warning", "error",
    name="notification_type_enum",
)

NotificationChannelEnum = Enum(
    "in_app", "email", "sms", "push", "whatsapp",
    name="notification_channel_enum",
)

NotificationCategoryEnum = Enum(
    "leave", "attendance", "payroll", "performance", "recruitment",
    "training", "asset", "onboarding", "offboarding", "compliance",
    "system", "general",
    name="notification_category_enum",
)


# ─── Notification ─────────────────────────────────────────────────────────────

class Notification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    In-app and push notification records.
    One record per recipient per event. Batch processing via Celery.
    """
    __tablename__ = "notifications"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Recipient user
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(
        NotificationTypeEnum, nullable=False, server_default="info",
    )
    category: Mapped[str] = mapped_column(
        NotificationCategoryEnum, nullable=False, server_default="general", index=True,
    )
    channel: Mapped[str] = mapped_column(
        NotificationChannelEnum, nullable=False, server_default="in_app",
    )

    # Deep-link into the app
    action_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    action_label: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Related resource (for context)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Additional payload for rich notifications (e.g. push notification data)
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False, index=True)
    read_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Delivery (for non-in-app channels)
    is_sent: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(nullable=True)
    delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(server_default=text("0"), nullable=False)

    # Expiry
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Sender (NULL = system-generated)
    sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    sender: Mapped["User | None"] = relationship("User", foreign_keys=[sender_id], lazy="noload")

    def __repr__(self) -> str:
        return f"<Notification user_id={self.user_id!r} title={self.title!r} read={self.is_read!r}>"

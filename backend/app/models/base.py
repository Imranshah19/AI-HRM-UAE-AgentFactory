"""
AI-HRMS — SQLAlchemy Declarative Base & Shared Mixins
All models import Base from here. Never instantiate Base directly.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.
    Provides type_annotation_map for clean Mapped[] annotations.
    """
    type_annotation_map: dict[type, Any] = {
        uuid.UUID: UUID(as_uuid=True),
        datetime: DateTime(timezone=True),
    }


class TimestampMixin:
    """
    Adds created_at and updated_at to any model.
    updated_at is automatically refreshed on every UPDATE via server_onupdate.
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class UUIDPrimaryKeyMixin:
    """UUID primary key using PostgreSQL gen_random_uuid()."""
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        index=True,
    )


class TenantScopeMixin(UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Combines UUID PK + timestamps. Use as base for tenant-scoped models.
    The tenant_id FK is defined in each model individually so that
    SQLAlchemy can order table creation correctly.
    """
    pass

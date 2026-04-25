"""
AI-HRMS — Asset, AssetAssignment models
"""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, Numeric, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.employee import Employee
    from app.models.tenant import Tenant, User


# ─── ENUMs ────────────────────────────────────────────────────────────────────

AssetConditionEnum = Enum(
    "excellent", "good", "fair", "poor", "damaged",
    name="asset_condition_enum",
)

AssetStatusEnum = Enum(
    "available", "assigned", "maintenance", "retired", "lost", "disposed",
    name="asset_status_enum",
)

AssetCategoryEnum = Enum(
    "laptop", "desktop", "mobile", "tablet", "monitor", "keyboard",
    "mouse", "headset", "sim_card", "access_card", "vehicle",
    "furniture", "other",
    name="asset_category_enum",
)


# ─── Asset ────────────────────────────────────────────────────────────────────

class Asset(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    IT and office asset inventory.
    Assets are tracked from purchase → assignment → return → retirement.
    """
    __tablename__ = "assets"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Identification ────────────────────────────────────────────────────────
    asset_tag: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(AssetCategoryEnum, nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model: Mapped[str | None] = mapped_column(String(200), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    specifications: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # e.g. {"ram_gb": 16, "storage_gb": 512, "processor": "Intel i7", "os": "Windows 11"}

    # ── Financial ─────────────────────────────────────────────────────────────
    purchase_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    purchase_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    currency: Mapped[str] = mapped_column(String(3), server_default="PKR", nullable=False)
    vendor: Mapped[str | None] = mapped_column(String(200), nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    warranty_expiry: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)

    # ── Status ────────────────────────────────────────────────────────────────
    condition: Mapped[str] = mapped_column(AssetConditionEnum, nullable=False, server_default="good")
    status: Mapped[str] = mapped_column(AssetStatusEnum, nullable=False, server_default="available", index=True)

    location: Mapped[str | None] = mapped_column(String(200), nullable=True)   # Storage location
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Current assignee (denormalised from AssetAssignment for quick lookup)
    current_employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    assigned_since: Mapped[date | None] = mapped_column(Date, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship("Tenant", lazy="noload")
    current_employee: Mapped["Employee | None"] = relationship(
        "Employee", foreign_keys=[current_employee_id], lazy="noload",
    )
    assignments: Mapped[list["AssetAssignment"]] = relationship(
        "AssetAssignment", back_populates="asset", cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Asset tag={self.asset_tag!r} name={self.name!r} status={self.status!r}>"


# ─── Asset Assignment ─────────────────────────────────────────────────────────

class AssetAssignment(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    History of asset assignments to employees.
    A new record is created each time an asset is assigned or returned.
    """
    __tablename__ = "asset_assignments"

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Assignment
    assigned_at: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )
    condition_at_assignment: Mapped[str] = mapped_column(
        AssetConditionEnum, nullable=False, server_default="good",
    )
    assignment_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    handover_document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    employee_acknowledged: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(nullable=True)

    # Return
    returned_at: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    condition_at_return: Mapped[str | None] = mapped_column(AssetConditionEnum, nullable=True)
    return_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    return_document_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    received_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
    )

    # Damage/loss
    is_damaged: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    damage_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    damage_cost: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    asset: Mapped["Asset"] = relationship("Asset", back_populates="assignments")
    employee: Mapped["Employee"] = relationship("Employee", back_populates="asset_assignments")
    assigned_by_user: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_by], lazy="noload",
    )

    @property
    def is_active(self) -> bool:
        return self.returned_at is None

    def __repr__(self) -> str:
        return (
            f"<AssetAssignment asset_id={self.asset_id!r} "
            f"employee_id={self.employee_id!r} active={self.is_active!r}>"
        )

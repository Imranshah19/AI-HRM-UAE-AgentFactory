"""
AI-HRMS — Asset Management service layer.
All DB operations are tenant-scoped; every function receives tenant_id explicitly.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing   import Optional
from uuid     import UUID

from fastapi              import HTTPException
from sqlalchemy           import and_, func, or_, select, update
from sqlalchemy.orm       import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset    import Asset, AssetAssignment
from app.models.employee import Employee

from app.api.v1.assets.schemas import (
    AssetAssignmentRequest,
    AssetCreate,
    AssetFilterParams,
    AssetReturnRequest,
    AssetUpdate,
)

logger = logging.getLogger(__name__)


def _str(v) -> str | None:
    return str(v) if v is not None else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Asset tag generation ─────────────────────────────────────────────────────

async def _next_asset_tag(tenant_id: UUID, db: AsyncSession) -> str:
    """Generate next sequential asset tag: AST-0001, AST-0002, …"""
    count = (await db.execute(
        select(func.count(Asset.id)).where(Asset.tenant_id == tenant_id)
    )).scalar_one()
    return f"AST-{(count + 1):04d}"


# ─── CRUD ─────────────────────────────────────────────────────────────────────

async def create_asset(
    tenant_id:  UUID,
    data:       AssetCreate,
    created_by: UUID,
    db:         AsyncSession,
) -> Asset:
    tag = data.asset_tag or await _next_asset_tag(tenant_id, db)

    # Ensure tag unique within tenant
    existing = (await db.execute(
        select(Asset).where(Asset.tenant_id == tenant_id, Asset.asset_tag == tag)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, f"Asset tag '{tag}' already exists")

    asset = Asset(
        tenant_id      = tenant_id,
        asset_tag      = tag,
        name           = data.name,
        category       = data.category,
        brand          = data.brand,
        model          = data.model,
        serial_number  = data.serial_number,
        specifications = data.specifications,
        purchase_date  = data.purchase_date,
        purchase_cost  = data.purchase_cost,
        current_value  = data.current_value,
        currency       = data.currency,
        vendor         = data.vendor,
        invoice_number = data.invoice_number,
        warranty_expiry= data.warranty_expiry,
        condition      = data.condition,
        status         = "available",
        location       = data.location,
        notes          = data.notes,
        is_active      = True,
    )
    db.add(asset)
    await db.commit()
    await db.refresh(asset)
    return asset


async def get_assets(
    tenant_id: UUID,
    filters:   AssetFilterParams,
    db:        AsyncSession,
) -> tuple[int, list[Asset]]:
    q = (
        select(Asset)
        .options(selectinload(Asset.current_employee))
        .where(Asset.tenant_id == tenant_id, Asset.is_active == True)
    )

    if filters.category:
        q = q.where(Asset.category == filters.category)
    if filters.status:
        q = q.where(Asset.status == filters.status)
    if filters.assigned is not None:
        if filters.assigned:
            q = q.where(Asset.status == "assigned")
        else:
            q = q.where(Asset.status != "assigned")
    if filters.search:
        term = f"%{filters.search}%"
        q = q.where(
            or_(
                Asset.name.ilike(term),
                Asset.asset_tag.ilike(term),
                Asset.serial_number.ilike(term),
                Asset.brand.ilike(term),
            )
        )

    q = q.order_by(Asset.created_at.desc())

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    offset = (filters.page - 1) * filters.page_size
    rows   = (await db.execute(q.offset(offset).limit(filters.page_size))).scalars().all()
    return total, list(rows)


async def get_asset(tenant_id: UUID, asset_id: UUID, db: AsyncSession) -> Asset:
    row = (await db.execute(
        select(Asset)
        .options(
            selectinload(Asset.current_employee),
            selectinload(Asset.assignments).selectinload(AssetAssignment.employee),
        )
        .where(Asset.id == asset_id, Asset.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Asset not found")
    return row


async def update_asset(
    tenant_id: UUID,
    asset_id:  UUID,
    data:      AssetUpdate,
    db:        AsyncSession,
) -> Asset:
    asset = await get_asset(tenant_id, asset_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(asset, field, value)
    await db.commit()
    await db.refresh(asset)
    return asset


# ─── Assignment ───────────────────────────────────────────────────────────────

async def assign_asset(
    tenant_id:   UUID,
    asset_id:    UUID,
    data:        AssetAssignmentRequest,
    assigned_by: UUID,
    db:          AsyncSession,
) -> AssetAssignment:
    asset = await get_asset(tenant_id, asset_id, db)

    if asset.status == "assigned":
        raise HTTPException(409, "Asset is already assigned. Return it first.")
    if asset.status not in ("available",):
        raise HTTPException(400, f"Asset cannot be assigned — current status: {asset.status}")

    # Verify employee belongs to tenant
    emp = (await db.execute(
        select(Employee).where(
            Employee.id == data.employee_id,
            Employee.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "Employee not found")

    assignment = AssetAssignment(
        asset_id                = asset_id,
        employee_id             = data.employee_id,
        assigned_at             = date.today(),
        assigned_by             = assigned_by,
        condition_at_assignment = data.condition_at_assignment,
        assignment_notes        = data.notes,
    )
    db.add(assignment)

    # Update denormalised fields on asset
    asset.status              = "assigned"
    asset.current_employee_id = data.employee_id
    asset.assigned_since      = date.today()

    await db.commit()
    await db.refresh(assignment)
    return assignment


async def return_asset(
    tenant_id:     UUID,
    assignment_id: UUID,
    data:          AssetReturnRequest,
    received_by:   UUID,
    db:            AsyncSession,
) -> AssetAssignment:
    assignment = (await db.execute(
        select(AssetAssignment)
        .options(selectinload(AssetAssignment.asset))
        .where(AssetAssignment.id == assignment_id)
    )).scalar_one_or_none()
    if not assignment:
        raise HTTPException(404, "Assignment not found")
    if str(assignment.asset.tenant_id) != str(tenant_id):
        raise HTTPException(403, "Access denied")
    if assignment.returned_at is not None:
        raise HTTPException(400, "Asset already returned")

    assignment.returned_at         = date.today()
    assignment.condition_at_return = data.condition_at_return
    assignment.return_notes        = data.notes
    assignment.is_damaged          = data.is_damaged
    assignment.damage_description  = data.damage_description
    assignment.damage_cost         = data.damage_cost
    assignment.received_by         = received_by

    # Update asset status
    asset = assignment.asset
    asset.status              = "available"
    asset.condition           = data.condition_at_return
    asset.current_employee_id = None
    asset.assigned_since      = None

    await db.commit()
    await db.refresh(assignment)
    return assignment


async def get_employee_assets(
    tenant_id:   UUID,
    employee_id: UUID,
    db:          AsyncSession,
) -> list[Asset]:
    """All currently assigned (active) assets for an employee."""
    rows = (await db.execute(
        select(Asset)
        .where(
            Asset.tenant_id          == tenant_id,
            Asset.current_employee_id == employee_id,
            Asset.status              == "assigned",
        )
        .order_by(Asset.assigned_since.desc())
    )).scalars().all()
    return list(rows)


async def trigger_return_on_offboarding(
    tenant_id:   UUID,
    employee_id: UUID,
    db:          AsyncSession,
) -> list[Asset]:
    """Mark all employee's assets as 'return pending' (maintenance status) on offboarding."""
    assets = await get_employee_assets(tenant_id, employee_id, db)

    for asset in assets:
        asset.status = "maintenance"   # signals return pending
        asset.notes  = (asset.notes or "") + "\n[OFFBOARDING] Return pending."

    if assets:
        await db.commit()

        # Best-effort notification to IT admin
        try:
            from app.models.tenant import User
            from app.models.notification import Notification
            it_users = (await db.execute(
                select(User).where(User.tenant_id == tenant_id, User.is_active == True)
            )).scalars().all()
            emp = (await db.execute(
                select(Employee).where(Employee.id == employee_id)
            )).scalar_one_or_none()
            emp_name = f"{emp.first_name} {emp.last_name}" if emp else str(employee_id)

            for user in it_users[:5]:   # notify first 5 admins
                notif = Notification(
                    tenant_id  = tenant_id,
                    user_id    = user.id,
                    title      = "Asset Return Required",
                    message    = f"{emp_name} is offboarding. {len(assets)} asset(s) pending return.",
                    type       = "warning",
                    category   = "asset",
                    action_url = f"/assets?assigned=true&employee_id={employee_id}",
                )
                db.add(notif)
            await db.commit()
        except Exception:
            pass

    return assets


async def get_asset_history(
    tenant_id: UUID,
    asset_id:  UUID,
    db:        AsyncSession,
) -> list[AssetAssignment]:
    asset = (await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Asset not found")

    rows = (await db.execute(
        select(AssetAssignment)
        .options(selectinload(AssetAssignment.employee))
        .where(AssetAssignment.asset_id == asset_id)
        .order_by(AssetAssignment.assigned_at.desc())
    )).scalars().all()
    return list(rows)

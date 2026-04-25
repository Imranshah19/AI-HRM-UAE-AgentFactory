"""
AI-HRMS — Asset Management router.

GET    /assets                           → list (paginated, filterable)
POST   /assets                           → create  (HR/IT only)
GET    /assets/{id}                      → detail + assignment history
PATCH  /assets/{id}                     → update  (HR/IT only)
POST   /assets/{id}/assign               → assign to employee
POST   /assets/{id}/return               → return from employee
GET    /assets/employee/{employee_id}    → all active assets for employee
"""

from __future__ import annotations

from typing import Annotated, Optional
from uuid   import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.models        import Employee
from app.models.tenant import User

from app.api.v1.assets import service
from app.api.v1.assets.schemas import (
    AssetAssignmentRequest,
    AssetAssignmentResponse,
    AssetCreate,
    AssetFilterParams,
    AssetListResponse,
    AssetResponse,
    AssetReturnRequest,
    AssetUpdate,
)

router = APIRouter(prefix="/assets", tags=["Assets"])


async def _get_employee(user: User, db: AsyncSession) -> Employee | None:
    return (await db.execute(
        select(Employee).where(
            Employee.user_id   == user.id,
            Employee.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()


# ─── List & Create ────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=AssetListResponse,
    summary="List assets (filterable by category, status, assigned)",
)
async def list_assets(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    category:     Optional[str]  = Query(None),
    status_filter:Optional[str]  = Query(None, alias="status"),
    assigned:     Optional[bool] = Query(None),
    search:       Optional[str]  = Query(None),
    page:         int = Query(1,  ge=1),
    page_size:    int = Query(20, ge=1, le=100),
):
    filters = AssetFilterParams(
        category  = category,
        status    = status_filter,
        assigned  = assigned,
        search    = search,
        page      = page,
        page_size = page_size,
    )
    total, assets = await service.get_assets(current_user.tenant_id, filters, db)
    return AssetListResponse(count=total, results=assets)


@router.post(
    "",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an asset (HR/IT only)",
)
async def create_asset(
    body:         AssetCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("assets", "write"),
):
    emp = await _get_employee(current_user, db)
    created_by = emp.id if emp else current_user.id
    return await service.create_asset(current_user.tenant_id, body, created_by, db)


# ─── Employee-specific ────────────────────────────────────────────────────────

@router.get(
    "/employee/{employee_id}",
    response_model=list[AssetResponse],
    summary="Get all active assets assigned to an employee",
)
async def employee_assets(
    employee_id:  UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.get_employee_assets(current_user.tenant_id, employee_id, db)


# ─── Detail, Update, Assign, Return ──────────────────────────────────────────

@router.get(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Get asset detail with assignment history",
)
async def get_asset(
    asset_id:     UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.get_asset(current_user.tenant_id, asset_id, db)


@router.patch(
    "/{asset_id}",
    response_model=AssetResponse,
    summary="Update asset details (HR/IT only)",
)
async def update_asset(
    asset_id:     UUID,
    body:         AssetUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("assets", "write"),
):
    return await service.update_asset(current_user.tenant_id, asset_id, body, db)


@router.post(
    "/{asset_id}/assign",
    response_model=AssetAssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign asset to an employee",
)
async def assign_asset(
    asset_id:     UUID,
    body:         AssetAssignmentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("assets", "write"),
):
    emp = await _get_employee(current_user, db)
    assigned_by = emp.id if emp else current_user.id
    return await service.assign_asset(
        current_user.tenant_id, asset_id, body, assigned_by, db
    )


@router.post(
    "/{asset_id}/return",
    response_model=AssetAssignmentResponse,
    summary="Record return of an assigned asset",
)
async def return_asset(
    asset_id:     UUID,
    body:         AssetReturnRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    received_by = emp.id if emp else current_user.id

    # Find the active assignment
    from app.models.asset import Asset, AssetAssignment
    asset = await service.get_asset(current_user.tenant_id, asset_id, db)
    if asset.status != "assigned":
        from fastapi import HTTPException
        raise HTTPException(400, "Asset is not currently assigned")

    # Get the open assignment record
    from sqlalchemy import select as sa_select
    assignment = (await db.execute(
        sa_select(AssetAssignment).where(
            AssetAssignment.asset_id    == asset_id,
            AssetAssignment.returned_at == None,
        )
    )).scalar_one_or_none()
    if not assignment:
        from fastapi import HTTPException
        raise HTTPException(404, "Active assignment not found")

    return await service.return_asset(
        current_user.tenant_id, assignment.id, body, received_by, db
    )


@router.get(
    "/{asset_id}/history",
    response_model=list[AssetAssignmentResponse],
    summary="Full assignment history for an asset",
)
async def asset_history(
    asset_id:     UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.get_asset_history(current_user.tenant_id, asset_id, db)

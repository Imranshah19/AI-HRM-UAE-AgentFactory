"""
AI-HRMS — Designations router.
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.v1.designations.schemas import (
    DesignationCreate,
    DesignationResponse,
    DesignationUpdate,
)
from app.core.dependencies import DbDep, TenantIdDep, require_permission
from app.models.employee import Designation

router = APIRouter(prefix="/designations", tags=["Designations"])


@router.get(
    "",
    response_model=list[DesignationResponse],
    summary="List designations",
    dependencies=[require_permission("employee_management", "read")],
)
async def list_designations(
    tenant_id:     TenantIdDep,
    db:            DbDep,
    department_id: uuid.UUID | None = None,
    active_only:   bool = True,
):
    stmt = select(Designation).where(Designation.tenant_id == tenant_id)
    if active_only:
        stmt = stmt.where(Designation.is_active.is_(True))
    if department_id:
        stmt = stmt.where(Designation.department_id == department_id)
    stmt = stmt.order_by(Designation.name)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "",
    response_model=DesignationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create designation",
    dependencies=[require_permission("employee_management", "create")],
)
async def create_designation(
    tenant_id: TenantIdDep,
    db:        DbDep,
    data:      DesignationCreate,
):
    designation = Designation(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=data.name,
        department_id=data.department_id,
        level=data.level,
        grade=data.grade,
        min_salary=data.min_salary,
        max_salary=data.max_salary,
        is_active=True,
    )
    db.add(designation)
    await db.flush()
    return designation


@router.patch(
    "/{designation_id}",
    response_model=DesignationResponse,
    summary="Update designation",
    dependencies=[require_permission("employee_management", "update")],
)
async def update_designation(
    designation_id: uuid.UUID,
    tenant_id:      TenantIdDep,
    db:             DbDep,
    data:           DesignationUpdate,
):
    result = await db.execute(
        select(Designation).where(
            Designation.id == designation_id,
            Designation.tenant_id == tenant_id,
        )
    )
    designation = result.scalar_one_or_none()
    if designation is None:
        raise HTTPException(status_code=404, detail="Designation not found.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(designation, field, value)
    db.add(designation)
    await db.flush()
    return designation


@router.delete(
    "/{designation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate designation",
    dependencies=[require_permission("employee_management", "delete")],
)
async def delete_designation(
    designation_id: uuid.UUID,
    tenant_id:      TenantIdDep,
    db:             DbDep,
):
    result = await db.execute(
        select(Designation).where(
            Designation.id == designation_id,
            Designation.tenant_id == tenant_id,
        )
    )
    designation = result.scalar_one_or_none()
    if designation is None:
        raise HTTPException(status_code=404, detail="Designation not found.")

    # Check no active employees assigned
    from sqlalchemy import func
    from app.models.employee import Employee
    count_result = await db.execute(
        select(func.count(Employee.id)).where(
            Employee.designation_id == designation_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == "active",
        )
    )
    if (count_result.scalar_one() or 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot deactivate: active employees are assigned to this designation.",
        )

    designation.is_active = False
    db.add(designation)

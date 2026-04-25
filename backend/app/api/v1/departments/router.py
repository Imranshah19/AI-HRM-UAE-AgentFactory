"""
AI-HRMS — Departments router.
"""

import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.v1.departments.schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdate,
)
from app.core.dependencies import CurrentUser, DbDep, TenantIdDep, require_permission
from app.models.employee import Department, Employee

router = APIRouter(prefix="/departments", tags=["Departments"])


# ─── List ──────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=list[DepartmentResponse],
    summary="List departments",
    dependencies=[require_permission("employee_management", "read")],
)
async def list_departments(
    tenant_id:  TenantIdDep,
    db:         DbDep,
    active_only: bool = True,
):
    stmt = select(Department).where(Department.tenant_id == tenant_id)
    if active_only:
        stmt = stmt.where(Department.is_active.is_(True))
    stmt = stmt.order_by(Department.name)

    result = await db.execute(stmt)
    departments = list(result.scalars().all())

    # Employee count per department (single query)
    count_result = await db.execute(
        select(Employee.department_id, func.count(Employee.id))
        .where(
            Employee.tenant_id == tenant_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == "active",
        )
        .group_by(Employee.department_id)
    )
    count_map: dict[uuid.UUID, int] = {row[0]: row[1] for row in count_result.fetchall()}

    return [
        DepartmentResponse(
            id=d.id,
            name=d.name,
            code=d.code,
            description=d.description,
            parent_id=d.parent_id,
            is_active=d.is_active,
            employee_count=count_map.get(d.id, 0),
        )
        for d in departments
    ]


# ─── Create ────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create department",
    dependencies=[require_permission("employee_management", "create")],
)
async def create_department(
    tenant_id: TenantIdDep,
    db:        DbDep,
    data:      DepartmentCreate,
):
    # Uniqueness check
    existing = await db.execute(
        select(Department.id).where(
            Department.tenant_id == tenant_id,
            Department.name == data.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Department '{data.name}' already exists.",
        )

    dept = Department(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=data.name,
        code=data.code,
        description=data.description,
        parent_id=data.parent_id,
        is_active=True,
    )
    db.add(dept)
    await db.flush()

    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        description=dept.description,
        parent_id=dept.parent_id,
        is_active=dept.is_active,
        employee_count=0,
    )


# ─── Update ────────────────────────────────────────────────────────────────────

@router.patch(
    "/{department_id}",
    response_model=DepartmentResponse,
    summary="Update department",
    dependencies=[require_permission("employee_management", "update")],
)
async def update_department(
    department_id: uuid.UUID,
    tenant_id:     TenantIdDep,
    db:            DbDep,
    data:          DepartmentUpdate,
):
    result = await db.execute(
        select(Department).where(
            Department.id == department_id,
            Department.tenant_id == tenant_id,
        )
    )
    dept = result.scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(dept, field, value)
    db.add(dept)
    await db.flush()

    count_result = await db.execute(
        select(func.count(Employee.id)).where(
            Employee.department_id == dept.id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == "active",
        )
    )
    count = count_result.scalar_one() or 0

    return DepartmentResponse(
        id=dept.id,
        name=dept.name,
        code=dept.code,
        description=dept.description,
        parent_id=dept.parent_id,
        is_active=dept.is_active,
        employee_count=count,
    )


# ─── Delete (soft) ─────────────────────────────────────────────────────────────

@router.delete(
    "/{department_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate department",
    dependencies=[require_permission("employee_management", "delete")],
)
async def delete_department(
    department_id: uuid.UUID,
    tenant_id:     TenantIdDep,
    db:            DbDep,
):
    result = await db.execute(
        select(Department).where(
            Department.id == department_id,
            Department.tenant_id == tenant_id,
        )
    )
    dept = result.scalar_one_or_none()
    if dept is None:
        raise HTTPException(status_code=404, detail="Department not found.")

    # Block if active employees are assigned
    count_result = await db.execute(
        select(func.count(Employee.id)).where(
            Employee.department_id == department_id,
            Employee.is_deleted.is_(False),
            Employee.employment_status == "active",
        )
    )
    active_count: int = count_result.scalar_one() or 0
    if active_count > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot deactivate: {active_count} active employee(s) are assigned to this department.",
        )

    dept.is_active = False
    db.add(dept)

"""
AI-HRMS — Employee router.

All routes:
- require authentication (CurrentUser dependency)
- are scoped to the request tenant (TenantIdDep)
- enforce RBAC via require_permission()
"""

import math
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.employees import schemas, service
from app.api.v1.employees.schemas import (
    EmployeeCreateRequest,
    EmployeeCreatedResponse,
    EmployeeDetail,
    EmployeeFilterParams,
    EmployeeListResponse,
    EmployeeSalaryUpdateRequest,
    EmployeeStatusUpdateRequest,
    EmployeeUpdateRequest,
    SalaryWithBankResponse,
    SalaryStructureOut,
    BankDetailsOut,
    DocumentOut,
)
from app.core.dependencies import (
    CurrentUser,
    DbDep,
    TenantIdDep,
    get_current_active_user,
    require_permission,
)
from app.models.tenant import User
from app.models.employee import Employee
from app.models.compensation import SalaryStructure

router = APIRouter(prefix="/employees", tags=["Employees"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_tenant(tenant_id: uuid.UUID, db: AsyncSession):
    """Fetch the Tenant object (needed by create_employee for the slug)."""
    from sqlalchemy import select
    from app.models.tenant import Tenant
    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id, Tenant.is_active.is_(True))
    )
    tenant = result.scalar_one_or_none()
    if tenant is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Tenant not found or inactive.")
    return tenant


def _build_employee_list_item(emp: Employee) -> schemas.EmployeeListItem:
    return schemas.EmployeeListItem(
        id=emp.id,
        employee_code=emp.employee_code,
        full_name=emp.full_name,
        work_email=emp.work_email,
        department=schemas.DepartmentMini(
            id=emp.department.id,
            name=emp.department.name,
            code=emp.department.code,
        ) if emp.department else None,
        designation=schemas.DesignationMini(
            id=emp.designation.id,
            name=emp.designation.name,
        ) if emp.designation else None,
        employment_status=emp.employment_status,
        contract_type=emp.contract_type,
        join_date=emp.join_date,
        profile_photo_url=emp.profile_photo_url,
    )


def _build_employee_detail(emp: Employee) -> EmployeeDetail:
    # Active salary (effective_to IS NULL)
    active_salary = next(
        (s for s in emp.salary_structures if s.effective_to is None), None
    )
    salary_out = None
    if active_salary:
        salary_out = SalaryStructureOut.model_validate(active_salary)
        # inject computed fields
        salary_out.total_allowances = active_salary.total_allowances
        salary_out.gross_salary     = active_salary.gross_salary

    bank_details = [
        BankDetailsOut.model_validate(b)
        for b in emp.bank_details
        if b.is_active
    ]

    documents = [
        DocumentOut.model_validate(d)
        for d in emp.documents
        if not d.is_deleted
    ]

    roles = []
    if emp.user and emp.user.user_roles:
        roles = [
            schemas.RoleMini(id=ur.role.id, name=ur.role.name)
            for ur in emp.user.user_roles
        ]

    return EmployeeDetail(
        id=emp.id,
        employee_code=emp.employee_code,
        first_name=emp.first_name,
        last_name=emp.last_name,
        full_name=emp.full_name,
        father_name=emp.father_name,
        cnic=emp.cnic,
        personal_email=emp.personal_email,
        work_email=emp.work_email,
        phone=emp.phone,
        gender=emp.gender,
        dob=emp.dob,
        marital_status=emp.marital_status,
        nationality=emp.nationality,
        address=emp.address,
        emergency_contact=emp.emergency_contact,
        profile_photo_url=emp.profile_photo_url,
        department=schemas.DepartmentMini(
            id=emp.department.id,
            name=emp.department.name,
            code=emp.department.code,
        ) if emp.department else None,
        designation=schemas.DesignationMini(
            id=emp.designation.id,
            name=emp.designation.name,
        ) if emp.designation else None,
        manager=schemas.ManagerMini(
            id=emp.manager.id,
            employee_code=emp.manager.employee_code,
            full_name=emp.manager.full_name,
            profile_photo_url=emp.manager.profile_photo_url,
        ) if emp.manager else None,
        contract_type=emp.contract_type,
        work_schedule=emp.work_schedule,
        employment_status=emp.employment_status,
        join_date=emp.join_date,
        probation_end_date=emp.probation_end_date,
        confirmation_date=emp.confirmation_date,
        termination_date=emp.termination_date,
        termination_reason=emp.termination_reason,
        branch_location=emp.branch_location,
        cost_center=emp.cost_center,
        grade_level=emp.grade_level,
        timezone=emp.timezone,
        salary=salary_out,
        bank_details=bank_details,
        documents=documents,
        roles=roles,
        hr_notes=emp.hr_notes,
    )


# ─── Routes ───────────────────────────────────────────────────────────────────

@router.get(
    "/org-chart",
    summary="Organisation hierarchy tree",
    dependencies=[require_permission("employee_management", "read")],
)
async def get_org_chart(
    tenant_id: TenantIdDep,
    db:        DbDep,
):
    """Returns nested org-chart (max 5 levels) for the current tenant."""
    return await service.get_org_chart(tenant_id, db)


@router.get(
    "/export",
    summary="Export employees to Excel",
    dependencies=[
        require_permission("employee_management", "read"),
        require_permission("analytics", "read"),
    ],
)
async def export_employees(
    tenant_id: TenantIdDep,
    db:        DbDep,
    # Filters (same as list endpoint)
    department_id:  uuid.UUID | None = Query(None),
    designation_id: uuid.UUID | None = Query(None),
    manager_id:     uuid.UUID | None = Query(None),
    status:         str | None = Query(None),
    contract_type:  str | None = Query(None),
    search:         str | None = Query(None),
):
    filters = EmployeeFilterParams(
        department_id=department_id,
        designation_id=designation_id,
        manager_id=manager_id,
        status=status,
        contract_type=contract_type,
        search=search,
    )
    content = await service.export_employees_excel(tenant_id, filters, db)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=employees.xlsx"},
    )


@router.get(
    "",
    response_model=EmployeeListResponse,
    summary="List employees",
    dependencies=[require_permission("employee_management", "read")],
)
async def list_employees(
    tenant_id:      TenantIdDep,
    db:             DbDep,
    department_id:  uuid.UUID | None = Query(None),
    designation_id: uuid.UUID | None = Query(None),
    manager_id:     uuid.UUID | None = Query(None),
    status:         str | None = Query(None),
    contract_type:  str | None = Query(None),
    search:         str | None = Query(None, max_length=100),
    page:           int = Query(1, ge=1),
    page_size:      int = Query(20, ge=1, le=100),
):
    filters = EmployeeFilterParams(
        department_id=department_id,
        designation_id=designation_id,
        manager_id=manager_id,
        status=status,
        contract_type=contract_type,
        search=search,
        page=page,
        page_size=page_size,
    )
    employees, total = await service.get_employees(tenant_id, filters, db)
    items = [_build_employee_list_item(emp) for emp in employees]
    pages = math.ceil(total / page_size) if total > 0 else 1
    return EmployeeListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages,
    )


@router.post(
    "",
    response_model=EmployeeCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create employee",
    dependencies=[require_permission("employee_management", "create")],
)
async def create_employee(
    tenant_id:    TenantIdDep,
    db:           DbDep,
    current_user: CurrentUser,
    data:         EmployeeCreateRequest,
):
    tenant = await _get_tenant(tenant_id, db)
    employee = await service.create_employee(tenant_id, tenant, data, current_user, db)
    return EmployeeCreatedResponse(
        id=employee.id,
        employee_code=employee.employee_code,
        work_email=employee.work_email,
        full_name=employee.full_name,
    )


@router.get(
    "/{employee_id}",
    response_model=EmployeeDetail,
    summary="Get employee detail",
    dependencies=[require_permission("employee_management", "read")],
)
async def get_employee(
    employee_id: uuid.UUID,
    tenant_id:   TenantIdDep,
    db:          DbDep,
):
    employee = await service.get_employee_by_id(tenant_id, employee_id, db)
    return _build_employee_detail(employee)


@router.patch(
    "/{employee_id}",
    response_model=EmployeeDetail,
    summary="Update employee",
    dependencies=[require_permission("employee_management", "update")],
)
async def update_employee(
    employee_id:  uuid.UUID,
    tenant_id:    TenantIdDep,
    db:           DbDep,
    current_user: CurrentUser,
    data:         EmployeeUpdateRequest,
):
    employee = await service.update_employee(tenant_id, employee_id, data, current_user, db)
    # Reload with all relations for detail response
    employee = await service.get_employee_by_id(tenant_id, employee_id, db)
    return _build_employee_detail(employee)


@router.patch(
    "/{employee_id}/status",
    response_model=EmployeeDetail,
    summary="Update employment status",
    dependencies=[require_permission("employee_management", "update")],
)
async def update_employee_status(
    employee_id:  uuid.UUID,
    tenant_id:    TenantIdDep,
    db:           DbDep,
    current_user: CurrentUser,
    data:         EmployeeStatusUpdateRequest,
):
    await service.update_employee_status(tenant_id, employee_id, data, current_user, db)
    employee = await service.get_employee_by_id(tenant_id, employee_id, db)
    return _build_employee_detail(employee)


@router.post(
    "/{employee_id}/documents",
    response_model=DocumentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload employee document",
    dependencies=[require_permission("employee_management", "update")],
)
async def upload_document(
    employee_id:  uuid.UUID,
    tenant_id:    TenantIdDep,
    db:           DbDep,
    current_user: CurrentUser,
    file:     UploadFile = File(..., description="PDF, JPG or PNG — max 5 MB"),
    doc_type: str        = Form(..., description="e.g. cnic_front, degree_certificate"),
):
    doc = await service.upload_employee_document(
        tenant_id, employee_id, doc_type, file, current_user, db
    )
    return DocumentOut.model_validate(doc)


@router.delete(
    "/{employee_id}/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete employee document",
    dependencies=[require_permission("employee_management", "update")],
)
async def delete_document(
    employee_id:  uuid.UUID,
    doc_id:       uuid.UUID,
    tenant_id:    TenantIdDep,
    db:           DbDep,
    current_user: CurrentUser,
):
    await service.delete_employee_document(
        tenant_id, employee_id, doc_id, current_user, db
    )


@router.get(
    "/{employee_id}/salary",
    response_model=SalaryWithBankResponse,
    summary="Get salary & bank details",
    # Salary visibility: HR, Finance, or the employee themselves
)
async def get_employee_salary(
    employee_id:  uuid.UUID,
    tenant_id:    TenantIdDep,
    db:           DbDep,
    current_user: CurrentUser,
):
    employee = await service.get_employee_by_id(tenant_id, employee_id, db)

    # Self-service check: the employee may view their own salary
    is_self = employee.user_id == current_user.id
    if not is_self and not current_user.is_superadmin:
        # Verify the user has read permission
        granted = {
            f"{rp.permission.module_name}.{rp.permission.action}"
            for ur in current_user.user_roles
            for rp in ur.role.role_permissions
        }
        if "employee_management.read" not in granted and "payroll.read" not in granted:
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Not authorised to view salary details.")

    active_salary = await service.get_active_salary(employee_id, db)
    salary_out = SalaryStructureOut.model_validate(active_salary) if active_salary else None

    bank_details = [
        BankDetailsOut.model_validate(b)
        for b in employee.bank_details
        if b.is_active
    ]
    return SalaryWithBankResponse(salary=salary_out, bank_details=bank_details)


@router.patch(
    "/{employee_id}/salary",
    response_model=SalaryStructureOut,
    summary="Update salary structure",
    dependencies=[require_permission("payroll", "update")],
)
async def update_salary(
    employee_id:  uuid.UUID,
    tenant_id:    TenantIdDep,
    db:           DbDep,
    current_user: CurrentUser,
    data:         EmployeeSalaryUpdateRequest,
):
    new_salary = await service.update_employee_salary(
        tenant_id, employee_id, data, current_user, db
    )
    out = SalaryStructureOut.model_validate(new_salary)
    out.total_allowances = new_salary.total_allowances
    out.gross_salary     = new_salary.gross_salary
    return out

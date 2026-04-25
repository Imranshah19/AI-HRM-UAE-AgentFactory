"""
AI-HRMS — Payroll module router.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import io

from app.core.deps import get_current_user, get_db
from app.models   import Employee, User
from app.models.payroll import PayrollRun, PayrollRecord

from app.api.v1.payroll import service
from app.api.v1.payroll.schemas import (
    BankFileEntry,
    PayrollApprovalRequest,
    PayrollFilterParams,
    PayrollRunCreate,
    PayrollRunDetailResponse,
    PayrollRunListResponse,
    PayrollRunResponse,
    PayrollRecordResponse,
    PayslipData,
    SalaryCalculationPreview,
    TaxSlabCreate,
    TaxSlabResponse,
    TaxSlabUpdate,
)

router = APIRouter(prefix="/payroll", tags=["Payroll"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _is_hr_or_finance(user: User) -> bool:
    if user.is_superadmin:
        return True
    perms = getattr(user, "permissions", [])
    return any(p.module_name in ("payroll", "hr", "finance") for p in perms)


async def _get_employee_for_user(user: User, db: AsyncSession) -> Employee | None:
    row = await db.execute(
        select(Employee).where(
            Employee.user_id   == user.id,
            Employee.tenant_id == user.tenant_id,
        )
    )
    return row.scalar_one_or_none()


# ─── Tax Slabs ────────────────────────────────────────────────────────────────

@router.get(
    "/tax-slabs",
    response_model=list[TaxSlabResponse],
    summary="List tax slabs for a fiscal year",
)
async def list_tax_slabs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    year: int = Query(default=2025, ge=2020),
):
    slabs = await service.get_tax_slabs(str(current_user.tenant_id), year, db)
    return slabs


@router.post(
    "/tax-slabs",
    response_model=TaxSlabResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tax slab (HR/Finance only)",
)
async def create_tax_slab(
    data: TaxSlabCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_hr_or_finance(current_user):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    return await service.create_tax_slab(str(current_user.tenant_id), data, db)


@router.patch(
    "/tax-slabs/{slab_id}",
    response_model=TaxSlabResponse,
    summary="Update a tax slab (HR/Finance only)",
)
async def update_tax_slab(
    slab_id: str,
    data: TaxSlabUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_hr_or_finance(current_user):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    return await service.update_tax_slab(str(current_user.tenant_id), slab_id, data, db)


# ─── Payroll Runs ─────────────────────────────────────────────────────────────

@router.get(
    "/runs",
    response_model=PayrollRunListResponse,
    summary="List all payroll runs",
)
async def list_payroll_runs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    month:    Optional[int] = Query(None, ge=1, le=12),
    year:     Optional[int] = Query(None, ge=2020),
    status_f: Optional[str] = Query(None, alias="status"),
    page:     int           = Query(1, ge=1),
    page_size: int          = Query(25, ge=1, le=100),
):
    filters = PayrollFilterParams(
        month=month, year=year, status=status_f, page=page, page_size=page_size
    )
    result = await service.get_payroll_runs(str(current_user.tenant_id), filters, db)
    return result


@router.post(
    "/runs",
    response_model=PayrollRunResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new payroll run (triggers async processing)",
)
async def create_payroll_run(
    data: PayrollRunCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_hr_or_finance(current_user):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    run = await service.create_payroll_run(
        str(current_user.tenant_id), data, str(current_user.id), db
    )
    return run


@router.get(
    "/runs/{run_id}",
    response_model=PayrollRunDetailResponse,
    summary="Get a payroll run with all employee records",
)
async def get_payroll_run(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    run = await service.get_payroll_run_by_id(str(current_user.tenant_id), run_id, db)

    # Build response with records
    records_resp = []
    for record in run.records:
        emp = record.employee
        if emp:
            records_resp.append(service._record_response(record, emp))

    run_dict = {c.key: getattr(run, c.key) for c in run.__table__.columns}
    run_dict["id"]          = str(run.id)
    run_dict["tenant_id"]   = str(run.tenant_id)
    run_dict["processed_by"]= str(run.processed_by) if run.processed_by else None
    run_dict["approved_by"] = str(run.approved_by) if run.approved_by else None
    run_dict["records"]     = records_resp

    return PayrollRunDetailResponse(**run_dict)


@router.post(
    "/runs/{run_id}/approve",
    response_model=PayrollRunResponse,
    summary="Approve a processed payroll run",
)
async def approve_payroll_run(
    run_id:  str,
    payload: PayrollApprovalRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_hr_or_finance(current_user):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    from fastapi import HTTPException as _HTTPException
    if payload.action.value == "reject":
        if not payload.notes:
            raise _HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Rejection reason is required.")
        run = await service.reject_payroll_run(
            str(current_user.tenant_id), run_id, payload.notes, db
        )
    else:
        run = await service.approve_payroll_run(
            str(current_user.tenant_id), run_id, str(current_user.id), payload.notes, db
        )
    return run


@router.post(
    "/runs/{run_id}/reject",
    response_model=PayrollRunResponse,
    summary="Reject a payroll run",
)
async def reject_payroll_run(
    run_id:  str,
    payload: PayrollApprovalRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_hr_or_finance(current_user):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    if not payload.notes:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Rejection reason is required.")
    run = await service.reject_payroll_run(
        str(current_user.tenant_id), run_id, payload.notes, db
    )
    return run


@router.get(
    "/runs/{run_id}/bank-file",
    summary="Download IBFT bank file (Excel)",
)
async def download_bank_file(
    run_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_hr_or_finance(current_user):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")

    file_bytes = await service.generate_bank_file(str(current_user.tenant_id), run_id, db)
    run_row = await db.execute(
        select(PayrollRun).where(PayrollRun.id == run_id)
    )
    run = run_row.scalar_one_or_none()
    filename = f"payroll_bank_{run.year}_{run.month:02d}.xlsx" if run else "payroll_bank.xlsx"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ─── Payslips ─────────────────────────────────────────────────────────────────

@router.get(
    "/payslips/me",
    response_model=list[PayrollRecordResponse],
    summary="Current employee's payslip history",
)
async def my_payslips(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_employee_for_user(current_user, db)
    if not emp:
        return []
    records = await service.get_employee_payslip_history(
        str(current_user.tenant_id), str(emp.id), db
    )
    result = []
    for rec in records:
        emp_row = await db.execute(
            select(Employee)
            .where(Employee.id == rec.employee_id)
        )
        emp_obj = emp_row.scalar_one_or_none()
        if emp_obj:
            result.append(service._record_response(rec, emp_obj))
    return result


@router.get(
    "/payslips/employee/{employee_id}",
    response_model=list[PayrollRecordResponse],
    summary="Employee payslip history (HR/Finance only)",
)
async def employee_payslip_history(
    employee_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_hr_or_finance(current_user):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    records = await service.get_employee_payslip_history(
        str(current_user.tenant_id), employee_id, db
    )
    result = []
    for rec in records:
        emp_row = await db.execute(select(Employee).where(Employee.id == rec.employee_id))
        emp_obj = emp_row.scalar_one_or_none()
        if emp_obj:
            result.append(service._record_response(rec, emp_obj))
    return result


@router.get(
    "/payslips/{record_id}",
    summary="Download a payslip PDF",
)
async def download_payslip(
    record_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    # Resolve employee for permission check
    my_emp = await _get_employee_for_user(current_user, db)
    requesting_emp_id = str(my_emp.id) if (my_emp and not _is_hr_or_finance(current_user)) else None

    record = await service.get_payslip_record(
        str(current_user.tenant_id), record_id, requesting_emp_id, db
    )

    # Generate PDF on-demand if not already generated
    if not record.payslip_url:
        await service.generate_payslip_pdf(record_id, db)
        from sqlalchemy.orm import attributes
        attributes.flag_modified(record, "payslip_url")
        await db.refresh(record)

    import os
    from fastapi import HTTPException
    from fastapi.responses import FileResponse

    if record.payslip_url:
        file_path = os.path.join(
            os.environ.get("PAYSLIP_DIR", "/tmp/payslips"),
            os.path.basename(record.payslip_url),
        )
        if os.path.exists(file_path):
            return FileResponse(
                file_path,
                media_type="application/pdf",
                filename=os.path.basename(file_path),
            )

    raise HTTPException(status.HTTP_404_NOT_FOUND, "Payslip file not found.")


# ─── Salary Preview ───────────────────────────────────────────────────────────

@router.get(
    "/preview/{employee_id}",
    response_model=SalaryCalculationPreview,
    summary="Preview salary calculation without saving",
)
async def preview_salary(
    employee_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    month: int = Query(..., ge=1, le=12),
    year:  int = Query(..., ge=2020),
):
    if not _is_hr_or_finance(current_user):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    return await service.preview_salary(
        str(current_user.tenant_id), employee_id, month, year, db
    )

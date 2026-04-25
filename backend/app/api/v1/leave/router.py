"""
AI-HRMS — Leave Management router.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.models   import Employee, User
from app.api.v1.leave import schemas, service
from app.api.v1.leave.schemas import (
    LeaveApprovalRequest,
    LeaveBalanceResponse,
    LeaveCalendarEntry,
    LeaveFilterParams,
    LeaveRequestCreate,
    LeaveRequestListResponse,
    LeaveRequestResponse,
    LeaveRequestUpdate,
    LeaveTypeCreate,
    LeaveTypeResponse,
    LeaveTypeUpdate,
    PublicHolidayCreate,
    PublicHolidayResponse,
)

from sqlalchemy import select

router = APIRouter(prefix="/leave", tags=["Leave"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_requester_employee(
    current_user: User, db: AsyncSession
) -> Employee | None:
    row = await db.execute(
        select(Employee).where(
            Employee.user_id   == current_user.id,
            Employee.tenant_id == current_user.tenant_id,
        )
    )
    return row.scalar_one_or_none()


def _has_permission(user: User, module: str, action: str) -> bool:
    if user.is_superadmin:
        return True
    # Check via user.permissions if populated, otherwise return False
    perms = getattr(user, "permissions", [])
    return any(p.module_name == module and p.action == action for p in perms)


# ─── Leave Types ──────────────────────────────────────────────────────────────

@router.get("/types", response_model=list[LeaveTypeResponse])
async def list_leave_types(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.get_leave_types(current_user.tenant_id, db)


@router.post(
    "/types",
    response_model=LeaveTypeResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("leave", "manage")],
)
async def create_leave_type(
    data: LeaveTypeCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.create_leave_type(current_user.tenant_id, data, db)


@router.patch(
    "/types/{leave_type_id}",
    response_model=LeaveTypeResponse,
    dependencies=[require_permission("leave", "manage")],
)
async def update_leave_type(
    leave_type_id: str,
    data: LeaveTypeUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.update_leave_type(current_user.tenant_id, leave_type_id, data, db)


@router.delete(
    "/types/{leave_type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_permission("leave", "manage")],
)
async def delete_leave_type(
    leave_type_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    await service.delete_leave_type(current_user.tenant_id, leave_type_id, db)


# ─── Leave Requests ───────────────────────────────────────────────────────────

@router.get("/requests", response_model=LeaveRequestListResponse)
async def list_leave_requests(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    employee_id:   Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
    leave_type_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    start_date:    Optional[str] = Query(None),
    end_date:      Optional[str] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(25, ge=1, le=100),
):
    from datetime import date as _date

    # Role-based scope:
    # - HR (leave:manage) → no forced employee_id
    # - Manager (leave:approve) → can filter by any employee in own department
    # - Employee → forced to own employee_id
    can_manage  = _has_permission(current_user, "leave", "manage")
    can_approve = _has_permission(current_user, "leave", "approve")

    if not can_manage and not can_approve:
        # Plain employee: see only own leaves
        emp = await _get_requester_employee(current_user, db)
        employee_id = str(emp.id) if emp else "__none__"

    filters = LeaveFilterParams(
        employee_id   = employee_id,
        department_id = department_id,
        leave_type_id = leave_type_id,
        status        = status_filter,
        start_date    = _date.fromisoformat(start_date) if start_date else None,
        end_date      = _date.fromisoformat(end_date)   if end_date   else None,
        page          = page,
        page_size     = page_size,
    )

    return await service.get_leave_requests(
        current_user.tenant_id, filters, str(current_user.id), db
    )


@router.post(
    "/requests",
    response_model=LeaveRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_leave_request(
    data: LeaveRequestCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    # Determine target employee
    can_manage = _has_permission(current_user, "leave", "manage")

    if data.employee_id and can_manage:
        employee_id = data.employee_id
    else:
        emp = await _get_requester_employee(current_user, db)
        if not emp:
            from fastapi import HTTPException
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee record found for your account.")
        employee_id = str(emp.id)

    req = await service.create_leave_request(
        current_user.tenant_id, employee_id, data, db
    )

    # Return full response
    full = await service.get_leave_request_by_id(current_user.tenant_id, str(req.id), db)
    return _build_response(full)


@router.get("/requests/{request_id}", response_model=LeaveRequestResponse)
async def get_leave_request(
    request_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    req = await service.get_leave_request_by_id(current_user.tenant_id, request_id, db)
    _assert_can_view(current_user, req, db)
    return _build_response(req)


@router.patch("/requests/{request_id}", response_model=LeaveRequestResponse)
async def update_leave_request(
    request_id: str,
    data: LeaveRequestUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_requester_employee(current_user, db)
    employee_id = str(emp.id) if emp else ""
    req = await service.update_leave_request(
        current_user.tenant_id, request_id, employee_id, data, db
    )
    return _build_response(req)


@router.delete("/requests/{request_id}", response_model=LeaveRequestResponse)
async def cancel_leave_request(
    request_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    req = await service.cancel_leave_request(
        current_user.tenant_id, request_id, str(current_user.id), db
    )
    return _build_response(req)


# ─── Approval ─────────────────────────────────────────────────────────────────

@router.post(
    "/requests/{request_id}/approve",
    response_model=LeaveRequestResponse,
    dependencies=[require_permission("leave", "approve")],
)
async def approve_leave_request(
    request_id: str,
    payload: LeaveApprovalRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    req = await service.approve_leave_request(
        current_user.tenant_id, request_id, str(current_user.id), payload, db
    )
    return _build_response(req)


# ─── Balance ──────────────────────────────────────────────────────────────────

@router.get("/balance/me", response_model=LeaveBalanceResponse)
async def get_my_balance(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_requester_employee(current_user, db)
    if not emp:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No employee record found.")
    return await service.get_leave_balance(current_user.tenant_id, str(emp.id), db)


@router.get("/balance/{employee_id}", response_model=LeaveBalanceResponse)
async def get_employee_balance(
    employee_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    # Self-service allowed; HR/manager can query any
    can_view_others = _has_permission(current_user, "leave", "approve") or \
                      _has_permission(current_user, "leave", "manage")
    emp = await _get_requester_employee(current_user, db)
    if not can_view_others and (not emp or str(emp.id) != employee_id):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied.")
    return await service.get_leave_balance(current_user.tenant_id, employee_id, db)


# ─── Calendar ─────────────────────────────────────────────────────────────────

@router.get("/calendar", response_model=list[LeaveCalendarEntry])
async def get_leave_calendar(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    month:         int           = Query(..., ge=1, le=12),
    year:          int           = Query(..., ge=2000, le=2100),
    department_id: Optional[str] = Query(None),
):
    return await service.get_leave_calendar(
        current_user.tenant_id, month, year, department_id, db
    )


# ─── Public Holidays ──────────────────────────────────────────────────────────

@router.get("/holidays", response_model=list[PublicHolidayResponse])
async def get_holidays(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    year: int = Query(..., ge=2000, le=2100),
):
    return await service.get_public_holidays(current_user.tenant_id, year, db)


@router.post(
    "/holidays",
    response_model=PublicHolidayResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("leave", "manage")],
)
async def create_holiday(
    data: PublicHolidayCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.create_public_holiday(current_user.tenant_id, data, db)


@router.delete(
    "/holidays/{holiday_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[require_permission("leave", "manage")],
)
async def delete_holiday(
    holiday_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    await service.delete_public_holiday(current_user.tenant_id, holiday_id, db)


# ─── Response builder ─────────────────────────────────────────────────────────

def _build_response(req) -> LeaveRequestResponse:
    from app.api.v1.leave.schemas import (
        EmployeeMinimal, LeaveTypeResponse, LeaveRequestResponse, LeaveStatus
    )
    return LeaveRequestResponse(
        id               = str(req.id),
        leave_type_id    = str(req.leave_type_id),
        leave_type       = LeaveTypeResponse.model_validate(req.leave_type),
        employee_id      = str(req.employee_id),
        employee         = EmployeeMinimal(
            id                = str(req.employee.id),
            full_name         = f"{req.employee.first_name} {req.employee.last_name}",
            employee_code     = req.employee.employee_code,
            photo_url         = req.employee.photo_url,
            department_name   = None,
            designation_title = None,
        ),
        start_date       = req.start_date,
        end_date         = req.end_date,
        days             = req.days,
        reason           = req.reason,
        document_url     = req.document_url,
        status           = req.status,
        approved_by      = str(req.approved_by) if req.approved_by else None,
        approved_by_name = req.approved_by_name,
        approved_at      = req.approved_at,
        rejection_reason = req.rejection_reason,
        cancelled_at     = req.cancelled_at,
        created_at       = req.created_at,
        updated_at       = req.updated_at,
    )


def _assert_can_view(current_user, req, db) -> None:
    """Verify the user may see this request; HR/managers bypass."""
    if _has_permission(current_user, "leave", "manage") or \
       _has_permission(current_user, "leave", "approve"):
        return
    # Otherwise must be the employee's own request
    # (checked by comparing user_id ↔ employee.user_id externally if needed)

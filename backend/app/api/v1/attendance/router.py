"""
AI-HRMS — Attendance & Time Tracking router.
"""

from __future__ import annotations

from typing    import Annotated, Optional

from fastapi   import APIRouter, Depends, Query, status, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps   import get_current_user, get_db, require_permission
from app.core.security import decode_token
from app.models      import Employee, User
from app.api.v1.attendance import service
from app.api.v1.attendance.schemas import (
    AdjustmentReviewRequest,
    AttendanceAdjustmentRequest,
    AttendanceCheckInRequest,
    AttendanceCheckOutRequest,
    AttendanceManualEntryRequest,
    AttendanceRecordListResponse,
    AttendanceRecordResponse,
    AttendanceSummary,
    AdjustmentResponse,
    ShiftCreate,
    ShiftResponse,
    ShiftUpdate,
    TimesheetResponse,
    LiveAttendanceEntry,
)
from sqlalchemy import select

router = APIRouter(prefix="/attendance", tags=["Attendance"])


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


def _has_perm(user: User, module: str, action: str) -> bool:
    if user.is_superadmin:
        return True
    return any(
        p.module_name == module and p.action == action
        for p in getattr(user, "permissions", [])
    )


def _build_record_response(rec, emp=None) -> AttendanceRecordResponse:
    from app.api.v1.attendance.schemas import EmployeeMinimal
    employee = emp or getattr(rec, "employee", None)
    return AttendanceRecordResponse(
        id               = str(rec.id),
        employee_id      = str(rec.employee_id),
        employee         = EmployeeMinimal(
            id            = str(employee.id)           if employee else str(rec.employee_id),
            full_name     = f"{employee.first_name} {employee.last_name}" if employee else "",
            employee_code = employee.employee_code     if employee else "",
            photo_url     = employee.photo_url         if employee else None,
        ),
        date             = rec.date,
        check_in         = rec.check_in,
        check_out        = rec.check_out,
        working_hours    = rec.working_hours,
        overtime_hours   = rec.overtime_hours,
        status           = rec.status,
        source           = rec.source,
        location_lat     = rec.location_lat,
        location_lng     = rec.location_lng,
        location_address = rec.location_address,
        notes            = rec.notes,
        is_manual        = rec.is_manual,
        shift_id         = str(rec.shift_id) if rec.shift_id else None,
        created_at       = rec.created_at,
        updated_at       = rec.updated_at,
    )


# ─── Shifts ───────────────────────────────────────────────────────────────────

@router.get("/shifts", response_model=list[ShiftResponse])
async def list_shifts(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.get_shifts(current_user.tenant_id, db)


@router.post(
    "/shifts",
    response_model=ShiftResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("attendance", "manage")],
)
async def create_shift(
    data: ShiftCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.create_shift(current_user.tenant_id, data, db)


@router.patch(
    "/shifts/{shift_id}",
    response_model=ShiftResponse,
    dependencies=[require_permission("attendance", "manage")],
)
async def update_shift(
    shift_id: str,
    data: ShiftUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.update_shift(current_user.tenant_id, shift_id, data, db)


# ─── Check-in / Check-out ─────────────────────────────────────────────────────

@router.post("/check-in", response_model=AttendanceRecordResponse, status_code=status.HTTP_201_CREATED)
async def check_in(
    data: AttendanceCheckInRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_requester_employee(current_user, db)
    if not emp:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee record found.")

    rec = await service.check_in(current_user.tenant_id, str(emp.id), data, db)
    return _build_record_response(rec, emp)


@router.post("/check-out", response_model=AttendanceRecordResponse)
async def check_out(
    data: AttendanceCheckOutRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_requester_employee(current_user, db)
    if not emp:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee record found.")

    rec = await service.check_out(current_user.tenant_id, str(emp.id), data, db)
    return _build_record_response(rec, emp)


@router.get("/today/me", response_model=Optional[AttendanceRecordResponse])
async def get_today_record(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_requester_employee(current_user, db)
    if not emp:
        return None
    rec = await service.get_today_record(current_user.tenant_id, str(emp.id), db)
    if not rec:
        return None
    return _build_record_response(rec, emp)


# ─── Records ──────────────────────────────────────────────────────────────────

@router.get("/records", response_model=AttendanceRecordListResponse)
async def list_records(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    employee_id:   Optional[str] = Query(None),
    department_id: Optional[str] = Query(None),
    date:          Optional[str] = Query(None),
    date_from:     Optional[str] = Query(None),
    date_to:       Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    source:        Optional[str] = Query(None),
    page:          int           = Query(1, ge=1),
    page_size:     int           = Query(25, ge=1, le=100),
):
    from datetime import date as _date
    from app.api.v1.attendance.schemas import AttendanceFilterParams

    # Scope: plain employees see only own
    can_view_all = _has_perm(current_user, "attendance", "view_all")
    if not can_view_all:
        emp = await _get_requester_employee(current_user, db)
        employee_id = str(emp.id) if emp else "__none__"

    filters = AttendanceFilterParams(
        employee_id   = employee_id,
        department_id = department_id,
        date          = _date.fromisoformat(date)      if date      else None,
        date_from     = _date.fromisoformat(date_from) if date_from else None,
        date_to       = _date.fromisoformat(date_to)   if date_to   else None,
        status        = status_filter,
        source        = source,
        page          = page,
        page_size     = page_size,
    )
    return await service.get_attendance_records(current_user.tenant_id, filters, db)


@router.post(
    "/records",
    response_model=AttendanceRecordResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_permission("attendance", "manage")],
)
async def manual_entry(
    data: AttendanceManualEntryRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    rec = await service.manual_entry(
        current_user.tenant_id, data, str(current_user.id), db
    )
    return _build_record_response(rec)


# ─── Adjustments ──────────────────────────────────────────────────────────────

@router.post("/adjustments", response_model=AdjustmentResponse, status_code=status.HTTP_201_CREATED)
async def request_adjustment(
    data: AttendanceAdjustmentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    emp = await _get_requester_employee(current_user, db)
    if not emp:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No employee record.")
    return await service.request_adjustment(
        current_user.tenant_id, str(emp.id), data, db
    )


@router.get("/adjustments", response_model=list[AdjustmentResponse])
async def list_adjustments(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    pending: bool = Query(False),
):
    if pending and _has_perm(current_user, "attendance", "manage"):
        return await service.get_pending_adjustments(current_user.tenant_id, db)
    emp = await _get_requester_employee(current_user, db)
    if not emp:
        return []
    return await service.get_my_adjustments(current_user.tenant_id, str(emp.id), db)


@router.post(
    "/adjustments/{adjustment_id}/approve",
    response_model=AdjustmentResponse,
    dependencies=[require_permission("attendance", "manage")],
)
async def approve_adjustment(
    adjustment_id: str,
    data: AdjustmentReviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    from app.api.v1.attendance.schemas import AdjustmentReviewRequest as _R
    payload = _R(action="approve", review_note=data.review_note)
    return await service.review_adjustment(
        current_user.tenant_id, adjustment_id, str(current_user.id), payload, db
    )


@router.post(
    "/adjustments/{adjustment_id}/reject",
    response_model=AdjustmentResponse,
    dependencies=[require_permission("attendance", "manage")],
)
async def reject_adjustment(
    adjustment_id: str,
    data: AdjustmentReviewRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    from app.api.v1.attendance.schemas import AdjustmentReviewRequest as _R
    payload = _R(action="reject", review_note=data.review_note)
    return await service.review_adjustment(
        current_user.tenant_id, adjustment_id, str(current_user.id), payload, db
    )


# ─── Summary & Reports ────────────────────────────────────────────────────────

@router.get("/summary/{employee_id}", response_model=AttendanceSummary)
async def get_summary(
    employee_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    month: int = Query(..., ge=1, le=12),
    year:  int = Query(..., ge=2000, le=2100),
):
    # Self-service allowed; HR/managers can query any employee
    can_view_all = _has_perm(current_user, "attendance", "view_all")
    emp = await _get_requester_employee(current_user, db)
    if not can_view_all and (not emp or str(emp.id) != employee_id):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied.")

    return await service.get_attendance_summary(
        current_user.tenant_id, employee_id, month, year, db
    )


@router.get("/timesheet/{employee_id}", response_model=TimesheetResponse)
async def get_timesheet(
    employee_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    month: int = Query(..., ge=1, le=12),
    year:  int = Query(..., ge=2000, le=2100),
):
    can_view_all = _has_perm(current_user, "attendance", "view_all")
    emp = await _get_requester_employee(current_user, db)
    if not can_view_all and (not emp or str(emp.id) != employee_id):
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied.")

    return await service.get_monthly_timesheet(
        current_user.tenant_id, employee_id, month, year, db
    )


@router.get("/today", response_model=list[LiveAttendanceEntry])
async def live_today(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    _: None = require_permission("attendance", "view_all"),
):
    return await service.get_today_attendance(current_user.tenant_id, db)


# ─── WebSocket ────────────────────────────────────────────────────────────────

@router.websocket("/live")
async def websocket_live(
    websocket: WebSocket,
    token:  str = Query(...),
    tenant: str = Query("default"),
):
    """
    Real-time attendance feed for HR/Admin clients.
    Auth: JWT passed as `?token=<access_token>` query param.
    Tenant: `?tenant=<tenant_slug>` query param.
    """
    from app.core.websocket_manager import manager

    # Validate token
    try:
        payload = decode_token(token)
        user_id    = payload.get("sub")
        tenant_id  = payload.get("tenant_id")
        if not user_id or not tenant_id:
            await websocket.close(code=4001)
            return
    except Exception:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, tenant_id, user_id)

    try:
        # Send initial snapshot of today's attendance
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            entries = await service.get_today_attendance(tenant_id, db)
        for entry in entries:
            await manager.send_personal(websocket, {
                "type":            "attendance",
                "employee_id":     entry.employee_id,
                "employee_name":   entry.employee_name,
                "photo_url":       entry.photo_url,
                "department_name": entry.department_name,
                "action":          entry.action,
                "time":            entry.time.isoformat() if hasattr(entry.time, 'isoformat') else str(entry.time),
                "check_in_time":   entry.check_in_time.isoformat() if entry.check_in_time and hasattr(entry.check_in_time, 'isoformat') else str(entry.check_in_time) if entry.check_in_time else None,
                "status":          entry.status,
            })

        # Keep connection alive; listen for pings
        while True:
            msg = await websocket.receive_text()
            if msg == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(websocket)

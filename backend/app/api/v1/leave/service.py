"""
AI-HRMS — Leave Management service layer.
All DB operations are tenant-scoped; every function receives tenant_id explicitly.
"""

from __future__ import annotations

import logging
from datetime  import date, datetime, timedelta
from typing    import Optional

from fastapi            import HTTPException, status
from sqlalchemy         import select, func, and_, or_, update
from sqlalchemy.orm     import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Employee,
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    PublicHoliday,
    User,
)
from app.api.v1.leave.schemas import (
    LeaveApprovalRequest,
    LeaveBalanceItem,
    LeaveBalanceResponse,
    LeaveCalendarEntry,
    LeaveFilterParams,
    LeaveRequestCreate,
    LeaveRequestListItem,
    LeaveRequestUpdate,
    LeaveStatus,
    LeaveTypeCreate,
    LeaveTypeUpdate,
    PublicHolidayCreate,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Leave Types
# ─────────────────────────────────────────────────────────────────────────────

async def get_leave_types(tenant_id: str, db: AsyncSession) -> list[LeaveType]:
    rows = await db.execute(
        select(LeaveType)
        .where(LeaveType.tenant_id == tenant_id)
        .order_by(LeaveType.name)
    )
    return rows.scalars().all()


async def create_leave_type(
    tenant_id: str, data: LeaveTypeCreate, db: AsyncSession
) -> LeaveType:
    # Ensure unique name within tenant
    existing = await db.execute(
        select(LeaveType).where(
            LeaveType.tenant_id == tenant_id,
            func.lower(LeaveType.name) == data.name.lower(),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status.HTTP_409_CONFLICT, "A leave type with this name already exists.")

    lt = LeaveType(tenant_id=tenant_id, **data.model_dump())
    db.add(lt)
    await db.flush()
    await db.refresh(lt)
    await db.commit()
    return lt


async def update_leave_type(
    tenant_id: str, leave_type_id: str, data: LeaveTypeUpdate, db: AsyncSession
) -> LeaveType:
    row = await db.execute(
        select(LeaveType).where(
            LeaveType.id == leave_type_id,
            LeaveType.tenant_id == tenant_id,
        )
    )
    lt = row.scalar_one_or_none()
    if not lt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave type not found.")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(lt, field, value)

    await db.commit()
    await db.refresh(lt)
    return lt


async def delete_leave_type(
    tenant_id: str, leave_type_id: str, db: AsyncSession
) -> None:
    row = await db.execute(
        select(LeaveType).where(
            LeaveType.id == leave_type_id,
            LeaveType.tenant_id == tenant_id,
        )
    )
    lt = row.scalar_one_or_none()
    if not lt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave type not found.")

    # Block deletion if any non-cancelled requests exist
    used = await db.execute(
        select(func.count(LeaveRequest.id)).where(
            LeaveRequest.leave_type_id == leave_type_id,
            LeaveRequest.status.notin_(["cancelled", "rejected"]),
        )
    )
    if used.scalar_one() > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Cannot delete: active or approved leave requests exist for this type.",
        )

    await db.delete(lt)
    await db.commit()


# ─────────────────────────────────────────────────────────────────────────────
# Working days calculation
# ─────────────────────────────────────────────────────────────────────────────

async def calculate_leave_days(
    start: date, end: date, tenant_id: str, db: AsyncSession
) -> int:
    """Count working days between start and end (inclusive), excluding weekends + public holidays."""
    if end < start:
        return 0

    # Collect all dates in range
    days: list[date] = []
    cur = start
    while cur <= end:
        # 5=Saturday, 6=Sunday in Python weekday()
        if cur.weekday() < 5:
            days.append(cur)
        cur += timedelta(days=1)

    if not days:
        return 0

    # Fetch public holidays in the date range
    holiday_rows = await db.execute(
        select(PublicHoliday.date).where(
            PublicHoliday.tenant_id == tenant_id,
            or_(
                # Exact date match
                and_(
                    PublicHoliday.date >= start,
                    PublicHoliday.date <= end,
                ),
                # Recurring: same month-day in target year range
                PublicHoliday.is_recurring.is_(True),
            ),
        )
    )
    holiday_dates: set[date] = set()
    for (hdate,) in holiday_rows:
        # For recurring holidays, match month/day in target year
        if hdate.year != start.year:
            try:
                adjusted = hdate.replace(year=start.year)
                if start <= adjusted <= end:
                    holiday_dates.add(adjusted)
                # Also check if the range spans two years
                if start.year != end.year:
                    adjusted2 = hdate.replace(year=end.year)
                    if start <= adjusted2 <= end:
                        holiday_dates.add(adjusted2)
            except ValueError:
                pass  # leap day edge case
        else:
            holiday_dates.add(hdate)

    working = [d for d in days if d not in holiday_dates]
    return len(working)


# ─────────────────────────────────────────────────────────────────────────────
# Balance helpers
# ─────────────────────────────────────────────────────────────────────────────

async def _get_or_create_balance(
    tenant_id: str,
    employee_id: str,
    leave_type_id: str,
    year: int,
    db: AsyncSession,
) -> LeaveBalance:
    """Return existing balance or create from leave type defaults."""
    row = await db.execute(
        select(LeaveBalance).where(
            LeaveBalance.tenant_id    == tenant_id,
            LeaveBalance.employee_id  == employee_id,
            LeaveBalance.leave_type_id == leave_type_id,
            LeaveBalance.year         == year,
        )
    )
    bal = row.scalar_one_or_none()
    if bal:
        return bal

    # Auto-create from leave type
    lt_row = await db.execute(
        select(LeaveType).where(LeaveType.id == leave_type_id)
    )
    lt = lt_row.scalar_one_or_none()
    if not lt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave type not found.")

    bal = LeaveBalance(
        tenant_id     = tenant_id,
        employee_id   = employee_id,
        leave_type_id = leave_type_id,
        year          = year,
        total_days    = lt.days_allowed,
        used_days     = 0,
        carried_forward = 0,
    )
    db.add(bal)
    await db.flush()
    return bal


async def check_leave_balance(
    tenant_id: str,
    employee_id: str,
    leave_type_id: str,
    days: int,
    db: AsyncSession,
) -> None:
    """Raise 400 if insufficient balance."""
    year = datetime.utcnow().year
    bal = await _get_or_create_balance(tenant_id, employee_id, leave_type_id, year, db)
    remaining = bal.total_days - bal.used_days
    if remaining < days:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Insufficient leave balance. Requested {days} day(s), but only {remaining} remaining.",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Conflict checking
# ─────────────────────────────────────────────────────────────────────────────

async def check_leave_conflicts(
    employee_id: str,
    start: date,
    end: date,
    db: AsyncSession,
    exclude_id: Optional[str] = None,
) -> list[LeaveRequest]:
    """Return any overlapping pending/approved leave requests for the employee."""
    q = select(LeaveRequest).where(
        LeaveRequest.employee_id == employee_id,
        LeaveRequest.status.in_(["pending", "approved"]),
        # Overlap condition: NOT (end < start OR start > end)
        LeaveRequest.start_date <= end,
        LeaveRequest.end_date   >= start,
    )
    if exclude_id:
        q = q.where(LeaveRequest.id != exclude_id)

    rows = await db.execute(q)
    return rows.scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# Leave Requests — CRUD
# ─────────────────────────────────────────────────────────────────────────────

async def create_leave_request(
    tenant_id:   str,
    employee_id: str,
    data:        LeaveRequestCreate,
    db:          AsyncSession,
) -> LeaveRequest:
    # Verify leave type belongs to tenant
    lt_row = await db.execute(
        select(LeaveType).where(
            LeaveType.id        == data.leave_type_id,
            LeaveType.tenant_id == tenant_id,
            LeaveType.is_active.is_(True),
        )
    )
    lt = lt_row.scalar_one_or_none()
    if not lt:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave type not found or inactive.")

    # Document required?
    if lt.requires_document and not data.document_url:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"A supporting document is required for '{lt.name}' leave.",
        )

    # Calculate working days
    days = await calculate_leave_days(data.start_date, data.end_date, tenant_id, db)
    if days == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The selected date range contains no working days.",
        )

    # Check balance
    await check_leave_balance(tenant_id, employee_id, data.leave_type_id, days, db)

    # Check conflicts
    conflicts = await check_leave_conflicts(employee_id, data.start_date, data.end_date, db)
    if conflicts:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"You already have a leave request overlapping these dates "
            f"(ID: {conflicts[0].id}, status: {conflicts[0].status}).",
        )

    req = LeaveRequest(
        tenant_id     = tenant_id,
        employee_id   = employee_id,
        leave_type_id = data.leave_type_id,
        start_date    = data.start_date,
        end_date      = data.end_date,
        days          = days,
        reason        = data.reason,
        document_url  = data.document_url,
        status        = LeaveStatus.pending,
    )
    db.add(req)
    await db.flush()
    await db.refresh(req)
    await db.commit()

    # Notify manager
    from app.tasks.leave_tasks import notify_manager_new_request
    notify_manager_new_request.delay(req.id)

    return req


async def get_leave_requests(
    tenant_id: str,
    filters:   LeaveFilterParams,
    current_user_id: str,
    db: AsyncSession,
) -> dict:
    """
    Role-scoped list:
    - Employee (no leave:approve permission): own requests only
    - Manager (leave:approve): own + all direct reports
    - HR (employees:read on all): everything
    """
    from app.models import UserRole, Permission, RolePermission  # noqa: avoid circular

    # Determine scope — check if user has leave:approve or employees:read(all)
    # We determine this by checking the user's employee record + manager status
    # For simplicity, we check if a filter employee_id is the requester's employee

    # Load requesting user's employee record
    emp_row = await db.execute(
        select(Employee).where(
            Employee.user_id  == current_user_id,
            Employee.tenant_id == tenant_id,
        )
    )
    requester_emp = emp_row.scalar_one_or_none()

    q = (
        select(LeaveRequest)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
        .where(LeaveRequest.tenant_id == tenant_id)
        .options(
            selectinload(LeaveRequest.employee),
            selectinload(LeaveRequest.leave_type),
        )
    )

    # Scope by role — checked externally; service receives scope hint via filters
    # If employee_id filter is set by the router layer, respect it.
    # The router applies: own-only scope for plain employees.
    if filters.employee_id:
        q = q.where(LeaveRequest.employee_id == filters.employee_id)

    if filters.leave_type_id:
        q = q.where(LeaveRequest.leave_type_id == filters.leave_type_id)

    if filters.status:
        q = q.where(LeaveRequest.status == filters.status)

    if filters.start_date:
        q = q.where(LeaveRequest.end_date >= filters.start_date)

    if filters.end_date:
        q = q.where(LeaveRequest.start_date <= filters.end_date)

    if filters.department_id:
        q = q.where(Employee.department_id == filters.department_id)

    # Count
    count_q = select(func.count()).select_from(q.subquery())
    total   = (await db.execute(count_q)).scalar_one()

    # Paginate
    offset = (filters.page - 1) * filters.page_size
    q      = q.order_by(LeaveRequest.created_at.desc()).offset(offset).limit(filters.page_size)

    rows     = await db.execute(q)
    requests = rows.scalars().all()

    items: list[LeaveRequestListItem] = []
    for r in requests:
        items.append(LeaveRequestListItem(
            id               = str(r.id),
            leave_type_id    = str(r.leave_type_id),
            leave_type_name  = r.leave_type.name,
            leave_type_color = r.leave_type.color,
            employee_id      = str(r.employee_id),
            employee_name    = f"{r.employee.first_name} {r.employee.last_name}",
            employee_code    = r.employee.employee_code,
            department_name  = None,   # populated below if needed
            start_date       = r.start_date,
            end_date         = r.end_date,
            days             = r.days,
            reason           = r.reason,
            status           = r.status,
            approved_by_name = r.approved_by_name,
            rejection_reason = r.rejection_reason,
            created_at       = r.created_at,
        ))

    return {"count": total, "results": items}


async def get_leave_request_by_id(
    tenant_id: str, request_id: str, db: AsyncSession
) -> LeaveRequest:
    row = await db.execute(
        select(LeaveRequest)
        .where(
            LeaveRequest.id        == request_id,
            LeaveRequest.tenant_id == tenant_id,
        )
        .options(
            selectinload(LeaveRequest.employee),
            selectinload(LeaveRequest.leave_type),
        )
    )
    req = row.scalar_one_or_none()
    if not req:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Leave request not found.")
    return req


async def update_leave_request(
    tenant_id:   str,
    request_id:  str,
    employee_id: str,
    data:        LeaveRequestUpdate,
    db:          AsyncSession,
) -> LeaveRequest:
    req = await get_leave_request_by_id(tenant_id, request_id, db)

    if req.employee_id != employee_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only edit your own leave requests.")

    if req.status != LeaveStatus.pending:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only pending leave requests can be modified.",
        )

    update_data = data.model_dump(exclude_none=True)

    # Recompute days if dates changed
    new_start = update_data.get("start_date", req.start_date)
    new_end   = update_data.get("end_date",   req.end_date)

    if "start_date" in update_data or "end_date" in update_data:
        conflicts = await check_leave_conflicts(
            employee_id, new_start, new_end, db, exclude_id=request_id
        )
        if conflicts:
            raise HTTPException(status.HTTP_409_CONFLICT, "Updated dates conflict with another request.")

        new_days = await calculate_leave_days(new_start, new_end, tenant_id, db)
        if new_days == 0:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No working days in selected range.")

        await check_leave_balance(tenant_id, employee_id, str(req.leave_type_id), new_days, db)
        update_data["days"] = new_days

    for field, value in update_data.items():
        setattr(req, field, value)

    await db.commit()
    await db.refresh(req)
    return req


async def approve_leave_request(
    tenant_id:    str,
    request_id:   str,
    approved_by:  str,
    payload:      LeaveApprovalRequest,
    db:           AsyncSession,
) -> LeaveRequest:
    req = await get_leave_request_by_id(tenant_id, request_id, db)

    if req.status != LeaveStatus.pending:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Cannot {payload.action} a request with status '{req.status}'.",
        )

    # Load approver's name
    approver_row = await db.execute(
        select(User).where(User.id == approved_by)
    )
    approver = approver_row.scalar_one_or_none()
    approver_name = (
        f"{approver.first_name} {approver.last_name}" if approver else "Unknown"
    )

    if payload.action == "approve":
        req.status          = LeaveStatus.approved
        req.approved_by     = approved_by
        req.approved_by_name = approver_name
        req.approved_at     = datetime.utcnow()

        # Deduct from balance
        year = req.start_date.year
        bal  = await _get_or_create_balance(
            tenant_id, str(req.employee_id), str(req.leave_type_id), year, db
        )
        bal.used_days += req.days

    else:  # reject
        req.status           = LeaveStatus.rejected
        req.approved_by      = approved_by
        req.approved_by_name = approver_name
        req.approved_at      = datetime.utcnow()
        req.rejection_reason = payload.rejection_reason

    await db.commit()
    await db.refresh(req)

    # Notify employee
    from app.tasks.leave_tasks import notify_employee_decision
    notify_employee_decision.delay(req.id, payload.action)

    return req


async def cancel_leave_request(
    tenant_id:    str,
    request_id:   str,
    cancelled_by: str,
    db:           AsyncSession,
) -> LeaveRequest:
    req = await get_leave_request_by_id(tenant_id, request_id, db)

    # Load requester's employee record to check ownership
    emp_row = await db.execute(
        select(Employee).where(
            Employee.user_id   == cancelled_by,
            Employee.tenant_id == tenant_id,
        )
    )
    emp = emp_row.scalar_one_or_none()

    is_owner = emp and str(emp.id) == str(req.employee_id)
    if not is_owner:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only cancel your own leave requests.")

    if req.status not in (LeaveStatus.pending, LeaveStatus.approved):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only pending or approved requests can be cancelled.",
        )

    # Restore balance if approved
    if req.status == LeaveStatus.approved:
        year = req.start_date.year
        bal  = await _get_or_create_balance(
            tenant_id, str(req.employee_id), str(req.leave_type_id), year, db
        )
        bal.used_days = max(bal.used_days - req.days, 0)

    req.status       = LeaveStatus.cancelled
    req.cancelled_at = datetime.utcnow()

    await db.commit()
    await db.refresh(req)
    return req


# ─────────────────────────────────────────────────────────────────────────────
# Leave Balance
# ─────────────────────────────────────────────────────────────────────────────

async def get_leave_balance(
    tenant_id: str, employee_id: str, db: AsyncSession
) -> LeaveBalanceResponse:
    year = datetime.utcnow().year

    # Load employee
    emp_row = await db.execute(
        select(Employee).where(
            Employee.id        == employee_id,
            Employee.tenant_id == tenant_id,
        )
    )
    emp = emp_row.scalar_one_or_none()
    if not emp:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Employee not found.")

    # Active leave types
    lt_rows = await db.execute(
        select(LeaveType).where(
            LeaveType.tenant_id == tenant_id,
            LeaveType.is_active.is_(True),
        ).order_by(LeaveType.name)
    )
    leave_types = lt_rows.scalars().all()

    balance_items: list[LeaveBalanceItem] = []
    for lt in leave_types:
        bal = await _get_or_create_balance(tenant_id, employee_id, str(lt.id), year, db)
        balance_items.append(LeaveBalanceItem(
            leave_type_id    = str(lt.id),
            leave_type_name  = lt.name,
            leave_type_color = lt.color,
            is_paid          = lt.is_paid,
            total_days       = bal.total_days,
            used_days        = bal.used_days,
            remaining_days   = max(bal.total_days - bal.used_days, 0),
            carried_forward  = bal.carried_forward,
        ))

    await db.commit()  # commit any auto-created balance rows

    return LeaveBalanceResponse(
        employee_id   = employee_id,
        employee_name = f"{emp.first_name} {emp.last_name}",
        year          = year,
        balances      = balance_items,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Leave Calendar
# ─────────────────────────────────────────────────────────────────────────────

async def get_leave_calendar(
    tenant_id:     str,
    month:         int,
    year:          int,
    department_id: Optional[str],
    db:            AsyncSession,
) -> list[LeaveCalendarEntry]:
    """Return all approved leaves for the given month as daily entries."""
    from calendar import monthrange

    last_day = monthrange(year, month)[1]
    start    = date(year, month, 1)
    end      = date(year, month, last_day)

    q = (
        select(LeaveRequest)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
        .where(
            LeaveRequest.tenant_id == tenant_id,
            LeaveRequest.status    == LeaveStatus.approved,
            LeaveRequest.start_date <= end,
            LeaveRequest.end_date   >= start,
        )
        .options(
            selectinload(LeaveRequest.employee),
            selectinload(LeaveRequest.leave_type),
        )
    )
    if department_id:
        q = q.where(Employee.department_id == department_id)

    rows     = await db.execute(q)
    requests = rows.scalars().all()

    entries: list[LeaveCalendarEntry] = []
    for req in requests:
        # Expand each request into individual date entries
        cur = max(req.start_date, start)
        req_end = min(req.end_date, end)
        while cur <= req_end:
            if cur.weekday() < 5:  # skip weekends in calendar
                entries.append(LeaveCalendarEntry(
                    date             = cur,
                    employee_id      = str(req.employee_id),
                    employee_name    = f"{req.employee.first_name} {req.employee.last_name}",
                    employee_code    = req.employee.employee_code,
                    photo_url        = req.employee.photo_url,
                    leave_type_id    = str(req.leave_type_id),
                    leave_type_name  = req.leave_type.name,
                    leave_type_color = req.leave_type.color,
                    status           = req.status,
                ))
            cur += timedelta(days=1)

    return entries


# ─────────────────────────────────────────────────────────────────────────────
# Public Holidays
# ─────────────────────────────────────────────────────────────────────────────

async def get_public_holidays(
    tenant_id: str, year: int, db: AsyncSession
) -> list[PublicHoliday]:
    rows = await db.execute(
        select(PublicHoliday).where(
            PublicHoliday.tenant_id == tenant_id,
            or_(
                PublicHoliday.date.between(date(year, 1, 1), date(year, 12, 31)),
                PublicHoliday.is_recurring.is_(True),
            ),
        ).order_by(PublicHoliday.date)
    )
    return rows.scalars().all()


async def create_public_holiday(
    tenant_id: str, data: PublicHolidayCreate, db: AsyncSession
) -> PublicHoliday:
    holiday = PublicHoliday(tenant_id=tenant_id, **data.model_dump())
    db.add(holiday)
    await db.flush()
    await db.refresh(holiday)
    await db.commit()
    return holiday


async def delete_public_holiday(
    tenant_id: str, holiday_id: str, db: AsyncSession
) -> None:
    row = await db.execute(
        select(PublicHoliday).where(
            PublicHoliday.id        == holiday_id,
            PublicHoliday.tenant_id == tenant_id,
        )
    )
    h = row.scalar_one_or_none()
    if not h:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Public holiday not found.")
    await db.delete(h)
    await db.commit()

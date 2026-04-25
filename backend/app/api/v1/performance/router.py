"""
AI-HRMS — Performance Management router.

Endpoints
─────────
Appraisal Cycles
  GET    /performance/cycles                  → list
  POST   /performance/cycles                  → create  (HR only)
  GET    /performance/cycles/{id}             → detail
  POST   /performance/cycles/{id}/launch      → launch  (HR only)
  POST   /performance/cycles/{id}/close       → close   (HR only)

Goals
  GET    /performance/goals                   → list by employee + cycle
  PUT    /performance/goals/bulk              → replace all goals for employee+cycle
  PATCH  /performance/goals/{id}             → update achievement/status
  DELETE /performance/goals/{id}             → delete  (HR only)

Appraisals
  GET    /performance/appraisals              → list (scoped by role)
  GET    /performance/appraisals/me           → my current appraisal
  GET    /performance/appraisals/{id}         → detail
  POST   /performance/appraisals/{id}/self-review     → submit self review
  POST   /performance/appraisals/{id}/manager-review  → submit manager review

Bell Curve & Team
  GET    /performance/cycles/{id}/bell-curve  → distribution
  GET    /performance/cycles/{id}/team        → team summary (manager view)

PIPs
  GET    /performance/pips                    → list for employee
  POST   /performance/pips                    → create standalone PIP
  PATCH  /performance/pips/{id}              → update PIP

Reports
  GET    /performance/cycles/{id}/report      → PDF download (HR only)
"""

from __future__ import annotations

import io
from typing import Annotated, Optional
from uuid   import UUID

from fastapi              import APIRouter, Depends, Query, status
from fastapi.responses    import StreamingResponse
from sqlalchemy           import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.models         import Employee
from app.models.tenant  import User

from app.api.v1.performance import service
from app.api.v1.performance.schemas import (
    AppraisalCycleCreate,
    AppraisalCycleListResponse,
    AppraisalCycleResponse,
    AppraisalFilterParams,
    AppraisalListResponse,
    AppraisalResponse,
    BellCurveData,
    GoalResponse,
    GoalsBulkSet,
    GoalUpdate,
    ManagerReviewSubmit,
    PIPCreate,
    PIPResponse,
    PIPUpdate,
    SelfReviewSubmit,
    TeamPerformanceSummary,
)

router = APIRouter(prefix="/performance", tags=["Performance"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_employee(user: User, db: AsyncSession) -> Employee:
    """Resolve the Employee record for the current user."""
    emp = (await db.execute(
        select(Employee).where(
            Employee.user_id   == user.id,
            Employee.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()
    if not emp:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Employee profile not found for this user")
    return emp


def _is_hr(user: User) -> bool:
    if user.is_superadmin:
        return True
    perms = getattr(user, "permissions", [])
    return any(getattr(p, "module_name", "") in ("hr", "performance") for p in perms)


# ─────────────────────────────────────────────────────────────────────────────
# Appraisal Cycles
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cycles",
    response_model=AppraisalCycleListResponse,
    summary="List appraisal cycles",
)
async def list_cycles(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    page:         int = Query(1,  ge=1),
    page_size:    int = Query(20, ge=1, le=100),
):
    total, cycles = await service.get_appraisal_cycles(
        tenant_id = current_user.tenant_id,
        db        = db,
        page      = page,
        page_size = page_size,
    )
    return AppraisalCycleListResponse(count=total, results=cycles)


@router.post(
    "/cycles",
    response_model=AppraisalCycleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an appraisal cycle (HR only)",
)
async def create_cycle(
    body:         AppraisalCycleCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("performance", "write"),
):
    cycle = await service.create_appraisal_cycle(
        tenant_id = current_user.tenant_id,
        data      = body,
        db        = db,
    )
    return cycle


@router.get(
    "/cycles/{cycle_id}",
    response_model=AppraisalCycleResponse,
    summary="Get appraisal cycle detail",
)
async def get_cycle(
    cycle_id:     UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.get_appraisal_cycle(current_user.tenant_id, cycle_id, db)


@router.post(
    "/cycles/{cycle_id}/launch",
    response_model=AppraisalCycleResponse,
    summary="Launch a cycle — creates appraisal records for all active employees (HR only)",
)
async def launch_cycle(
    cycle_id:     UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("performance", "write"),
):
    return await service.launch_cycle(current_user.tenant_id, cycle_id, db)


@router.post(
    "/cycles/{cycle_id}/close",
    response_model=AppraisalCycleResponse,
    summary="Close / complete a cycle (HR only)",
)
async def close_cycle(
    cycle_id:     UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("performance", "write"),
):
    return await service.close_cycle(current_user.tenant_id, cycle_id, db)


# ─────────────────────────────────────────────────────────────────────────────
# Goals
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/goals",
    response_model=list[GoalResponse],
    summary="Get goals for an employee (and optionally a cycle)",
)
async def list_goals(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    employee_id:  Optional[UUID] = Query(None),
    cycle_id:     Optional[UUID] = Query(None),
):
    # Default to the requesting employee if not specified
    if employee_id is None:
        emp = await _get_employee(current_user, db)
        employee_id = emp.id

    return await service.get_goals(
        tenant_id   = current_user.tenant_id,
        employee_id = employee_id,
        cycle_id    = cycle_id,
        db          = db,
    )


@router.put(
    "/goals/bulk",
    response_model=list[GoalResponse],
    summary="Replace all goals for an employee+cycle atomically",
)
async def bulk_set_goals(
    body:         GoalsBulkSet,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.set_goals(
        tenant_id = current_user.tenant_id,
        data      = body,
        db        = db,
    )


@router.patch(
    "/goals/{goal_id}",
    response_model=GoalResponse,
    summary="Update goal achievement / status",
)
async def update_goal(
    goal_id:      UUID,
    body:         GoalUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.update_goal_achievement(
        tenant_id = current_user.tenant_id,
        goal_id   = goal_id,
        data      = body,
        db        = db,
    )


@router.delete(
    "/goals/{goal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a goal (HR only)",
)
async def delete_goal(
    goal_id:      UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("performance", "write"),
):
    await service.delete_goal(current_user.tenant_id, goal_id, db)


# ─────────────────────────────────────────────────────────────────────────────
# Appraisals
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/appraisals/me",
    response_model=Optional[AppraisalResponse],
    summary="Get my current-cycle appraisal",
)
async def my_appraisal(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return await service.get_my_current_appraisal(current_user.tenant_id, emp, db)


@router.get(
    "/appraisals",
    response_model=AppraisalListResponse,
    summary="List appraisals (scoped by role: HR sees all, manager sees team, employee sees own)",
)
async def list_appraisals(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    cycle_id:     Optional[UUID]  = Query(None),
    employee_id:  Optional[UUID]  = Query(None),
    appraisal_status: Optional[str] = Query(None, alias="status"),
    page:         int = Query(1,  ge=1),
    page_size:    int = Query(20, ge=1, le=100),
):
    emp = await _get_employee(current_user, db)
    filters = AppraisalFilterParams(
        cycle_id    = str(cycle_id)    if cycle_id    else None,
        employee_id = str(employee_id) if employee_id else None,
        status      = appraisal_status,
        page        = page,
        page_size   = page_size,
    )
    total, rows = await service.get_appraisals(
        tenant_id       = current_user.tenant_id,
        filters         = filters,
        requesting_emp  = emp,
        db              = db,
    )
    return AppraisalListResponse(count=total, results=rows)


@router.get(
    "/appraisals/{appraisal_id}",
    response_model=AppraisalResponse,
    summary="Get appraisal detail",
)
async def get_appraisal(
    appraisal_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return await service.get_appraisal(current_user.tenant_id, appraisal_id, emp, db)


@router.post(
    "/appraisals/{appraisal_id}/self-review",
    response_model=AppraisalResponse,
    summary="Submit self review",
)
async def submit_self_review(
    appraisal_id: UUID,
    body:         SelfReviewSubmit,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return await service.submit_self_review(
        tenant_id    = current_user.tenant_id,
        appraisal_id = appraisal_id,
        data         = body,
        submitted_by = emp,
        db           = db,
    )


@router.post(
    "/appraisals/{appraisal_id}/manager-review",
    response_model=AppraisalResponse,
    summary="Submit manager review (manager or HR)",
)
async def submit_manager_review(
    appraisal_id: UUID,
    body:         ManagerReviewSubmit,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return await service.submit_manager_review(
        tenant_id    = current_user.tenant_id,
        appraisal_id = appraisal_id,
        data         = body,
        reviewer     = emp,
        db           = db,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Bell Curve & Team Summary
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cycles/{cycle_id}/bell-curve",
    response_model=BellCurveData,
    summary="Rating distribution (bell curve) for a cycle",
)
async def bell_curve(
    cycle_id:     UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.calculate_bell_curve(current_user.tenant_id, cycle_id, db)


@router.get(
    "/cycles/{cycle_id}/team",
    response_model=TeamPerformanceSummary,
    summary="Team performance summary for a manager",
)
async def team_summary(
    cycle_id:     UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return await service.get_team_performance_summary(
        tenant_id  = current_user.tenant_id,
        manager_id = emp.id,
        cycle_id   = cycle_id,
        db         = db,
    )


# ─────────────────────────────────────────────────────────────────────────────
# PIPs
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/pips",
    response_model=list[PIPResponse],
    summary="List PIPs for an employee",
)
async def list_pips(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    employee_id:  Optional[UUID] = Query(None),
):
    if employee_id is None:
        emp = await _get_employee(current_user, db)
        employee_id = emp.id
    return await service.get_employee_pips(current_user.tenant_id, employee_id, db)


@router.post(
    "/pips",
    response_model=PIPResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a standalone PIP (manager/HR)",
)
async def create_pip(
    body:         PIPCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return await service.create_pip(
        tenant_id     = current_user.tenant_id,
        data          = body,
        created_by_id = emp.id,
        db            = db,
    )


@router.patch(
    "/pips/{pip_id}",
    response_model=PIPResponse,
    summary="Update PIP status / notes / action items",
)
async def update_pip(
    pip_id:       UUID,
    body:         PIPUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.update_pip(current_user.tenant_id, pip_id, body, db)


# ─────────────────────────────────────────────────────────────────────────────
# Report
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cycles/{cycle_id}/report",
    summary="Download appraisal report PDF (HR only)",
)
async def download_report(
    cycle_id:     UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("performance", "read"),
):
    data = await service.generate_appraisal_report(current_user.tenant_id, cycle_id, db)

    # Try PDF; fallback to plain text
    content_type = "application/pdf" if data[:4] == b"%PDF" else "text/plain"
    filename     = f"appraisal_report_{cycle_id}.pdf"

    return StreamingResponse(
        io.BytesIO(data),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

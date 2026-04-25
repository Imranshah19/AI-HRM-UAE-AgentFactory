"""
AI-HRMS — Training Management router.

Endpoints
─────────
GET    /training/stats                          → stats for current user
GET    /training/programs                       → list
POST   /training/programs                       → create  (HR only)
GET    /training/programs/{id}                  → detail + enrollments
PATCH  /training/programs/{id}                 → update  (HR only)
DELETE /training/programs/{id}                 → delete  (HR / planned only)
POST   /training/programs/{id}/status          → change status (HR only)

GET    /training/programs/{id}/enrollments      → list enrollments
POST   /training/programs/{id}/enroll           → enroll employees
PATCH  /training/enrollments/{id}              → update enrollment (score, status, cert)

GET    /training/my                             → my enrollments
"""

from __future__ import annotations

from typing import Annotated, Optional
from uuid   import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.models         import Employee
from app.models.tenant  import User

from app.api.v1.training import service
from app.api.v1.training.schemas import (
    EnrollmentCreate,
    EnrollmentResponse,
    EnrollmentUpdate,
    TrainingFilterParams,
    TrainingProgramCreate,
    TrainingProgramListResponse,
    TrainingProgramResponse,
    TrainingProgramUpdate,
    TrainingStats,
)

router = APIRouter(prefix="/training", tags=["Training"])


# ─── Helpers ──────────────────────────────────────────────────────────────────

async def _get_employee(user: User, db: AsyncSession) -> Employee | None:
    return (await db.execute(
        select(Employee).where(
            Employee.user_id   == user.id,
            Employee.tenant_id == user.tenant_id,
        )
    )).scalar_one_or_none()


# ─── Stats ────────────────────────────────────────────────────────────────────

@router.get(
    "/stats",
    response_model=TrainingStats,
    summary="Training stats for the current user/tenant",
)
async def training_stats(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    return await service.get_stats(
        tenant_id   = current_user.tenant_id,
        employee_id = emp.id if emp else None,
        db          = db,
    )


# ─── Programs ─────────────────────────────────────────────────────────────────

@router.get(
    "/programs",
    response_model=TrainingProgramListResponse,
    summary="List training programs",
)
async def list_programs(
    current_user:  Annotated[User, Depends(get_current_user)],
    db:            AsyncSession = Depends(get_db),
    status_filter: Optional[str]  = Query(None, alias="status"),
    category:      Optional[str]  = Query(None),
    is_mandatory:  Optional[bool] = Query(None),
    search:        Optional[str]  = Query(None),
    page:          int = Query(1,  ge=1),
    page_size:     int = Query(20, ge=1, le=100),
):
    filters = TrainingFilterParams(
        status       = status_filter,
        category     = category,
        is_mandatory = is_mandatory,
        search       = search,
        page         = page,
        page_size    = page_size,
    )
    total, programs = await service.get_programs(current_user.tenant_id, filters, db)
    return TrainingProgramListResponse(count=total, results=programs)


@router.post(
    "/programs",
    response_model=TrainingProgramResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a training program (HR only)",
)
async def create_program(
    body:         TrainingProgramCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("training", "write"),
):
    emp = await _get_employee(current_user, db)
    created_by = emp.id if emp else current_user.id
    return await service.create_program(
        tenant_id  = current_user.tenant_id,
        data       = body,
        created_by = created_by,
        db         = db,
    )


@router.get(
    "/programs/{program_id}",
    response_model=TrainingProgramResponse,
    summary="Get training program detail (includes enrollments count)",
)
async def get_program(
    program_id:   UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.get_program(current_user.tenant_id, program_id, db)


@router.patch(
    "/programs/{program_id}",
    response_model=TrainingProgramResponse,
    summary="Update training program (HR only)",
)
async def update_program(
    program_id:   UUID,
    body:         TrainingProgramUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("training", "write"),
):
    return await service.update_program(current_user.tenant_id, program_id, body, db)


@router.delete(
    "/programs/{program_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a planned/cancelled training program (HR only)",
)
async def delete_program(
    program_id:   UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("training", "write"),
):
    await service.delete_program(current_user.tenant_id, program_id, db)


@router.post(
    "/programs/{program_id}/status",
    response_model=TrainingProgramResponse,
    summary="Change program status (HR only)",
)
async def change_status(
    program_id:   UUID,
    new_status:   str = Query(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db:           AsyncSession = Depends(get_db),
    _perm = require_permission("training", "write"),
):
    return await service.update_program_status(
        current_user.tenant_id, program_id, new_status, db
    )


# ─── Enrollments ──────────────────────────────────────────────────────────────

@router.get(
    "/programs/{program_id}/enrollments",
    response_model=list[EnrollmentResponse],
    summary="List all enrollments for a program",
)
async def list_enrollments(
    program_id:   UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    return await service.get_enrollments(current_user.tenant_id, program_id, db)


@router.post(
    "/programs/{program_id}/enroll",
    response_model=list[EnrollmentResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Enroll employees in a training program",
)
async def enroll_employees(
    program_id:   UUID,
    body:         EnrollmentCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    enrolled_by = emp.id if emp else current_user.id
    return await service.enroll_employees(
        tenant_id   = current_user.tenant_id,
        program_id  = program_id,
        data        = body,
        enrolled_by = enrolled_by,
        db          = db,
    )


@router.patch(
    "/enrollments/{enrollment_id}",
    response_model=EnrollmentResponse,
    summary="Update enrollment (score, status, certificate, feedback)",
)
async def update_enrollment(
    enrollment_id: UUID,
    body:          EnrollmentUpdate,
    current_user:  Annotated[User, Depends(get_current_user)],
    db:            AsyncSession = Depends(get_db),
):
    return await service.update_enrollment(
        tenant_id     = current_user.tenant_id,
        enrollment_id = enrollment_id,
        data          = body,
        db            = db,
    )


# ─── Employee portal ─────────────────────────────────────────────────────────

@router.get(
    "/my",
    response_model=list[EnrollmentResponse],
    summary="My training enrollments",
)
async def my_trainings(
    current_user: Annotated[User, Depends(get_current_user)],
    db:           AsyncSession = Depends(get_db),
):
    emp = await _get_employee(current_user, db)
    if not emp:
        return []
    return await service.get_my_enrollments(current_user.tenant_id, emp.id, db)

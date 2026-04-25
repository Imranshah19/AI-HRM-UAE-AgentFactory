"""
AI-HRMS — Training Management service layer.
All DB operations are tenant-scoped; every function receives tenant_id explicitly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing   import Optional
from uuid     import UUID

from fastapi              import HTTPException, status
from sqlalchemy           import and_, func, or_, select, update
from sqlalchemy.orm       import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training  import TrainingProgram, TrainingEnrollment
from app.models.employee  import Employee

from app.api.v1.training.schemas import (
    EnrollmentCreate,
    EnrollmentUpdate,
    TrainingFilterParams,
    TrainingProgramCreate,
    TrainingProgramUpdate,
    TrainingStats,
)

logger = logging.getLogger(__name__)


def _str(v) -> str | None:
    return str(v) if v is not None else None


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ─── Programs ─────────────────────────────────────────────────────────────────

async def create_program(
    tenant_id: UUID,
    data:      TrainingProgramCreate,
    created_by: UUID,
    db:        AsyncSession,
) -> TrainingProgram:
    program = TrainingProgram(
        tenant_id                   = tenant_id,
        title                       = data.title,
        description                 = data.description,
        category                    = data.category,
        skills_covered              = data.skills_covered,
        trainer                     = data.trainer,
        trainer_id                  = data.trainer_id,
        mode                        = data.mode,
        venue                       = data.venue,
        meeting_link                = data.meeting_link,
        start_date                  = data.start_date,
        end_date                    = data.end_date,
        duration_hours              = data.duration_hours,
        max_participants            = data.max_participants,
        min_participants            = data.min_participants,
        cost_per_participant        = data.cost_per_participant,
        currency                    = data.currency,
        is_mandatory                = data.is_mandatory,
        issues_certificate          = data.issues_certificate,
        certificate_validity_months = data.certificate_validity_months,
        material_url                = data.material_url,
        external_url                = data.external_url,
        status                      = "planned",
        created_by                  = created_by,
    )
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return program


async def get_programs(
    tenant_id: UUID,
    filters:   TrainingFilterParams,
    db:        AsyncSession,
) -> tuple[int, list[TrainingProgram]]:
    q = (
        select(TrainingProgram)
        .options(selectinload(TrainingProgram.enrollments))
        .where(TrainingProgram.tenant_id == tenant_id)
    )

    if filters.status:
        q = q.where(TrainingProgram.status == filters.status)
    if filters.category:
        q = q.where(TrainingProgram.category.ilike(f"%{filters.category}%"))
    if filters.is_mandatory is not None:
        q = q.where(TrainingProgram.is_mandatory == filters.is_mandatory)
    if filters.search:
        term = f"%{filters.search}%"
        q = q.where(
            or_(
                TrainingProgram.title.ilike(term),
                TrainingProgram.description.ilike(term),
                TrainingProgram.category.ilike(term),
            )
        )

    q = q.order_by(TrainingProgram.start_date.desc().nullslast(), TrainingProgram.created_at.desc())

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    offset = (filters.page - 1) * filters.page_size
    rows   = (await db.execute(q.offset(offset).limit(filters.page_size))).scalars().all()
    return total, list(rows)


async def get_program(tenant_id: UUID, program_id: UUID, db: AsyncSession) -> TrainingProgram:
    row = (await db.execute(
        select(TrainingProgram)
        .options(selectinload(TrainingProgram.enrollments).selectinload(TrainingEnrollment.employee))
        .where(TrainingProgram.id == program_id, TrainingProgram.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Training program not found")
    return row


async def update_program(
    tenant_id:  UUID,
    program_id: UUID,
    data:       TrainingProgramUpdate,
    db:         AsyncSession,
) -> TrainingProgram:
    program = await get_program(tenant_id, program_id, db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(program, field, value)
    await db.commit()
    await db.refresh(program)
    return program


async def delete_program(tenant_id: UUID, program_id: UUID, db: AsyncSession) -> None:
    program = await get_program(tenant_id, program_id, db)
    # Only allow deletion of planned/cancelled programs
    if program.status not in ("planned", "cancelled"):
        raise HTTPException(400, "Cannot delete an active or completed program")
    await db.delete(program)
    await db.commit()


async def update_program_status(
    tenant_id:  UUID,
    program_id: UUID,
    new_status: str,
    db:         AsyncSession,
) -> TrainingProgram:
    allowed = ("planned", "registration_open", "ongoing", "completed", "cancelled")
    if new_status not in allowed:
        raise HTTPException(400, f"Invalid status: {new_status}")
    program = await get_program(tenant_id, program_id, db)
    program.status = new_status
    await db.commit()
    await db.refresh(program)
    return program


# ─── Enrollments ──────────────────────────────────────────────────────────────

async def enroll_employees(
    tenant_id:   UUID,
    program_id:  UUID,
    data:        EnrollmentCreate,
    enrolled_by: UUID,
    db:          AsyncSession,
) -> list[TrainingEnrollment]:
    program = await get_program(tenant_id, program_id, db)

    if program.status not in ("registration_open", "planned", "ongoing"):
        raise HTTPException(400, "Program is not accepting enrollments")

    if program.max_participants:
        current_count = len([e for e in program.enrollments if e.status != "dropped"])
        remaining     = program.max_participants - current_count
        if remaining < len(data.employee_ids):
            raise HTTPException(400, f"Only {remaining} seat(s) remaining")

    enrollments = []
    for emp_id in data.employee_ids:
        # Check if already enrolled (not dropped)
        existing = (await db.execute(
            select(TrainingEnrollment).where(
                TrainingEnrollment.program_id  == program_id,
                TrainingEnrollment.employee_id == emp_id,
                TrainingEnrollment.status.notin_(["dropped"]),
            )
        )).scalar_one_or_none()
        if existing:
            continue   # skip duplicates silently

        enrollment = TrainingEnrollment(
            program_id   = program_id,
            employee_id  = emp_id,
            status       = "enrolled",
            nominated_by = data.nominated_by or enrolled_by,
        )
        db.add(enrollment)
        enrollments.append(enrollment)

    await db.commit()
    for e in enrollments:
        await db.refresh(e)
    return enrollments


async def get_enrollments(
    tenant_id:  UUID,
    program_id: UUID,
    db:         AsyncSession,
) -> list[TrainingEnrollment]:
    program = await get_program(tenant_id, program_id, db)   # ensures tenant ownership
    rows = (await db.execute(
        select(TrainingEnrollment)
        .options(selectinload(TrainingEnrollment.employee))
        .where(TrainingEnrollment.program_id == program_id)
        .order_by(TrainingEnrollment.enrolled_at)
    )).scalars().all()
    return list(rows)


async def update_enrollment(
    tenant_id:     UUID,
    enrollment_id: UUID,
    data:          EnrollmentUpdate,
    db:            AsyncSession,
) -> TrainingEnrollment:
    enrollment = (await db.execute(
        select(TrainingEnrollment)
        .options(selectinload(TrainingEnrollment.program))
        .where(TrainingEnrollment.id == enrollment_id)
    )).scalar_one_or_none()
    if not enrollment:
        raise HTTPException(404, "Enrollment not found")
    # Verify tenant ownership via program
    if str(enrollment.program.tenant_id) != str(tenant_id):
        raise HTTPException(403, "Access denied")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(enrollment, field, value)

    if data.status == "completed" and enrollment.completed_at is None:
        enrollment.completed_at = _now()

    # Auto-issue certificate if program issues_certificate and status=completed
    if (data.status == "completed"
            and enrollment.program.issues_certificate
            and enrollment.certificate_issued_at is None):
        from datetime import date, timedelta
        today = date.today()
        enrollment.certificate_issued_at = today
        months = enrollment.program.certificate_validity_months
        if months:
            enrollment.certificate_expires_at = date(
                today.year + months // 12,
                today.month + months % 12 if today.month + months % 12 <= 12
                else today.month + months % 12 - 12,
                today.day,
            )

    await db.commit()
    await db.refresh(enrollment)
    return enrollment


async def get_my_enrollments(
    tenant_id:   UUID,
    employee_id: UUID,
    db:          AsyncSession,
) -> list[TrainingEnrollment]:
    rows = (await db.execute(
        select(TrainingEnrollment)
        .options(selectinload(TrainingEnrollment.program))
        .where(
            TrainingEnrollment.employee_id == employee_id,
        )
        .order_by(TrainingEnrollment.enrolled_at.desc())
    )).scalars().all()

    # Filter by tenant via program
    return [r for r in rows if str(r.program.tenant_id) == str(tenant_id)]


# ─── Stats ────────────────────────────────────────────────────────────────────

async def get_stats(
    tenant_id:   UUID,
    employee_id: Optional[UUID],
    db:          AsyncSession,
):
    from app.api.v1.training.schemas import TrainingStats

    total_programs = (await db.execute(
        select(func.count(TrainingProgram.id))
        .where(TrainingProgram.tenant_id == tenant_id)
    )).scalar_one()

    active_programs = (await db.execute(
        select(func.count(TrainingProgram.id))
        .where(
            TrainingProgram.tenant_id == tenant_id,
            TrainingProgram.status == "ongoing",
        )
    )).scalar_one()

    completed_programs = (await db.execute(
        select(func.count(TrainingProgram.id))
        .where(
            TrainingProgram.tenant_id == tenant_id,
            TrainingProgram.status == "completed",
        )
    )).scalar_one()

    # Total enrollments across all tenant programs
    total_enrollments = (await db.execute(
        select(func.count(TrainingEnrollment.id))
        .join(TrainingProgram, TrainingEnrollment.program_id == TrainingProgram.id)
        .where(TrainingProgram.tenant_id == tenant_id)
    )).scalar_one()

    completed_enrollments = (await db.execute(
        select(func.count(TrainingEnrollment.id))
        .join(TrainingProgram, TrainingEnrollment.program_id == TrainingProgram.id)
        .where(
            TrainingProgram.tenant_id == tenant_id,
            TrainingEnrollment.status == "completed",
        )
    )).scalar_one()

    completion_rate = (
        round(completed_enrollments / total_enrollments * 100, 1)
        if total_enrollments > 0 else 0.0
    )

    # Mandatory programs not yet completed by this employee
    mandatory_pending = 0
    if employee_id:
        # Programs that are mandatory + active/open
        mandatory_programs = (await db.execute(
            select(TrainingProgram.id)
            .where(
                TrainingProgram.tenant_id  == tenant_id,
                TrainingProgram.is_mandatory == True,
                TrainingProgram.status.in_(["registration_open", "ongoing"]),
            )
        )).scalars().all()

        if mandatory_programs:
            completed_mandatory = (await db.execute(
                select(func.count(TrainingEnrollment.id))
                .where(
                    TrainingEnrollment.program_id.in_(mandatory_programs),
                    TrainingEnrollment.employee_id == employee_id,
                    TrainingEnrollment.status == "completed",
                )
            )).scalar_one()
            mandatory_pending = len(mandatory_programs) - completed_mandatory

    return TrainingStats(
        total_programs    = total_programs,
        active_programs   = active_programs,
        completed         = completed_programs,
        total_enrollments = total_enrollments,
        completion_rate   = completion_rate,
        mandatory_pending = mandatory_pending,
    )

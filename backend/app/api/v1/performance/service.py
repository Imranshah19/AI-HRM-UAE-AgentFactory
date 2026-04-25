"""
AI-HRMS — Performance Management service layer.
All DB operations are tenant-scoped; every function receives tenant_id explicitly.
"""

from __future__ import annotations

import io
import logging
import os
from datetime import date, datetime, timezone
from typing   import Optional
from uuid     import UUID

from fastapi                 import HTTPException, status
from sqlalchemy              import and_, delete, func, select, update
from sqlalchemy.orm          import selectinload
from sqlalchemy.ext.asyncio  import AsyncSession

from app.models.performance  import AppraisalCycle, Appraisal, Goal
from app.models.employee     import Employee
from app.models.notification import Notification

from app.api.v1.performance.schemas import (
    AppraisalCycleCreate,
    AppraisalFilterParams,
    BellCurveBucket,
    BellCurveData,
    EmployeeMinimal,
    GoalCreate,
    GoalsBulkSet,
    GoalUpdate,
    KPIScoreEntry,
    ManagerReviewSubmit,
    PIPCreate,
    PIPUpdate,
    SelfReviewSubmit,
    TeamMemberSummary,
    TeamPerformanceSummary,
)

logger = logging.getLogger(__name__)

APPRAISAL_REPORT_DIR = os.environ.get("APPRAISAL_REPORT_DIR", "/tmp/appraisal_reports")

RATING_LABELS = {
    1: "Poor",
    2: "Below Expectations",
    3: "Meets Expectations",
    4: "Exceeds Expectations",
    5: "Outstanding",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _str(v) -> str | None:
    return str(v) if v is not None else None


def _emp_minimal(emp: Employee) -> EmployeeMinimal:
    return EmployeeMinimal(
        id            = _str(emp.id),
        employee_code = emp.employee_code,
        full_name     = f"{emp.first_name} {emp.last_name}",
        photo_url     = getattr(emp, "photo_url", None),
        department    = emp.department.name if getattr(emp, "department", None) else None,
        designation   = emp.designation.title if getattr(emp, "designation", None) else None,
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _calc_avg_competency(scores: dict) -> float:
    """Average of 5 competency scores."""
    if not scores:
        return 0.0
    return sum(scores.values()) / len(scores)


def _calc_weighted_kpi(kpi_scores: dict[str, float], goals: list[Goal]) -> float:
    """Weighted KPI score: sum(score * weight / 100) for each goal."""
    goal_weights = {_str(g.id): float(g.weight) for g in goals}
    total_weight = sum(goal_weights.values())
    if total_weight == 0:
        return 0.0
    weighted = sum(
        kpi_scores.get(gid, 0) * (w / total_weight)
        for gid, w in goal_weights.items()
    )
    return round(weighted, 2)


async def _notify(db: AsyncSession, tenant_id: UUID, employee_id: UUID,
                  message: str, link: str | None = None) -> None:
    try:
        notif = Notification(
            tenant_id   = tenant_id,
            user_id     = employee_id,      # assumes user_id == employee_id for notifications
            message     = message,
            link        = link,
            is_read     = False,
        )
        db.add(notif)
    except Exception:
        pass   # notifications are best-effort


# ─── Appraisal Cycles ─────────────────────────────────────────────────────────

async def create_appraisal_cycle(
    tenant_id: UUID,
    data:      AppraisalCycleCreate,
    db:        AsyncSession,
) -> AppraisalCycle:
    cycle = AppraisalCycle(
        tenant_id                   = tenant_id,
        name                        = data.name,
        year                        = data.year,
        quarter                     = data.quarter,
        period_label                = data.period_label,
        start_date                  = data.start_date,
        end_date                    = data.end_date,
        self_review_deadline        = data.self_review_deadline,
        manager_review_deadline     = data.manager_review_deadline,
        status                      = "upcoming",
        rating_scale_min            = data.rating_scale_min,
        rating_scale_max            = data.rating_scale_max,
        self_review_instructions    = data.self_review_instructions,
        manager_review_instructions = data.manager_review_instructions,
    )
    db.add(cycle)
    await db.commit()
    await db.refresh(cycle)
    return cycle


async def get_appraisal_cycles(
    tenant_id: UUID,
    db:        AsyncSession,
    page:      int = 1,
    page_size: int = 20,
) -> tuple[int, list[AppraisalCycle]]:
    q = select(AppraisalCycle).where(
        AppraisalCycle.tenant_id == tenant_id,
    ).order_by(AppraisalCycle.year.desc(), AppraisalCycle.created_at.desc())

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    rows  = (await db.execute(q.offset((page - 1) * page_size).limit(page_size))).scalars().all()
    return total, list(rows)


async def get_appraisal_cycle(
    tenant_id: UUID,
    cycle_id:  UUID,
    db:        AsyncSession,
) -> AppraisalCycle:
    row = (await db.execute(
        select(AppraisalCycle).where(
            AppraisalCycle.id        == cycle_id,
            AppraisalCycle.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Appraisal cycle not found")
    return row


async def launch_cycle(
    tenant_id: UUID,
    cycle_id:  UUID,
    db:        AsyncSession,
) -> AppraisalCycle:
    cycle = await get_appraisal_cycle(tenant_id, cycle_id, db)
    if cycle.status not in ("upcoming", "draft"):
        raise HTTPException(400, "Cycle is already launched or completed")

    # Fetch all active employees in tenant
    employees = (await db.execute(
        select(Employee).where(
            Employee.tenant_id         == tenant_id,
            Employee.employment_status == "active",
        )
    )).scalars().all()

    # Create one Appraisal record per employee
    for emp in employees:
        # Check if already exists
        existing = (await db.execute(
            select(Appraisal).where(
                Appraisal.cycle_id    == cycle_id,
                Appraisal.employee_id == emp.id,
                Appraisal.tenant_id   == tenant_id,
            )
        )).scalar_one_or_none()
        if existing:
            continue

        appraisal = Appraisal(
            tenant_id   = tenant_id,
            cycle_id    = cycle_id,
            employee_id = emp.id,
            reviewer_id = getattr(emp, "manager_id", None),
            status      = "self_review_pending",
        )
        db.add(appraisal)

    cycle.status = "active"
    await db.commit()
    await db.refresh(cycle)

    # Async notification (fire-and-forget via Celery)
    try:
        from app.tasks.performance_tasks import send_appraisal_launch_notifications
        send_appraisal_launch_notifications.delay(str(cycle_id), str(tenant_id))
    except Exception:
        pass

    return cycle


async def close_cycle(
    tenant_id: UUID,
    cycle_id:  UUID,
    db:        AsyncSession,
) -> AppraisalCycle:
    cycle = await get_appraisal_cycle(tenant_id, cycle_id, db)
    if cycle.status == "completed":
        raise HTTPException(400, "Cycle is already completed")

    # Finalise any remaining appraisals that have manager review
    await db.execute(
        update(Appraisal)
        .where(
            Appraisal.cycle_id  == cycle_id,
            Appraisal.status    == "manager_review_submitted",
            Appraisal.tenant_id == tenant_id,
        )
        .values(status="completed", finalized_at=_now())
    )

    cycle.status = "completed"
    await db.commit()
    await db.refresh(cycle)

    try:
        from app.tasks.performance_tasks import generate_cycle_completion_report
        generate_cycle_completion_report.delay(str(cycle_id), str(tenant_id))
    except Exception:
        pass

    return cycle


# ─── Goals ────────────────────────────────────────────────────────────────────

async def set_goals(
    tenant_id: UUID,
    data:      GoalsBulkSet,
    db:        AsyncSession,
) -> list[Goal]:
    # Validate weights sum (already validated in schema, but double-check)
    total_weight = sum(g.weight for g in data.goals)
    if abs(total_weight - 100.0) > 0.01:
        raise HTTPException(400, f"Goal weights must sum to 100 (got {total_weight:.1f})")

    # Delete existing goals for this employee+cycle
    await db.execute(
        delete(Goal).where(
            Goal.tenant_id   == tenant_id,
            Goal.employee_id == data.employee_id,
            Goal.cycle_id    == data.cycle_id,
        )
    )

    new_goals = []
    for g in data.goals:
        goal = Goal(
            tenant_id    = tenant_id,
            employee_id  = data.employee_id,
            cycle_id     = data.cycle_id,
            title        = g.title,
            description  = g.description,
            category     = g.category,
            target       = g.target,
            target_value = g.target_value,
            weight       = g.weight,
            due_date     = g.due_date,
            status       = "active",
            set_by       = g.set_by,
        )
        db.add(goal)
        new_goals.append(goal)

    await db.commit()
    for g in new_goals:
        await db.refresh(g)
    return new_goals


async def get_goals(
    tenant_id:   UUID,
    employee_id: UUID,
    cycle_id:    Optional[UUID],
    db:          AsyncSession,
) -> list[Goal]:
    filters = [
        Goal.tenant_id   == tenant_id,
        Goal.employee_id == employee_id,
    ]
    if cycle_id:
        filters.append(Goal.cycle_id == cycle_id)
    rows = (await db.execute(select(Goal).where(and_(*filters)))).scalars().all()
    return list(rows)


async def update_goal_achievement(
    tenant_id: UUID,
    goal_id:   UUID,
    data:      GoalUpdate,
    db:        AsyncSession,
) -> Goal:
    goal = (await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not goal:
        raise HTTPException(404, "Goal not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(goal, field, value)

    await db.commit()
    await db.refresh(goal)
    return goal


async def delete_goal(tenant_id: UUID, goal_id: UUID, db: AsyncSession) -> None:
    goal = (await db.execute(
        select(Goal).where(Goal.id == goal_id, Goal.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not goal:
        raise HTTPException(404, "Goal not found")
    await db.delete(goal)
    await db.commit()


# ─── Appraisals ───────────────────────────────────────────────────────────────

async def get_appraisals(
    tenant_id:     UUID,
    filters:       AppraisalFilterParams,
    requesting_emp: Employee,
    db:            AsyncSession,
) -> tuple[int, list[Appraisal]]:
    q = (
        select(Appraisal)
        .options(
            selectinload(Appraisal.employee).selectinload(Employee.department),
            selectinload(Appraisal.employee).selectinload(Employee.designation),
            selectinload(Appraisal.reviewer),
        )
        .where(Appraisal.tenant_id == tenant_id)
    )

    # Visibility rules
    is_hr      = getattr(requesting_emp, "is_hr", False)
    is_manager = bool(getattr(requesting_emp, "manages", None))

    if not is_hr:
        if is_manager:
            # Manager sees own + direct reports
            from sqlalchemy import or_
            q = q.where(or_(
                Appraisal.employee_id == requesting_emp.id,
                Appraisal.reviewer_id == requesting_emp.id,
            ))
        else:
            # Regular employee sees own only
            q = q.where(Appraisal.employee_id == requesting_emp.id)

    if filters.cycle_id:
        q = q.where(Appraisal.cycle_id == filters.cycle_id)
    if filters.employee_id:
        q = q.where(Appraisal.employee_id == filters.employee_id)
    if filters.status:
        q = q.where(Appraisal.status == filters.status)

    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    offset = (filters.page - 1) * filters.page_size
    rows   = (await db.execute(q.offset(offset).limit(filters.page_size))).scalars().all()
    return total, list(rows)


async def get_appraisal(
    tenant_id:      UUID,
    appraisal_id:   UUID,
    requesting_emp: Employee,
    db:             AsyncSession,
) -> Appraisal:
    row = (await db.execute(
        select(Appraisal)
        .options(
            selectinload(Appraisal.employee).selectinload(Employee.department),
            selectinload(Appraisal.employee).selectinload(Employee.designation),
            selectinload(Appraisal.reviewer),
            selectinload(Appraisal.cycle),
        )
        .where(Appraisal.id == appraisal_id, Appraisal.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not row:
        raise HTTPException(404, "Appraisal not found")

    # Visibility check
    is_hr = getattr(requesting_emp, "is_hr", False)
    if not is_hr:
        if str(row.employee_id) != str(requesting_emp.id) and \
           str(row.reviewer_id) != str(requesting_emp.id):
            raise HTTPException(403, "Access denied")

    return row


async def get_my_current_appraisal(
    tenant_id: UUID,
    employee:  Employee,
    db:        AsyncSession,
) -> Appraisal | None:
    # Find active cycle
    cycle = (await db.execute(
        select(AppraisalCycle).where(
            AppraisalCycle.tenant_id == tenant_id,
            AppraisalCycle.status.in_(["active", "self_review", "manager_review"]),
        ).order_by(AppraisalCycle.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if not cycle:
        return None

    return (await db.execute(
        select(Appraisal)
        .options(selectinload(Appraisal.cycle))
        .where(
            Appraisal.tenant_id   == tenant_id,
            Appraisal.cycle_id    == cycle.id,
            Appraisal.employee_id == employee.id,
        )
    )).scalar_one_or_none()


async def submit_self_review(
    tenant_id:    UUID,
    appraisal_id: UUID,
    data:         SelfReviewSubmit,
    submitted_by: Employee,
    db:           AsyncSession,
) -> Appraisal:
    appraisal = (await db.execute(
        select(Appraisal).where(
            Appraisal.id        == appraisal_id,
            Appraisal.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not appraisal:
        raise HTTPException(404, "Appraisal not found")
    if str(appraisal.employee_id) != str(submitted_by.id):
        raise HTTPException(403, "You can only submit your own self-review")
    if appraisal.status not in ("self_review_pending", "not_started"):
        raise HTTPException(400, "Self review already submitted or not in the right state")

    # Load goals for KPI calculation
    goals = await get_goals(tenant_id, appraisal.employee_id, appraisal.cycle_id, db)

    # Build KPI score entries
    cycle = (await db.execute(
        select(AppraisalCycle).where(AppraisalCycle.id == appraisal.cycle_id)
    )).scalar_one_or_none()
    scale_max = float(cycle.rating_scale_max) if cycle else 5.0

    # Validate KPI scores are within scale
    for goal_id, score in data.kpi_scores.items():
        if not (1 <= score <= scale_max):
            raise HTTPException(400, f"KPI score for goal {goal_id} must be 1–{scale_max}")

    # Calculate weighted KPI rating
    self_kpi_rating = _calc_weighted_kpi(data.kpi_scores, goals)
    competency_avg  = _calc_avg_competency(data.competency_scores)
    # Self rating = weighted avg of kpi (60%) + competency (40%) normalised to scale
    self_rating = round((self_kpi_rating * 0.6 + competency_avg * 0.4), 2)

    # Update existing KPI score entries with self_score
    existing_kpi = appraisal.kpi_scores or []
    goal_map = {_str(g.id): g for g in goals}
    new_kpi: list[dict] = []
    for g in goals:
        gid = _str(g.id)
        new_kpi.append({
            "goal_id":    gid,
            "goal_title": g.title,
            "weight":     float(g.weight),
            "self_score": data.kpi_scores.get(gid),
            "mgr_score":  None,
        })

    appraisal.kpi_scores        = new_kpi
    appraisal.self_rating       = self_rating
    appraisal.self_achievements = data.self_achievements
    appraisal.self_improvements = data.self_improvements
    appraisal.self_strengths    = data.self_strengths
    # Store competency scores in ai_insights for reference
    appraisal.ai_insights       = {
        "self_competency_scores": data.competency_scores,
        "self_kpi_scores":        data.kpi_scores,
    }
    appraisal.status            = "self_review_submitted"
    appraisal.self_submitted_at = _now()

    await db.commit()
    await db.refresh(appraisal)
    return appraisal


async def submit_manager_review(
    tenant_id:    UUID,
    appraisal_id: UUID,
    data:         ManagerReviewSubmit,
    reviewer:     Employee,
    db:           AsyncSession,
) -> Appraisal:
    appraisal = (await db.execute(
        select(Appraisal).where(
            Appraisal.id        == appraisal_id,
            Appraisal.tenant_id == tenant_id,
        )
    )).scalar_one_or_none()
    if not appraisal:
        raise HTTPException(404, "Appraisal not found")

    # Reviewer must be the assigned reviewer or HR
    is_hr = getattr(reviewer, "is_hr", False)
    if not is_hr and str(appraisal.reviewer_id) != str(reviewer.id):
        raise HTTPException(403, "You are not the reviewer for this appraisal")

    # Must not be the employee themselves
    if str(appraisal.employee_id) == str(reviewer.id):
        raise HTTPException(403, "Manager cannot submit self review via this endpoint")

    if appraisal.status not in ("self_review_submitted", "manager_review_pending"):
        raise HTTPException(400, "Employee must submit self-review first")

    # Validate final_rating within scale
    cycle = (await db.execute(
        select(AppraisalCycle).where(AppraisalCycle.id == appraisal.cycle_id)
    )).scalar_one_or_none()
    scale_max = float(cycle.rating_scale_max) if cycle else 5.0
    if not (1 <= data.final_rating <= scale_max):
        raise HTTPException(400, f"final_rating must be 1–{scale_max}")

    # Update KPI entries with mgr_score
    existing_kpi = appraisal.kpi_scores or []
    updated_kpi = []
    for entry in existing_kpi:
        entry = dict(entry)
        entry["mgr_score"] = data.kpi_scores.get(entry["goal_id"])
        updated_kpi.append(entry)

    mgr_competency_avg = _calc_avg_competency(data.competency_scores)

    # Merge existing ai_insights
    ai_insights = appraisal.ai_insights or {}
    ai_insights["mgr_competency_scores"] = data.competency_scores
    ai_insights["mgr_kpi_scores"]        = data.kpi_scores

    appraisal.kpi_scores              = updated_kpi
    appraisal.manager_rating          = round(mgr_competency_avg, 2)
    appraisal.final_rating            = data.final_rating
    appraisal.manager_feedback        = data.manager_feedback
    appraisal.increment_recommended   = data.increment_recommended
    appraisal.increment_percentage    = data.increment_percentage
    appraisal.promotion_recommended   = data.promotion_recommended
    appraisal.promotion_to_designation= data.promotion_to_designation
    appraisal.ai_insights             = ai_insights
    appraisal.status                  = "manager_review_submitted"
    appraisal.manager_submitted_at    = _now()
    appraisal.finalized_at            = _now()

    await db.commit()

    # Create PIP if recommended
    if data.pip_recommended and data.pip_improvement_areas:
        from app.models.performance import PIP as PIPModel   # local import
        pip = PIPModel(
            tenant_id         = tenant_id,
            employee_id       = appraisal.employee_id,
            cycle_id          = appraisal.cycle_id,
            improvement_areas = data.pip_improvement_areas,
            action_items      = [ai.model_dump() for ai in data.pip_action_items],
            review_date       = data.pip_review_date,
            supervisor_id     = appraisal.reviewer_id,
            status            = "active",
        )
        db.add(pip)
        await db.commit()

    # Notify employee
    try:
        from app.tasks.performance_tasks import send_review_completed_notification
        send_review_completed_notification.delay(str(appraisal_id), str(tenant_id))
    except Exception:
        pass

    await db.refresh(appraisal)
    return appraisal


# ─── Bell Curve ───────────────────────────────────────────────────────────────

async def calculate_bell_curve(
    tenant_id: UUID,
    cycle_id:  UUID,
    db:        AsyncSession,
) -> BellCurveData:
    cycle = await get_appraisal_cycle(tenant_id, cycle_id, db)

    rows = (await db.execute(
        select(Appraisal)
        .options(
            selectinload(Appraisal.employee).selectinload(Employee.department),
        )
        .where(
            Appraisal.tenant_id  == tenant_id,
            Appraisal.cycle_id   == cycle_id,
            Appraisal.final_rating.isnot(None),
        )
    )).scalars().all()

    total = len(rows)
    if total == 0:
        return BellCurveData(cycle_id=str(cycle_id), total=0, buckets=[], is_skewed=False, skew_note=None)

    scale_min = int(cycle.rating_scale_min)
    scale_max = int(cycle.rating_scale_max)
    buckets_map: dict[int, list[Appraisal]] = {r: [] for r in range(scale_min, scale_max + 1)}

    for appraisal in rows:
        bucket = min(scale_max, max(scale_min, round(float(appraisal.final_rating))))
        buckets_map[bucket].append(appraisal)

    buckets = []
    for rating, bucket_appraisals in sorted(buckets_map.items()):
        count = len(bucket_appraisals)
        buckets.append(BellCurveBucket(
            rating     = rating,
            label      = RATING_LABELS.get(rating, str(rating)),
            count      = count,
            percentage = round(count / total * 100, 1) if total else 0,
            employees  = [_emp_minimal(a.employee) for a in bucket_appraisals if a.employee],
        ))

    # Skew check: top 20% should not have more than 60% of employees
    top_bucket_pct = sum(b.percentage for b in buckets if b.rating >= scale_max - 1)
    is_skewed = top_bucket_pct > 60 or top_bucket_pct < 5
    skew_note = None
    if top_bucket_pct > 60:
        skew_note = f"{top_bucket_pct:.0f}% of employees rated Outstanding/Exceeds — distribution may be too lenient."
    elif top_bucket_pct < 5:
        skew_note = "Very few top ratings — distribution may be too strict."

    return BellCurveData(
        cycle_id  = str(cycle_id),
        total     = total,
        buckets   = buckets,
        is_skewed = is_skewed,
        skew_note = skew_note,
    )


# ─── Team Summary ─────────────────────────────────────────────────────────────

async def get_team_performance_summary(
    tenant_id:  UUID,
    manager_id: UUID,
    cycle_id:   UUID,
    db:         AsyncSession,
) -> TeamPerformanceSummary:
    cycle = await get_appraisal_cycle(tenant_id, cycle_id, db)

    # Get direct reports
    employees = (await db.execute(
        select(Employee)
        .options(
            Employee.department if hasattr(Employee, 'department') else None,
        )
        .where(
            Employee.tenant_id  == tenant_id,
            Employee.manager_id == manager_id,
        )
    )).scalars().all()

    member_summaries = []
    ratings = []
    pip_count = 0

    for emp in employees:
        appraisal = (await db.execute(
            select(Appraisal).where(
                Appraisal.tenant_id   == tenant_id,
                Appraisal.cycle_id    == cycle_id,
                Appraisal.employee_id == emp.id,
            )
        )).scalar_one_or_none()

        summary = TeamMemberSummary(
            employee             = _emp_minimal(emp),
            appraisal_id         = _str(appraisal.id)               if appraisal else None,
            status               = appraisal.status                  if appraisal else None,
            self_rating          = float(appraisal.self_rating)      if appraisal and appraisal.self_rating else None,
            manager_rating       = float(appraisal.manager_rating)   if appraisal and appraisal.manager_rating else None,
            final_rating         = float(appraisal.final_rating)     if appraisal and appraisal.final_rating else None,
            self_submitted_at    = appraisal.self_submitted_at       if appraisal else None,
            manager_submitted_at = appraisal.manager_submitted_at    if appraisal else None,
        )
        member_summaries.append(summary)

        if appraisal and appraisal.final_rating:
            ratings.append(float(appraisal.final_rating))

    # Count PIPs for this team+cycle
    from app.models.performance import PIP as PIPModel
    emp_ids = [emp.id for emp in employees]
    if emp_ids:
        pip_count = (await db.execute(
            select(func.count(PIPModel.id)).where(
                PIPModel.tenant_id  == tenant_id,
                PIPModel.cycle_id   == cycle_id,
                PIPModel.employee_id.in_(emp_ids),
            )
        )).scalar_one()

    avg_rating  = round(sum(ratings) / len(ratings), 2) if ratings else None
    top_count   = sum(1 for r in ratings if r >= 4)

    # Sort by final_rating desc (nulls last)
    member_summaries.sort(key=lambda m: m.final_rating or 0, reverse=True)

    return TeamPerformanceSummary(
        cycle_id   = str(cycle_id),
        cycle_name = cycle.name,
        members    = member_summaries,
        avg_rating = avg_rating,
        top_count  = top_count,
        pip_count  = pip_count,
    )


# ─── PIP ─────────────────────────────────────────────────────────────────────

async def create_pip(
    tenant_id:     UUID,
    data:          PIPCreate,
    created_by_id: UUID,
    db:            AsyncSession,
):
    from app.models.performance import PIP as PIPModel
    pip = PIPModel(
        tenant_id         = tenant_id,
        employee_id       = data.employee_id,
        cycle_id          = data.cycle_id,
        improvement_areas = data.improvement_areas,
        action_items      = [ai.model_dump() for ai in data.action_items],
        review_date       = data.review_date,
        supervisor_id     = data.supervisor_id or created_by_id,
        status            = "active",
        notes             = data.notes,
    )
    db.add(pip)
    await db.commit()
    await db.refresh(pip)
    return pip


async def get_employee_pips(tenant_id: UUID, employee_id: UUID, db: AsyncSession):
    from app.models.performance import PIP as PIPModel
    rows = (await db.execute(
        select(PIPModel)
        .options(selectinload(PIPModel.employee), selectinload(PIPModel.supervisor))
        .where(
            PIPModel.tenant_id   == tenant_id,
            PIPModel.employee_id == employee_id,
        )
        .order_by(PIPModel.created_at.desc())
    )).scalars().all()
    return list(rows)


async def update_pip(tenant_id: UUID, pip_id: UUID, data: PIPUpdate, db: AsyncSession):
    from app.models.performance import PIP as PIPModel
    pip = (await db.execute(
        select(PIPModel).where(PIPModel.id == pip_id, PIPModel.tenant_id == tenant_id)
    )).scalar_one_or_none()
    if not pip:
        raise HTTPException(404, "PIP not found")
    for field, value in data.model_dump(exclude_none=True).items():
        if field == "action_items" and value:
            value = [ai.model_dump() if hasattr(ai, 'model_dump') else ai for ai in value]
        setattr(pip, field, value)
    await db.commit()
    await db.refresh(pip)
    return pip


# ─── Report PDF ───────────────────────────────────────────────────────────────

async def generate_appraisal_report(
    tenant_id: UUID,
    cycle_id:  UUID,
    db:        AsyncSession,
) -> bytes:
    cycle     = await get_appraisal_cycle(tenant_id, cycle_id, db)
    bell_data = await calculate_bell_curve(tenant_id, cycle_id, db)

    try:
        from reportlab.lib.pagesizes   import A4
        from reportlab.lib.styles      import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units       import cm
        from reportlab.lib             import colors
        from reportlab.platypus        import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=2*cm, bottomMargin=2*cm)
        styles = getSampleStyleSheet()
        story  = []

        story.append(Paragraph(f"Appraisal Report: {cycle.name}", styles["Title"]))
        story.append(Paragraph(f"Period: {cycle.start_date} to {cycle.end_date}", styles["Normal"]))
        story.append(Spacer(1, 0.5*cm))

        # Bell curve table
        story.append(Paragraph("Rating Distribution", styles["Heading2"]))
        data = [["Rating", "Label", "Count", "Percentage"]]
        for b in bell_data.buckets:
            data.append([str(b.rating), b.label, str(b.count), f"{b.percentage:.1f}%"])
        t = Table(data, colWidths=[3*cm, 6*cm, 3*cm, 3*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
            ("ALIGN",      (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("GRID",       (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        if bell_data.is_skewed and bell_data.skew_note:
            story.append(Paragraph(f"⚠ {bell_data.skew_note}", styles["Normal"]))

        story.append(Paragraph(f"Total Completed Appraisals: {bell_data.total}", styles["Normal"]))

        doc.build(story)
        return buf.getvalue()

    except ImportError:
        # Fallback plain text
        lines = [
            f"APPRAISAL REPORT: {cycle.name}",
            f"Period: {cycle.start_date} — {cycle.end_date}",
            "",
            "RATING DISTRIBUTION",
            "-" * 40,
        ]
        for b in bell_data.buckets:
            lines.append(f"  {b.label}: {b.count} ({b.percentage:.1f}%)")
        lines.append(f"\nTotal: {bell_data.total}")
        return "\n".join(lines).encode()

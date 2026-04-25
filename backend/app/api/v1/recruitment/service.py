"""
AI-HRMS — Recruitment service layer.
All DB operations are tenant-scoped; every function receives tenant_id explicitly.
"""

from __future__ import annotations

import io
import logging
import os
import uuid as _uuid
from datetime  import date, datetime
from typing    import Optional

from fastapi             import HTTPException, UploadFile, status
from sqlalchemy          import select, func, and_, update as sql_update
from sqlalchemy.orm      import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Department, Designation, Employee, User
from app.models.recruitment import JobApplication, JobPosting, Interview

from app.api.v1.recruitment.schemas import (
    ApplicationFilterParams,
    ApplicationListResponse,
    ApplicationSource,
    ApplicationStageUpdate,
    ApplicationStatus,
    CVUploadResponse,
    EmploymentType,
    InterviewFeedbackRequest,
    InterviewScheduleRequest,
    JobApplicationCreate,
    JobApplicationListItem,
    JobApplicationResponse,
    JobPostingCreate,
    JobPostingListItem,
    JobPostingListResponse,
    JobPostingResponse,
    JobPostingUpdate,
    OfferLetterRequest,
    PipelineColumnData,
    PipelineStats,
    StageCounts,
    StageHistoryItem,
)

logger = logging.getLogger(__name__)

CV_UPLOAD_DIR = os.environ.get("CV_UPLOAD_DIR", "/tmp/cvs")
OFFER_DIR     = os.environ.get("OFFER_LETTER_DIR", "/tmp/offers")

ALLOWED_CV_EXTENSIONS  = {".pdf", ".doc", ".docx"}
MAX_CV_SIZE_BYTES      = 5 * 1024 * 1024  # 5 MB

PIPELINE_STAGES = [
    "applied", "screening", "shortlisted", "interview", "offered", "hired", "rejected", "withdrawn"
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _str(v) -> Optional[str]:
    return str(v) if v is not None else None


async def _get_job(tenant_id: str, job_id: str, db: AsyncSession) -> JobPosting:
    row = await db.execute(
        select(JobPosting)
        .options(
            selectinload(JobPosting.department),
            selectinload(JobPosting.designation),
        )
        .where(JobPosting.id == job_id, JobPosting.tenant_id == tenant_id)
    )
    job = row.scalar_one_or_none()
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job posting not found.")
    return job


def _job_list_item(job: JobPosting, app_count: int = 0) -> JobPostingListItem:
    return JobPostingListItem(
        id               = _str(job.id),
        title            = job.title,
        location         = job.location,
        employment_type  = job.employment_type,
        vacancies        = job.vacancies,
        status           = job.status,
        closing_date     = job.closing_date,
        department_name  = job.department.name if job.department else None,
        application_count= app_count,
        created_at       = job.created_at,
    )


async def _app_count(job_id, db: AsyncSession) -> int:
    row = await db.execute(
        select(func.count(JobApplication.id)).where(JobApplication.job_posting_id == job_id)
    )
    return row.scalar_one() or 0


# ─── Job Postings ─────────────────────────────────────────────────────────────

async def create_job_posting(
    tenant_id: str, data: JobPostingCreate, created_by: str, db: AsyncSession
) -> JobPosting:
    job = JobPosting(
        tenant_id              = tenant_id,
        title                  = data.title,
        department_id          = data.department_id,
        designation_id         = data.designation_id,
        location               = data.location,
        description            = data.description,
        requirements           = "\n".join(data.requirements) if data.requirements else None,
        responsibilities       = "\n".join(data.responsibilities) if data.responsibilities else None,
        benefits               = data.benefits,
        vacancies              = data.vacancies,
        employment_type        = data.employment_type.value,
        experience_years_min   = data.experience_years_min,
        experience_years_max   = data.experience_years_max,
        salary_min             = data.salary_range_min,
        salary_max             = data.salary_range_max,
        is_salary_visible      = data.salary_visible,
        required_skills        = data.skills_required or [],
        closing_date           = data.closing_date,
        posted_by              = created_by,
        status                 = "draft",
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    await db.commit()
    logger.info("Job posting created: %s by %s", job.id, created_by)
    return job


async def publish_job_posting(tenant_id: str, job_id: str, db: AsyncSession) -> JobPosting:
    job = await _get_job(tenant_id, job_id, db)
    if job.status == "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "Job posting is already published.")
    if job.status == "filled":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Cannot reopen a filled position.")
    job.status    = "open"
    job.posted_at = datetime.utcnow()
    await db.commit()
    await db.refresh(job)
    return job


async def close_job_posting(tenant_id: str, job_id: str, db: AsyncSession) -> JobPosting:
    job = await _get_job(tenant_id, job_id, db)
    job.status = "closed"
    await db.commit()
    await db.refresh(job)
    return job


async def update_job_posting(
    tenant_id: str, job_id: str, data: JobPostingUpdate, db: AsyncSession
) -> JobPosting:
    job = await _get_job(tenant_id, job_id, db)
    update_data = data.model_dump(exclude_none=True)
    for field_name, value in update_data.items():
        if field_name == "requirements":
            setattr(job, field_name, "\n".join(value) if value else None)
        elif field_name == "responsibilities":
            setattr(job, field_name, "\n".join(value) if value else None)
        elif field_name == "skills_required":
            setattr(job, "required_skills", value)
        elif field_name == "salary_range_min":
            setattr(job, "salary_min", value)
        elif field_name == "salary_range_max":
            setattr(job, "salary_max", value)
        elif field_name == "salary_visible":
            setattr(job, "is_salary_visible", value)
        elif field_name == "employment_type":
            setattr(job, field_name, value.value if hasattr(value, "value") else value)
        else:
            setattr(job, field_name, value)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job_postings(
    tenant_id: str, db: AsyncSession,
    status_f: Optional[str] = None,
    department_id: Optional[str] = None,
    employment_type: Optional[str] = None,
    search: Optional[str] = None,
    page: int = 1,
    page_size: int = 25,
) -> JobPostingListResponse:
    q = (
        select(JobPosting)
        .options(selectinload(JobPosting.department), selectinload(JobPosting.designation))
        .where(JobPosting.tenant_id == tenant_id)
    )
    if status_f:
        q = q.where(JobPosting.status == status_f)
    if department_id:
        q = q.where(JobPosting.department_id == department_id)
    if employment_type:
        q = q.where(JobPosting.employment_type == employment_type)
    if search:
        q = q.where(JobPosting.title.ilike(f"%{search}%"))

    count_q = select(func.count()).select_from(q.subquery())
    total   = (await db.execute(count_q)).scalar_one()

    q       = q.order_by(JobPosting.created_at.desc())
    q       = q.offset((page - 1) * page_size).limit(page_size)
    rows    = await db.execute(q)
    jobs    = rows.scalars().all()

    results = []
    for job in jobs:
        cnt = await _app_count(job.id, db)
        results.append(_job_list_item(job, cnt))

    return JobPostingListResponse(count=total, results=results)


async def get_job_posting(
    tenant_id: str, job_id: str, db: AsyncSession
) -> JobPostingResponse:
    job = await _get_job(tenant_id, job_id, db)
    cnt = await _app_count(job.id, db)

    # Stage counts
    stage_rows = await db.execute(
        select(JobApplication.status, func.count(JobApplication.id))
        .where(JobApplication.job_posting_id == job.id)
        .group_by(JobApplication.status)
    )
    stage_dict = {r[0]: r[1] for r in stage_rows}
    stage_counts = StageCounts(**{s: stage_dict.get(s, 0) for s in StageCounts.model_fields})

    return JobPostingResponse(
        id                   = _str(job.id),
        title                = job.title,
        location             = job.location,
        description          = job.description,
        requirements         = job.requirements.split("\n") if job.requirements else [],
        responsibilities     = job.responsibilities.split("\n") if job.responsibilities else [],
        benefits             = job.benefits,
        vacancies            = job.vacancies,
        employment_type      = job.employment_type,
        experience_years_min = job.experience_years_min,
        experience_years_max = job.experience_years_max,
        salary_min           = job.salary_min,
        salary_max           = job.salary_max,
        is_salary_visible    = job.is_salary_visible,
        required_skills      = job.required_skills or [],
        status               = job.status,
        is_internal          = False,
        posted_at            = job.posted_at,
        closing_date         = job.closing_date,
        department           = None if not job.department else
                               type("D", (), {"id": _str(job.department.id), "name": job.department.name})(),
        designation          = None if not job.designation else
                               type("Des", (), {"id": _str(job.designation.id), "title": job.designation.title})(),
        application_count    = cnt,
        stage_counts         = stage_counts,
        created_at           = job.created_at,
        updated_at           = job.updated_at,
    )


async def get_pipeline_stats(
    tenant_id: str, job_id: str, db: AsyncSession
) -> PipelineStats:
    job = await _get_job(tenant_id, job_id, db)

    apps_rows = await db.execute(
        select(JobApplication)
        .where(
            JobApplication.job_posting_id == job_id,
            JobApplication.is_archived == False,
        )
        .order_by(JobApplication.ai_score.desc().nulls_last(), JobApplication.applied_at.desc())
    )
    apps = apps_rows.scalars().all()

    stage_map: dict[str, list[JobApplication]] = {s: [] for s in PIPELINE_STAGES}
    for app in apps:
        stage_map.setdefault(app.status, []).append(app)

    columns = []
    for stage in PIPELINE_STAGES:
        col_apps = stage_map.get(stage, [])
        columns.append(PipelineColumnData(
            status       = stage,
            count        = len(col_apps),
            applications = [
                JobApplicationListItem(
                    id             = _str(a.id),
                    job_posting_id = _str(a.job_posting_id),
                    job_title      = job.title,
                    candidate_name = a.candidate_name,
                    candidate_email= a.candidate_email,
                    source         = a.source,
                    status         = a.status,
                    ai_score       = float(a.ai_score) if a.ai_score else None,
                    applied_at     = a.applied_at,
                    created_at     = a.created_at,
                )
                for a in col_apps
            ],
        ))

    return PipelineStats(
        job_posting_id = _str(job.id),
        job_title      = job.title,
        total          = len(apps),
        columns        = columns,
    )


# ─── CV Upload ────────────────────────────────────────────────────────────────

async def upload_cv(file: UploadFile, tenant_id: str) -> CVUploadResponse:
    import os as _os
    ext = _os.path.splitext(file.filename or "file.pdf")[1].lower()
    if ext not in ALLOWED_CV_EXTENSIONS:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"File type not allowed. Accepted: {', '.join(ALLOWED_CV_EXTENSIONS)}",
        )

    contents = await file.read()
    if len(contents) > MAX_CV_SIZE_BYTES:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "CV file exceeds 5 MB.")

    _os.makedirs(CV_UPLOAD_DIR, exist_ok=True)
    unique_name = f"{_uuid.uuid4()}{ext}"
    file_path   = _os.path.join(CV_UPLOAD_DIR, unique_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    cv_url = f"/cvs/{unique_name}"
    return CVUploadResponse(cv_url=cv_url, filename=file.filename or unique_name, file_size=len(contents))


# ─── Applications ─────────────────────────────────────────────────────────────

async def submit_application(
    tenant_id: str, data: JobApplicationCreate, db: AsyncSession
) -> JobApplication:
    # Check job is open
    job_row = await db.execute(
        select(JobPosting).where(
            JobPosting.id == data.job_posting_id,
            JobPosting.tenant_id == tenant_id,
        )
    )
    job = job_row.scalar_one_or_none()
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job posting not found.")
    if job.status != "open":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"This position is not accepting applications (status: {job.status}).",
        )
    if job.closing_date and job.closing_date < date.today():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "The application deadline has passed.",
        )

    # Duplicate check
    dup = await db.execute(
        select(JobApplication).where(
            JobApplication.job_posting_id == data.job_posting_id,
            JobApplication.candidate_email == data.candidate_email.lower(),
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "You have already applied for this position.",
        )

    app = JobApplication(
        job_posting_id    = data.job_posting_id,
        candidate_name    = data.candidate_name,
        candidate_email   = data.candidate_email.lower(),
        candidate_phone   = data.candidate_phone,
        candidate_location= data.candidate_location,
        cv_url            = data.cv_url,
        cover_letter      = data.cover_letter,
        portfolio_url     = data.portfolio_url,
        linkedin_url      = data.linkedin_url,
        source            = data.source.value,
        referred_by       = data.referred_by_employee_id,
        status            = "applied",
        applied_at        = datetime.utcnow(),
    )
    db.add(app)
    await db.flush()
    await db.refresh(app)
    await db.commit()

    # Trigger async AI scoring
    if data.cv_url:
        try:
            from app.tasks.recruitment_tasks import ai_score_cv
            ai_score_cv.delay(str(app.id))
        except Exception as exc:
            logger.warning("Could not queue AI scoring task: %s", exc)

    # Confirmation email
    try:
        from app.tasks.recruitment_tasks import send_application_confirmation
        send_application_confirmation.delay(str(app.id))
    except Exception as exc:
        logger.warning("Could not queue confirmation email: %s", exc)

    return app


async def get_applications(
    tenant_id: str, filters: ApplicationFilterParams, db: AsyncSession
) -> ApplicationListResponse:
    q = (
        select(JobApplication)
        .join(JobPosting, JobPosting.id == JobApplication.job_posting_id)
        .where(JobPosting.tenant_id == tenant_id)
    )

    if filters.job_posting_id:
        q = q.where(JobApplication.job_posting_id == filters.job_posting_id)
    if filters.status:
        q = q.where(JobApplication.status == filters.status)
    if filters.source:
        q = q.where(JobApplication.source == filters.source)
    if filters.date_from:
        q = q.where(JobApplication.applied_at >= datetime.combine(filters.date_from, datetime.min.time()))
    if filters.date_to:
        q = q.where(JobApplication.applied_at <= datetime.combine(filters.date_to, datetime.max.time()))
    if filters.min_ai_score is not None:
        q = q.where(JobApplication.ai_score >= filters.min_ai_score)
    if filters.search:
        term = f"%{filters.search}%"
        q = q.where(
            JobApplication.candidate_name.ilike(term) |
            JobApplication.candidate_email.ilike(term)
        )

    count_q = select(func.count()).select_from(q.subquery())
    total   = (await db.execute(count_q)).scalar_one()

    q = q.order_by(JobApplication.ai_score.desc().nulls_last(), JobApplication.applied_at.desc())
    q = q.offset((filters.page - 1) * filters.page_size).limit(filters.page_size)
    rows  = await db.execute(q)
    apps  = rows.scalars().all()

    # Fetch job titles in one shot
    job_ids   = list({str(a.job_posting_id) for a in apps})
    job_titles: dict[str, str] = {}
    if job_ids:
        jt_rows = await db.execute(
            select(JobPosting.id, JobPosting.title).where(JobPosting.id.in_(job_ids))
        )
        job_titles = {str(r[0]): r[1] for r in jt_rows}

    results = [
        JobApplicationListItem(
            id             = _str(a.id),
            job_posting_id = _str(a.job_posting_id),
            job_title      = job_titles.get(str(a.job_posting_id)),
            candidate_name = a.candidate_name,
            candidate_email= a.candidate_email,
            source         = a.source,
            status         = a.status,
            ai_score       = float(a.ai_score) if a.ai_score else None,
            applied_at     = a.applied_at,
            created_at     = a.created_at,
        )
        for a in apps
    ]
    return ApplicationListResponse(count=total, results=results)


async def get_application(
    tenant_id: str, app_id: str, db: AsyncSession
) -> JobApplicationResponse:
    row = await db.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job_posting).options(
                selectinload(JobPosting.department),
                selectinload(JobPosting.designation),
            ),
            selectinload(JobApplication.interviews).selectinload(Interview.interviewer),
        )
        .join(JobPosting, JobPosting.id == JobApplication.job_posting_id)
        .where(JobApplication.id == app_id, JobPosting.tenant_id == tenant_id)
    )
    app = row.scalar_one_or_none()
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found.")

    job = app.job_posting
    job_item = None
    if job:
        cnt = await _app_count(job.id, db)
        job_item = _job_list_item(job, cnt)

    # Stage history from JSONB or empty
    history = []
    if app.ai_explanation and "stage_history" in app.ai_explanation:
        for h in app.ai_explanation["stage_history"]:
            history.append(StageHistoryItem(**h))

    from app.api.v1.recruitment.schemas import InterviewResponse
    interviews_resp = []
    for iv in (app.interviews or []):
        interviews_resp.append(InterviewResponse(
            id               = _str(iv.id),
            application_id   = _str(iv.application_id),
            round_number     = iv.round_number,
            title            = iv.title,
            interviewer_id   = _str(iv.interviewer_id),
            interviewer      = None,
            scheduled_at     = iv.scheduled_at,
            duration_minutes = iv.duration_minutes,
            mode             = iv.mode,
            meeting_link     = iv.meeting_link,
            location         = iv.location,
            status           = iv.status,
            feedback         = iv.feedback,
            rating           = float(iv.rating) if iv.rating else None,
            recommendation   = iv.recommendation,
            completed_at     = iv.completed_at,
            created_at       = iv.created_at,
        ))

    return JobApplicationResponse(
        id                = _str(app.id),
        job_posting_id    = _str(app.job_posting_id),
        job_posting       = job_item,
        candidate_name    = app.candidate_name,
        candidate_email   = app.candidate_email,
        candidate_phone   = app.candidate_phone,
        candidate_location= app.candidate_location,
        cv_url            = app.cv_url,
        cover_letter      = app.cover_letter,
        portfolio_url     = app.portfolio_url,
        linkedin_url      = app.linkedin_url,
        source            = app.source,
        referred_by       = _str(app.referred_by),
        applied_at        = app.applied_at,
        status            = app.status,
        rejection_reason  = app.rejection_reason,
        is_archived       = app.is_archived,
        ai_score          = float(app.ai_score) if app.ai_score else None,
        ai_explanation    = app.ai_explanation,
        ai_scored_at      = app.ai_scored_at,
        hr_notes          = app.hr_notes,
        offer_letter_url  = app.offer_letter_url,
        offer_sent_at     = app.offer_sent_at,
        offer_deadline    = app.offer_deadline,
        hired_employee_id = _str(app.hired_employee_id),
        stage_history     = history,
        interviews        = interviews_resp,
        created_at        = app.created_at,
        updated_at        = app.updated_at,
    )


async def update_application_stage(
    tenant_id: str, app_id: str, data: ApplicationStageUpdate, updated_by: str, db: AsyncSession
) -> JobApplication:
    row = await db.execute(
        select(JobApplication)
        .join(JobPosting, JobPosting.id == JobApplication.job_posting_id)
        .where(JobApplication.id == app_id, JobPosting.tenant_id == tenant_id)
    )
    app = row.scalar_one_or_none()
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found.")

    old_status = app.status

    # Record stage change in ai_explanation JSONB
    history_entry = {
        "from_status": old_status,
        "to_status":   data.new_status.value,
        "changed_by":  updated_by,
        "notes":       data.notes,
        "changed_at":  datetime.utcnow().isoformat(),
    }
    existing_expl = app.ai_explanation or {}
    existing_hist = existing_expl.get("stage_history", [])
    existing_hist.append(history_entry)
    existing_expl["stage_history"] = existing_hist

    app.status          = data.new_status.value
    app.ai_explanation  = existing_expl
    if data.rejection_reason:
        app.rejection_reason = data.rejection_reason

    await db.commit()
    await db.refresh(app)

    # If hired, trigger employee creation
    if data.new_status.value == "hired":
        try:
            from app.tasks.recruitment_tasks import convert_to_employee
            convert_to_employee.delay(str(app.id))
        except Exception as exc:
            logger.warning("Could not queue convert_to_employee task: %s", exc)

    return app


# ─── Interviews ───────────────────────────────────────────────────────────────

async def schedule_interview(
    tenant_id: str, data: InterviewScheduleRequest, scheduled_by: str, db: AsyncSession
) -> list[Interview]:
    # Verify application belongs to this tenant
    row = await db.execute(
        select(JobApplication)
        .join(JobPosting, JobPosting.id == JobApplication.job_posting_id)
        .where(JobApplication.id == data.application_id, JobPosting.tenant_id == tenant_id)
    )
    app = row.scalar_one_or_none()
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found.")

    # Determine next round number
    round_row = await db.execute(
        select(func.max(Interview.round_number)).where(
            Interview.application_id == data.application_id
        )
    )
    last_round = round_row.scalar_one() or 0

    created = []
    for idx, interviewer_id in enumerate(data.interviewer_ids):
        iv = Interview(
            application_id   = data.application_id,
            round_number     = last_round + 1,
            title            = data.title or f"Interview Round {last_round + 1}",
            interviewer_id   = interviewer_id,
            scheduled_by     = scheduled_by,
            scheduled_at     = data.scheduled_at,
            duration_minutes = data.duration_minutes,
            mode             = data.mode.value,
            meeting_link     = data.location_or_link if data.mode.value == "online" else None,
            location         = data.location_or_link if data.mode.value != "online" else None,
            status           = "scheduled",
        )
        db.add(iv)
        created.append(iv)

    await db.flush()
    await db.commit()

    # Move application to interview stage if not already
    if app.status in ("applied", "screening", "shortlisted"):
        app.status = "interview"
        await db.commit()

    # Send invites
    for iv in created:
        await db.refresh(iv)
        try:
            from app.tasks.recruitment_tasks import send_interview_invitation
            send_interview_invitation.delay(str(iv.id))
        except Exception as exc:
            logger.warning("Could not queue interview invite: %s", exc)

    return created


async def submit_interview_feedback(
    tenant_id: str, interview_id: str, data: InterviewFeedbackRequest,
    submitted_by: str, db: AsyncSession
) -> Interview:
    row = await db.execute(
        select(Interview)
        .join(JobApplication, JobApplication.id == Interview.application_id)
        .join(JobPosting, JobPosting.id == JobApplication.job_posting_id)
        .where(Interview.id == interview_id, JobPosting.tenant_id == tenant_id)
    )
    iv = row.scalar_one_or_none()
    if not iv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found.")

    iv.feedback       = data.feedback
    iv.rating         = data.rating
    iv.recommendation = data.recommendation.value
    iv.status         = "completed"
    iv.completed_at   = datetime.utcnow()
    await db.commit()
    await db.refresh(iv)
    return iv


async def get_interviews_for_application(
    tenant_id: str, app_id: str, db: AsyncSession
) -> list[Interview]:
    # Verify ownership
    row = await db.execute(
        select(JobApplication)
        .join(JobPosting, JobPosting.id == JobApplication.job_posting_id)
        .where(JobApplication.id == app_id, JobPosting.tenant_id == tenant_id)
    )
    if not row.scalar_one_or_none():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found.")

    iv_rows = await db.execute(
        select(Interview)
        .options(selectinload(Interview.interviewer))
        .where(Interview.application_id == app_id)
        .order_by(Interview.round_number)
    )
    return iv_rows.scalars().all()


# ─── Offer Letter ─────────────────────────────────────────────────────────────

async def generate_offer_letter(
    tenant_id: str, data: OfferLetterRequest, generated_by: str, db: AsyncSession
) -> str:
    """Generate PDF offer letter. Returns file URL."""
    row = await db.execute(
        select(JobApplication)
        .options(
            selectinload(JobApplication.job_posting).options(
                selectinload(JobPosting.department),
                selectinload(JobPosting.designation),
            )
        )
        .join(JobPosting, JobPosting.id == JobApplication.job_posting_id)
        .where(JobApplication.id == data.application_id, JobPosting.tenant_id == tenant_id)
    )
    app = row.scalar_one_or_none()
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found.")

    os.makedirs(OFFER_DIR, exist_ok=True)
    filename  = f"offer_{app.candidate_email.split('@')[0]}_{data.joining_date}.pdf"
    file_path = os.path.join(OFFER_DIR, filename)

    _generate_offer_pdf(app, data, file_path)

    offer_url = f"/offers/{filename}"
    app.offer_letter_url = offer_url
    app.offer_sent_at    = datetime.utcnow()
    app.offer_deadline   = data.offer_expiry_date
    app.status           = "offered"
    await db.commit()

    # Email
    try:
        from app.tasks.recruitment_tasks import send_offer_letter_email
        send_offer_letter_email.delay(str(app.id), offer_url)
    except Exception as exc:
        logger.warning("Could not queue offer email: %s", exc)

    return offer_url


def _generate_offer_pdf(
    app: JobApplication, data: OfferLetterRequest, file_path: str
) -> None:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units     import cm
        from reportlab.lib           import colors
        from reportlab.lib.styles    import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus      import (
            SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle,
        )
        from reportlab.lib.enums     import TA_CENTER, TA_LEFT, TA_JUSTIFY

        doc    = SimpleDocTemplate(file_path, pagesize=A4,
                                   topMargin=2*cm, bottomMargin=2*cm,
                                   leftMargin=2.5*cm, rightMargin=2.5*cm)
        styles = getSampleStyleSheet()
        story  = []

        H1 = ParagraphStyle("H1", fontSize=18, fontName="Helvetica-Bold",
                             alignment=TA_CENTER, textColor=colors.HexColor("#1e293b"))
        H2 = ParagraphStyle("H2", fontSize=13, fontName="Helvetica-Bold",
                             textColor=colors.HexColor("#1e293b"), spaceAfter=6)
        NM = ParagraphStyle("NM", fontSize=10, fontName="Helvetica",
                             textColor=colors.HexColor("#334155"), leading=16)
        SM = ParagraphStyle("SM", fontSize=9,  fontName="Helvetica",
                             textColor=colors.HexColor("#64748b"))
        BIG = ParagraphStyle("BIG", fontSize=13, fontName="Helvetica-Bold",
                              textColor=colors.HexColor("#16a34a"))

        job       = app.job_posting
        job_title = job.title if job else "Position"
        dept_name = job.department.name if (job and job.department) else ""

        story.append(Paragraph("OFFER OF EMPLOYMENT", H1))
        story.append(Spacer(1, 0.4*cm))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0")))
        story.append(Spacer(1, 0.6*cm))

        today = date.today().strftime("%d %B %Y")
        story.append(Paragraph(f"Date: {today}", SM))
        story.append(Spacer(1, 0.4*cm))

        story.append(Paragraph(f"Dear <b>{app.candidate_name}</b>,", NM))
        story.append(Spacer(1, 0.3*cm))
        story.append(Paragraph(
            f"We are pleased to extend this offer of employment for the position of "
            f"<b>{job_title}</b>" +
            (f" in the <b>{dept_name}</b> department" if dept_name else "") +
            ". Please review the details below:",
            NM,
        ))
        story.append(Spacer(1, 0.5*cm))

        fmt_salary = f"PKR {data.offered_salary:,}"
        offer_rows = [
            ["Position",       job_title],
            ["Department",     dept_name or "—"],
            ["Joining Date",   data.joining_date.strftime("%d %B %Y")],
            ["Monthly Salary", fmt_salary],
            ["Offer Valid Until", data.offer_expiry_date.strftime("%d %B %Y")],
        ]
        t = Table(offer_rows, colWidths=[5*cm, 11*cm])
        t.setStyle(TableStyle([
            ("FONTNAME",   (0, 0), (0, -1), "Helvetica-Bold"),
            ("FONTSIZE",   (0, 0), (-1, -1), 10),
            ("TEXTCOLOR",  (0, 0), (0, -1), colors.HexColor("#475569")),
            ("GRID",       (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
            ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("PADDING",    (0, 0), (-1, -1), 6),
        ]))
        story.append(t)
        story.append(Spacer(1, 0.5*cm))

        # Net salary highlight
        story.append(Paragraph(f"Monthly Net Salary: {fmt_salary}", BIG))
        story.append(Spacer(1, 0.4*cm))

        if data.additional_terms:
            story.append(Paragraph("Additional Terms &amp; Conditions", H2))
            story.append(Paragraph(data.additional_terms, NM))
            story.append(Spacer(1, 0.4*cm))

        story.append(Paragraph(
            "Please sign and return a copy of this letter by the offer expiry date to accept. "
            "We look forward to welcoming you to our team.",
            NM,
        ))
        story.append(Spacer(1, 1.5*cm))

        # Signature block
        sig_data = [
            ["", ""],
            ["________________________", "________________________"],
            ["HR Department",           "Candidate Signature"],
            ["AI-HRMS",                 app.candidate_name],
        ]
        sig_t = Table(sig_data, colWidths=[8*cm, 8*cm])
        sig_t.setStyle(TableStyle([
            ("FONTSIZE",  (0, 0), (-1, -1), 9),
            ("TEXTCOLOR", (0, 2), (-1, -1), colors.HexColor("#64748b")),
            ("ALIGN",     (0, 0), (-1, -1), "LEFT"),
            ("TOPPADDING",(0, 0), (-1, -1), 3),
        ]))
        story.append(sig_t)

        doc.build(story)
        logger.info("Offer letter generated: %s", file_path)

    except ImportError:
        logger.warning("reportlab not installed — writing plain text offer letter.")
        with open(file_path.replace(".pdf", ".txt"), "w") as f:
            f.write(f"OFFER OF EMPLOYMENT\n\nDear {app.candidate_name},\n"
                    f"Salary: PKR {data.offered_salary:,}/month\n"
                    f"Joining: {data.joining_date}\n")

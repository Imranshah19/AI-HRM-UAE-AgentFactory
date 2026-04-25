"""
AI-HRMS — Recruitment / ATS router.
"""

from __future__ import annotations

import os
from typing import Annotated, Optional

from fastapi import (
    APIRouter, Depends, File, HTTPException, Query,
    UploadFile, status,
)
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.deps import get_current_user, get_db
from app.models   import User, Employee
from app.models.recruitment import JobPosting, JobApplication, Interview

from app.api.v1.recruitment import service
from app.api.v1.recruitment.schemas import (
    ApplicationFilterParams,
    ApplicationListResponse,
    ApplicationStageUpdate,
    CVUploadResponse,
    InterviewFeedbackRequest,
    InterviewResponse,
    InterviewScheduleRequest,
    JobApplicationCreate,
    JobApplicationResponse,
    JobPostingCreate,
    JobPostingListResponse,
    JobPostingResponse,
    JobPostingUpdate,
    OfferLetterRequest,
    PipelineStats,
    PublicJobPostingResponse,
)

router        = APIRouter(prefix="/recruitment", tags=["Recruitment"])
public_router = APIRouter(prefix="/public",      tags=["Public Recruitment"])


# ─── Permission helper ────────────────────────────────────────────────────────

def _is_recruiter(user: User) -> bool:
    if user.is_superadmin:
        return True
    perms = getattr(user, "permissions", [])
    return any(p.module_name in ("recruitment", "hr") for p in perms)


async def _get_employee_for_user(user: User, db: AsyncSession) -> Optional[Employee]:
    row = await db.execute(
        select(Employee).where(
            Employee.user_id   == user.id,
            Employee.tenant_id == user.tenant_id,
        )
    )
    return row.scalar_one_or_none()


# ─── Job Postings ─────────────────────────────────────────────────────────────

@router.get(
    "/jobs",
    response_model=JobPostingListResponse,
    summary="List job postings",
)
async def list_jobs(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    status_f:        Optional[str] = Query(None, alias="status"),
    department_id:   Optional[str] = Query(None),
    employment_type: Optional[str] = Query(None),
    search:          Optional[str] = Query(None),
    page:            int           = Query(1, ge=1),
    page_size:       int           = Query(25, ge=1, le=100),
):
    return await service.get_job_postings(
        str(current_user.tenant_id), db,
        status_f=status_f,
        department_id=department_id,
        employment_type=employment_type,
        search=search,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/jobs",
    response_model=JobPostingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job posting",
)
async def create_job(
    data: JobPostingCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_recruiter(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    job = await service.create_job_posting(
        str(current_user.tenant_id), data, str(current_user.id), db
    )
    return await service.get_job_posting(str(current_user.tenant_id), str(job.id), db)


@router.get(
    "/jobs/{job_id}",
    response_model=JobPostingResponse,
    summary="Get job posting detail",
)
async def get_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.get_job_posting(str(current_user.tenant_id), job_id, db)


@router.patch(
    "/jobs/{job_id}",
    response_model=JobPostingResponse,
    summary="Update a job posting",
)
async def update_job(
    job_id: str,
    data: JobPostingUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_recruiter(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    await service.update_job_posting(str(current_user.tenant_id), job_id, data, db)
    return await service.get_job_posting(str(current_user.tenant_id), job_id, db)


@router.post(
    "/jobs/{job_id}/publish",
    response_model=JobPostingResponse,
    summary="Publish job posting (draft → open)",
)
async def publish_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_recruiter(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    await service.publish_job_posting(str(current_user.tenant_id), job_id, db)
    return await service.get_job_posting(str(current_user.tenant_id), job_id, db)


@router.post(
    "/jobs/{job_id}/close",
    response_model=JobPostingResponse,
    summary="Close a job posting",
)
async def close_job(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_recruiter(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    await service.close_job_posting(str(current_user.tenant_id), job_id, db)
    return await service.get_job_posting(str(current_user.tenant_id), job_id, db)


@router.get(
    "/jobs/{job_id}/pipeline",
    response_model=PipelineStats,
    summary="Get kanban pipeline data for a job",
)
async def get_pipeline(
    job_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.get_pipeline_stats(str(current_user.tenant_id), job_id, db)


# ─── Applications ─────────────────────────────────────────────────────────────

@router.get(
    "/applications",
    response_model=ApplicationListResponse,
    summary="List applications across all jobs",
)
async def list_applications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
    job_posting_id: Optional[str]  = Query(None),
    status_f:       Optional[str]  = Query(None, alias="status"),
    source:         Optional[str]  = Query(None),
    date_from:      Optional[str]  = Query(None),
    date_to:        Optional[str]  = Query(None),
    min_ai_score:   Optional[float]= Query(None),
    search:         Optional[str]  = Query(None),
    page:           int            = Query(1, ge=1),
    page_size:      int            = Query(25, ge=1, le=100),
):
    from datetime import date as _date
    filters = ApplicationFilterParams(
        job_posting_id = job_posting_id,
        status         = status_f,
        source         = source,
        date_from      = _date.fromisoformat(date_from) if date_from else None,
        date_to        = _date.fromisoformat(date_to)   if date_to   else None,
        min_ai_score   = min_ai_score,
        search         = search,
        page           = page,
        page_size      = page_size,
    )
    return await service.get_applications(str(current_user.tenant_id), filters, db)


@router.post(
    "/applications",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an application (internal / HR-assisted)",
)
async def create_application(
    data: JobApplicationCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    app = await service.submit_application(str(current_user.tenant_id), data, db)
    return await service.get_application(str(current_user.tenant_id), str(app.id), db)


@router.get(
    "/applications/{app_id}",
    response_model=JobApplicationResponse,
    summary="Get application detail",
)
async def get_application(
    app_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await service.get_application(str(current_user.tenant_id), app_id, db)


@router.patch(
    "/applications/{app_id}/stage",
    response_model=JobApplicationResponse,
    summary="Move application through pipeline stages",
)
async def update_stage(
    app_id: str,
    data: ApplicationStageUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_recruiter(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    await service.update_application_stage(
        str(current_user.tenant_id), app_id, data, str(current_user.id), db
    )
    return await service.get_application(str(current_user.tenant_id), app_id, db)


@router.post(
    "/applications/upload-cv",
    response_model=CVUploadResponse,
    summary="Upload CV file (PDF/DOC/DOCX, max 5MB)",
)
async def upload_cv(
    file: UploadFile = File(...),
    current_user: Annotated[User, Depends(get_current_user)] = None,
    db: AsyncSession = Depends(get_db),
):
    return await service.upload_cv(file, str(current_user.tenant_id))


# ─── Interviews ───────────────────────────────────────────────────────────────

@router.post(
    "/interviews",
    response_model=list[InterviewResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Schedule an interview (one per interviewer)",
)
async def schedule_interview(
    data: InterviewScheduleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_recruiter(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    interviews = await service.schedule_interview(
        str(current_user.tenant_id), data, str(current_user.id), db
    )
    return [
        InterviewResponse(
            id               = str(iv.id),
            application_id   = str(iv.application_id),
            round_number     = iv.round_number,
            title            = iv.title,
            interviewer_id   = str(iv.interviewer_id) if iv.interviewer_id else None,
            interviewer      = None,
            scheduled_at     = iv.scheduled_at,
            duration_minutes = iv.duration_minutes,
            mode             = iv.mode,
            meeting_link     = iv.meeting_link,
            location         = iv.location,
            status           = iv.status,
            feedback         = iv.feedback,
            rating           = None,
            recommendation   = iv.recommendation,
            completed_at     = iv.completed_at,
            created_at       = iv.created_at,
        )
        for iv in interviews
    ]


@router.get(
    "/interviews/{interview_id}",
    response_model=InterviewResponse,
    summary="Get interview detail",
)
async def get_interview(
    interview_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy.orm import selectinload as _sil
    row = await db.execute(
        select(Interview)
        .options(_sil(Interview.interviewer))
        .where(Interview.id == interview_id)
    )
    iv = row.scalar_one_or_none()
    if not iv:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Interview not found.")
    return InterviewResponse(
        id               = str(iv.id),
        application_id   = str(iv.application_id),
        round_number     = iv.round_number,
        title            = iv.title,
        interviewer_id   = str(iv.interviewer_id) if iv.interviewer_id else None,
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
    )


@router.post(
    "/interviews/{interview_id}/feedback",
    response_model=InterviewResponse,
    summary="Submit interview feedback",
)
async def submit_feedback(
    interview_id: str,
    data: InterviewFeedbackRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    iv = await service.submit_interview_feedback(
        str(current_user.tenant_id), interview_id, data, str(current_user.id), db
    )
    return InterviewResponse(
        id               = str(iv.id),
        application_id   = str(iv.application_id),
        round_number     = iv.round_number,
        title            = iv.title,
        interviewer_id   = str(iv.interviewer_id) if iv.interviewer_id else None,
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
    )


@router.get(
    "/applications/{app_id}/interviews",
    response_model=list[InterviewResponse],
    summary="Get all interviews for an application",
)
async def get_app_interviews(
    app_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    interviews = await service.get_interviews_for_application(
        str(current_user.tenant_id), app_id, db
    )
    return [
        InterviewResponse(
            id               = str(iv.id),
            application_id   = str(iv.application_id),
            round_number     = iv.round_number,
            title            = iv.title,
            interviewer_id   = str(iv.interviewer_id) if iv.interviewer_id else None,
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
        )
        for iv in interviews
    ]


# ─── Offers ───────────────────────────────────────────────────────────────────

@router.post(
    "/offers",
    summary="Generate an offer letter PDF",
    status_code=status.HTTP_201_CREATED,
)
async def generate_offer(
    data: OfferLetterRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    if not _is_recruiter(current_user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions.")
    offer_url = await service.generate_offer_letter(
        str(current_user.tenant_id), data, str(current_user.id), db
    )
    return {"offer_url": offer_url}


@router.get(
    "/offers/{app_id}",
    summary="Download offer letter for an application",
)
async def get_offer(
    app_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    row = await db.execute(
        select(JobApplication)
        .join(JobPosting, JobPosting.id == JobApplication.job_posting_id)
        .where(JobApplication.id == app_id, JobPosting.tenant_id == str(current_user.tenant_id))
    )
    app = row.scalar_one_or_none()
    if not app or not app.offer_letter_url:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer letter not found.")

    file_path = os.path.join(
        os.environ.get("OFFER_LETTER_DIR", "/tmp/offers"),
        os.path.basename(app.offer_letter_url),
    )
    if not os.path.exists(file_path):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Offer letter file not found.")

    return FileResponse(
        file_path,
        media_type="application/pdf",
        filename=os.path.basename(file_path),
    )


# ─── Public endpoints (no auth) ───────────────────────────────────────────────

@public_router.get(
    "/jobs",
    response_model=list[PublicJobPostingResponse],
    summary="Public job listings (career portal)",
)
async def public_jobs(
    db: AsyncSession = Depends(get_db),
    employment_type: Optional[str] = Query(None),
    search:          Optional[str] = Query(None),
):
    """Open, non-internal jobs visible to the public."""
    from datetime import date as _date
    q = (
        select(JobPosting)
        .where(
            JobPosting.status    == "open",
        )
        .order_by(JobPosting.posted_at.desc())
    )
    # Exclude closed / past deadline
    today = _date.today()
    q = q.where(
        (JobPosting.closing_date == None) | (JobPosting.closing_date >= today)
    )

    if employment_type:
        q = q.where(JobPosting.employment_type == employment_type)
    if search:
        q = q.where(JobPosting.title.ilike(f"%{search}%"))

    rows = await db.execute(q)
    jobs = rows.scalars().all()

    results = []
    for job in jobs:
        # Fetch department separately for public response
        dept_name = None
        if job.department_id:
            from app.models import Department
            dept_row = await db.execute(
                select(Department).where(Department.id == job.department_id)
            )
            dept = dept_row.scalar_one_or_none()
            dept_name = dept.name if dept else None

        results.append(PublicJobPostingResponse(
            id                   = str(job.id),
            title                = job.title,
            location             = job.location,
            description          = job.description,
            requirements         = job.requirements.split("\n") if job.requirements else [],
            responsibilities     = job.responsibilities.split("\n") if job.responsibilities else [],
            employment_type      = job.employment_type,
            experience_years_min = job.experience_years_min,
            experience_years_max = job.experience_years_max,
            salary_min           = job.salary_min if job.is_salary_visible else None,
            salary_max           = job.salary_max if job.is_salary_visible else None,
            is_salary_visible    = job.is_salary_visible,
            required_skills      = job.required_skills or [],
            vacancies            = job.vacancies,
            closing_date         = job.closing_date,
            department_name      = dept_name,
            posted_at            = job.posted_at,
        ))

    return results


@public_router.post(
    "/jobs/{job_id}/apply",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    summary="Public application submission (career portal)",
)
async def public_apply(
    job_id: str,
    data: JobApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    """No auth required. Validates job is open then creates application."""
    # Override job_posting_id with URL parameter
    data = data.model_copy(update={"job_posting_id": job_id})

    # For public submissions we need the tenant_id from the job
    row = await db.execute(select(JobPosting).where(JobPosting.id == job_id))
    job = row.scalar_one_or_none()
    if not job:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Job not found.")
    if job.status != "open":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "This position is not accepting applications.")

    app = await service.submit_application(str(job.tenant_id), data, db)
    return {"message": "Application submitted successfully.", "application_id": str(app.id)}

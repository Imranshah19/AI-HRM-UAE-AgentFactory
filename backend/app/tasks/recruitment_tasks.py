"""
AI-HRMS — Recruitment module Celery tasks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime

from celery import shared_task

logger = logging.getLogger(__name__)


# ─── AI CV Scoring ────────────────────────────────────────────────────────────

@shared_task(name="recruitment.ai_score_cv", bind=True, max_retries=2)
def ai_score_cv(self, application_id: str) -> dict:
    """
    Download CV, parse it, score against job requirements, and store result.
    Notifies recruiter if score >= 70.
    """

    async def _run() -> dict:
        from sqlalchemy import select, update as sql_update
        from sqlalchemy.orm import selectinload
        from app.core.database import AsyncSessionLocal
        from app.models.recruitment import JobApplication, JobPosting
        from app.api.v1.recruitment.ai_scorer import (
            extract_cv_text, parse_cv_sections, score_cv_against_job
        )

        async with AsyncSessionLocal() as db:
            row = await db.execute(
                select(JobApplication)
                .options(
                    selectinload(JobApplication.job_posting)
                )
                .where(JobApplication.id == application_id)
            )
            app = row.scalar_one_or_none()
            if not app:
                logger.error("Application %s not found for AI scoring", application_id)
                return {"error": "not_found"}

            job = app.job_posting
            if not app.cv_url:
                logger.info("Application %s has no CV — skipping scoring", application_id)
                return {"skipped": "no_cv"}

            # Extract + parse CV
            try:
                cv_text = extract_cv_text(app.cv_url)
                if not cv_text.strip():
                    logger.warning("CV text empty for application %s", application_id)
                    return {"skipped": "empty_cv"}

                cv_data = parse_cv_sections(cv_text)
                result  = score_cv_against_job(
                    cv_data          = cv_data,
                    job_title        = job.title if job else "",
                    required_skills  = job.required_skills or [] if job else [],
                    experience_min   = job.experience_years_min if job else 0,
                    experience_max   = job.experience_years_max if job else None,
                    description      = job.description or "" if job else "",
                )
            except Exception as exc:
                logger.exception("CV scoring failed for application %s: %s", application_id, exc)
                return {"error": str(exc)}

            # Preserve existing JSONB explanation (stage history etc.)
            existing_expl = app.ai_explanation or {}
            existing_expl.update({
                "score":            result.score,
                "skills_matched":   result.skills_matched,
                "skills_missing":   result.skills_missing,
                "skills_score":     result.skills_score,
                "experience_score": result.experience_score,
                "title_relevance":  result.title_relevance,
                "education_score":  result.education_score,
                "explanation":      result.explanation,
                "bias_flags":       result.bias_flags,
            })

            await db.execute(
                sql_update(JobApplication)
                .where(JobApplication.id == application_id)
                .values(
                    ai_score       = result.score,
                    ai_explanation = existing_expl,
                    ai_scored_at   = datetime.utcnow(),
                )
            )
            await db.commit()

            logger.info(
                "AI scored application %s: %.1f/100 (%s)",
                application_id, result.score, result.explanation[:80],
            )

            # Notify recruiter if high score
            if result.score >= 70 and job:
                _notify_high_score(str(job.tenant_id), application_id, app.candidate_name, result.score)

            return {
                "application_id": application_id,
                "score":          result.score,
                "explanation":    result.explanation,
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("ai_score_cv task failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


# ─── Confirmation Email ───────────────────────────────────────────────────────

@shared_task(name="recruitment.send_application_confirmation", bind=True, max_retries=3)
def send_application_confirmation(self, application_id: str) -> None:
    """Send application acknowledgement email to candidate."""

    async def _run() -> None:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.recruitment import JobApplication, JobPosting
        from app.core.config import settings

        async with AsyncSessionLocal() as db:
            row = await db.execute(
                select(JobApplication)
                .options(__import__("sqlalchemy.orm", fromlist=["selectinload"])
                         .selectinload(JobApplication.job_posting))
                .where(JobApplication.id == application_id)
            )
            app = row.scalar_one_or_none()
            if not app:
                return

            job_title = app.job_posting.title if app.job_posting else "the position"
            subject   = f"Application Received — {job_title}"
            body      = (
                f"Dear {app.candidate_name},\n\n"
                f"Thank you for applying for <b>{job_title}</b>. "
                f"We have received your application and will review it shortly.\n\n"
                f"You will be contacted if your profile matches our requirements.\n\n"
                f"Best regards,\nHR Recruitment Team\nAI-HRMS"
            )

            try:
                import smtplib
                from email.mime.text      import MIMEText
                from email.mime.multipart import MIMEMultipart

                msg = MIMEMultipart()
                msg["From"]    = getattr(settings, "EMAIL_FROM", "recruitment@example.com")
                msg["To"]      = app.candidate_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "html"))

                smtp_host = getattr(settings, "SMTP_HOST", "localhost")
                smtp_port = getattr(settings, "SMTP_PORT", 587)
                smtp_user = getattr(settings, "SMTP_USER", "")
                smtp_pass = getattr(settings, "SMTP_PASSWORD", "")

                with smtplib.SMTP(smtp_host, smtp_port) as server:
                    server.starttls()
                    if smtp_user:
                        server.login(smtp_user, smtp_pass)
                    server.sendmail(msg["From"], [msg["To"]], msg.as_string())

                logger.info("Confirmation email sent to %s", app.candidate_email)
            except Exception as exc:
                logger.warning("Confirmation email failed for %s: %s", app.candidate_email, exc)

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.exception("send_application_confirmation task failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


# ─── Interview Invitation ─────────────────────────────────────────────────────

@shared_task(name="recruitment.send_interview_invitation", bind=True, max_retries=3)
def send_interview_invitation(self, interview_id: str) -> None:
    """Send interview schedule email to interviewer and candidate."""

    async def _run() -> None:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.core.database import AsyncSessionLocal
        from app.models.recruitment import Interview, JobApplication, JobPosting
        from app.models import Employee
        from app.core.config import settings

        async with AsyncSessionLocal() as db:
            row = await db.execute(
                select(Interview)
                .options(
                    selectinload(Interview.application).options(
                        selectinload(JobApplication.job_posting)
                    ),
                    selectinload(Interview.interviewer),
                )
                .where(Interview.id == interview_id)
            )
            iv = row.scalar_one_or_none()
            if not iv:
                return

            app       = iv.application
            job       = app.job_posting if app else None
            job_title = job.title if job else "Position"
            dt_str    = iv.scheduled_at.strftime("%A, %d %B %Y at %H:%M") if iv.scheduled_at else "TBD"
            location  = iv.meeting_link or iv.location or "Details to follow"

            recipients = [app.candidate_email] if app else []
            if iv.interviewer and iv.interviewer.work_email:
                recipients.append(iv.interviewer.work_email)

            subject = f"Interview Scheduled: {job_title} — {dt_str}"
            body    = (
                f"An interview has been scheduled for <b>{job_title}</b>.\n\n"
                f"Date & Time: {dt_str}\n"
                f"Duration: {iv.duration_minutes} minutes\n"
                f"Mode: {iv.mode}\n"
                f"Location/Link: {location}\n\n"
                f"Please confirm your attendance.\n\nBest regards,\nHR Team"
            )

            try:
                import smtplib
                from email.mime.text      import MIMEText
                from email.mime.multipart import MIMEMultipart
                from app.core.config      import settings as _s

                for recipient in recipients:
                    msg = MIMEMultipart()
                    msg["From"]    = getattr(_s, "EMAIL_FROM", "recruitment@example.com")
                    msg["To"]      = recipient
                    msg["Subject"] = subject
                    msg.attach(MIMEText(body, "html"))

                    with smtplib.SMTP(getattr(_s, "SMTP_HOST", "localhost"),
                                      getattr(_s, "SMTP_PORT", 587)) as server:
                        server.starttls()
                        user = getattr(_s, "SMTP_USER", "")
                        if user:
                            server.login(user, getattr(_s, "SMTP_PASSWORD", ""))
                        server.sendmail(msg["From"], [msg["To"]], msg.as_string())

                logger.info("Interview invitations sent for interview %s", interview_id)
            except Exception as exc:
                logger.warning("Interview invite failed: %s", exc)

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.exception("send_interview_invitation task failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


# ─── Convert to Employee ──────────────────────────────────────────────────────

@shared_task(name="recruitment.convert_to_employee", bind=True, max_retries=2)
def convert_to_employee(self, application_id: str) -> dict:
    """
    When a candidate is marked as Hired, pre-create an Employee record
    with status=onboarding and notify HR to complete the profile.
    """

    async def _run() -> dict:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.core.database import AsyncSessionLocal
        from app.models.recruitment import JobApplication, JobPosting
        from app.models import Employee, Notification, User

        async with AsyncSessionLocal() as db:
            row = await db.execute(
                select(JobApplication)
                .options(
                    selectinload(JobApplication.job_posting).options(
                        selectinload(JobPosting.department),
                        selectinload(JobPosting.designation),
                    )
                )
                .where(JobApplication.id == application_id)
            )
            app = row.scalar_one_or_none()
            if not app:
                return {"error": "not_found"}

            # Check if already converted
            if app.hired_employee_id:
                return {"skipped": "already_converted", "employee_id": str(app.hired_employee_id)}

            job = app.job_posting
            tenant_id = str(job.tenant_id) if job else None
            if not tenant_id:
                return {"error": "no_tenant"}

            # Split name
            name_parts  = app.candidate_name.strip().split(" ", 1)
            first_name  = name_parts[0]
            last_name   = name_parts[1] if len(name_parts) > 1 else ""

            # Generate employee code
            emp_code = f"EMP{str(_uuid_gen())[:6].upper()}"

            new_emp = Employee(
                tenant_id         = tenant_id,
                employee_code     = emp_code,
                first_name        = first_name,
                last_name         = last_name,
                work_email        = app.candidate_email,
                personal_phone    = app.candidate_phone,
                department_id     = str(job.department_id) if (job and job.department_id) else None,
                designation_id    = str(job.designation_id) if (job and job.designation_id) else None,
                employment_status = "inactive",  # HR completes onboarding
                contract_type     = "permanent",
                joining_date      = date.today(),
            )
            db.add(new_emp)
            await db.flush()

            app.hired_employee_id = str(new_emp.id)
            await db.commit()

            # Notify HR users
            hr_users = await db.execute(
                select(User).where(
                    User.tenant_id    == tenant_id,
                    User.is_superadmin == True,
                )
            )
            for hr_user in hr_users.scalars().all():
                db.add(Notification(
                    tenant_id      = tenant_id,
                    user_id        = str(hr_user.id),
                    title          = "New Hire — Onboarding Required",
                    message        = (
                        f"{app.candidate_name} has been hired for {job.title if job else 'position'}. "
                        f"Please complete their employee profile. (Code: {emp_code})"
                    ),
                    category       = "recruitment",
                    reference_id   = str(new_emp.id),
                    reference_type = "employee",
                ))
            await db.commit()

            logger.info("Converted application %s → employee %s", application_id, new_emp.id)
            return {"application_id": application_id, "employee_id": str(new_emp.id)}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("convert_to_employee task failed: %s", exc)
        raise self.retry(exc=exc, countdown=60)


def _uuid_gen():
    import uuid
    return uuid.uuid4().hex[:6]


# ─── Offer Letter Email ───────────────────────────────────────────────────────

@shared_task(name="recruitment.send_offer_letter_email", bind=True, max_retries=3)
def send_offer_letter_email(self, application_id: str, offer_url: str) -> None:
    """Send offer letter email with PDF link/attachment to candidate."""

    async def _run() -> None:
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models.recruitment import JobApplication, JobPosting
        from sqlalchemy.orm import selectinload
        from app.core.config import settings

        async with AsyncSessionLocal() as db:
            row = await db.execute(
                select(JobApplication)
                .options(selectinload(JobApplication.job_posting))
                .where(JobApplication.id == application_id)
            )
            app = row.scalar_one_or_none()
            if not app:
                return

            job_title = app.job_posting.title if app.job_posting else "the position"
            subject   = f"Offer Letter — {job_title}"
            body      = (
                f"Dear {app.candidate_name},\n\n"
                f"We are delighted to offer you the position of <b>{job_title}</b>.\n\n"
                f"Please find your offer letter attached or download it from: {offer_url}\n\n"
                f"Kindly sign and return a copy at your earliest convenience.\n\n"
                f"Best regards,\nHR Department\nAI-HRMS"
            )

            try:
                import smtplib
                from email.mime.text import MIMEText
                from email.mime.multipart import MIMEMultipart
                import os

                msg = MIMEMultipart()
                msg["From"]    = getattr(settings, "EMAIL_FROM", "recruitment@example.com")
                msg["To"]      = app.candidate_email
                msg["Subject"] = subject
                msg.attach(MIMEText(body, "html"))

                # Attach PDF if available
                local_path = os.path.join(
                    os.environ.get("OFFER_LETTER_DIR", "/tmp/offers"),
                    os.path.basename(offer_url),
                )
                if os.path.exists(local_path):
                    from email.mime.application import MIMEApplication
                    with open(local_path, "rb") as f:
                        part = MIMEApplication(f.read(), Name=os.path.basename(local_path))
                    part["Content-Disposition"] = f'attachment; filename="{os.path.basename(local_path)}"'
                    msg.attach(part)

                with smtplib.SMTP(getattr(settings, "SMTP_HOST", "localhost"),
                                  getattr(settings, "SMTP_PORT", 587)) as server:
                    server.starttls()
                    u = getattr(settings, "SMTP_USER", "")
                    if u:
                        server.login(u, getattr(settings, "SMTP_PASSWORD", ""))
                    server.sendmail(msg["From"], [msg["To"]], msg.as_string())

                logger.info("Offer letter email sent to %s", app.candidate_email)
            except Exception as exc:
                logger.warning("Offer letter email failed: %s", exc)

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.exception("send_offer_letter_email task failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _notify_high_score(tenant_id: str, app_id: str, candidate_name: str, score: float) -> None:
    """In-app notification for recruiter when AI finds a strong candidate."""

    async def _notif():
        from sqlalchemy import select
        from app.core.database import AsyncSessionLocal
        from app.models import User, Notification

        async with AsyncSessionLocal() as db:
            hr_rows = await db.execute(
                select(User).where(
                    User.tenant_id    == tenant_id,
                    User.is_superadmin == True,
                )
            )
            for hr in hr_rows.scalars().all():
                db.add(Notification(
                    tenant_id      = tenant_id,
                    user_id        = str(hr.id),
                    title          = "Strong Candidate Detected",
                    message        = (
                        f"{candidate_name} scored {score:.0f}/100 on AI screening. "
                        f"Worth reviewing!"
                    ),
                    category       = "recruitment",
                    reference_id   = app_id,
                    reference_type = "application",
                ))
            await db.commit()

    try:
        asyncio.run(_notif())
    except Exception as exc:
        logger.warning("High-score notification failed: %s", exc)

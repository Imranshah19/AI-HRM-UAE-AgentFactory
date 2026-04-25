"""
AI-HRMS — Employee-related Celery tasks.

Tasks:
  - send_welcome_email     — send login credentials to the new employee
  - trigger_offboarding_workflow — create clearance items, notify departments
"""

import structlog
from celery import Celery  # type: ignore[import-untyped]

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ─── Celery application ────────────────────────────────────────────────────────
# We instantiate Celery here; the app's celery worker process imports this module.

celery_app = Celery(
    "ai_hrms",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "app.tasks.employee_tasks.*": {"queue": "default"},
    },
    # Retry policy defaults
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


# ─── Welcome Email ─────────────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="employee_tasks.send_welcome_email",
    max_retries=3,
    default_retry_delay=60,  # seconds
)
def send_welcome_email(self, employee_id: str, temp_password: str) -> dict:
    """
    Send a welcome email with login credentials to the newly created employee.

    Args:
        employee_id:   UUID string of the Employee record.
        temp_password: Plaintext temporary password (sent once; user must change).

    Returns:
        dict with status and details.
    """
    import asyncio

    async def _run():
        from sqlalchemy import select as _select
        from app.core.database import AsyncSessionLocal
        from app.models.employee import Employee

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                _select(Employee).where(Employee.id == employee_id)
            )
            employee = result.scalar_one_or_none()
            if employee is None:
                logger.error("send_welcome_email: employee not found", employee_id=employee_id)
                return {"status": "error", "reason": "employee_not_found"}

            if not employee.work_email:
                logger.warning(
                    "send_welcome_email: no work email",
                    employee_id=employee_id,
                )
                return {"status": "skipped", "reason": "no_work_email"}

            _send_via_sendgrid(
                to_email=employee.work_email,
                to_name=employee.full_name,
                temp_password=temp_password,
                employee_code=employee.employee_code,
            )

            logger.info(
                "Welcome email sent",
                employee_id=employee_id,
                email=employee.work_email,
            )
            return {"status": "sent", "email": employee.work_email}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error("send_welcome_email failed", employee_id=employee_id, error=str(exc))
        raise self.retry(exc=exc)


def _send_via_sendgrid(
    to_email:      str,
    to_name:       str,
    temp_password: str,
    employee_code: str,
) -> None:
    """
    Dispatch a welcome email via SendGrid.
    Falls back to a structured log if SENDGRID_API_KEY is not configured.
    """
    if not settings.SENDGRID_API_KEY:
        logger.info(
            "Welcome email (no SendGrid key — dev mode)",
            to=to_email,
            employee_code=employee_code,
            temp_password="[REDACTED]",
        )
        return

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        html_body = f"""
        <html><body>
        <h2>Welcome to {settings.APP_NAME}!</h2>
        <p>Hi {to_name},</p>
        <p>Your employee account has been created. Please log in with the credentials below:</p>
        <ul>
          <li><strong>Employee Code:</strong> {employee_code}</li>
          <li><strong>Login Email:</strong> {to_email}</li>
          <li><strong>Temporary Password:</strong> <code>{temp_password}</code></li>
        </ul>
        <p>You will be asked to change your password on first login.</p>
        <p>Login portal: <a href="{settings.FRONTEND_URL}">{settings.FRONTEND_URL}</a></p>
        <hr>
        <p style="color:#666;font-size:12px;">This is an automated message. Do not reply.</p>
        </body></html>
        """

        message = Mail(
            from_email=(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME),
            to_emails=to_email,
            subject=f"Welcome to {settings.APP_NAME} — Your Account Is Ready",
            html_content=html_body,
        )
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        logger.debug("SendGrid response", status_code=response.status_code)
    except Exception as exc:
        logger.error("SendGrid send failed", error=str(exc))
        raise


# ─── Offboarding Workflow ──────────────────────────────────────────────────────

@celery_app.task(
    bind=True,
    name="employee_tasks.trigger_offboarding_workflow",
    max_retries=2,
    default_retry_delay=120,
)
def trigger_offboarding_workflow(self, employee_id: str, reason: str) -> dict:
    """
    Kick off the offboarding workflow for a terminated / resigned employee.

    Steps:
      1. Log the offboarding event.
      2. Create notification records for IT, Finance, and Admin.
      3. (Future) Create asset-return clearance checklist.

    Args:
        employee_id: UUID string of the Employee.
        reason:      Termination/resignation reason text.
    """
    import asyncio

    async def _run():
        from sqlalchemy import select as _select
        from app.core.database import AsyncSessionLocal
        from app.models.employee import Employee
        from app.models.notification import Notification
        from app.models.tenant import User

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                _select(Employee).where(Employee.id == employee_id)
            )
            employee = result.scalar_one_or_none()
            if employee is None:
                logger.error(
                    "trigger_offboarding_workflow: employee not found",
                    employee_id=employee_id,
                )
                return {"status": "error", "reason": "employee_not_found"}

            # Find superadmin / HR users in the same tenant to send notifications to
            users_result = await db.execute(
                _select(User).where(
                    User.tenant_id == employee.tenant_id,
                    User.is_active.is_(True),
                    User.is_superadmin.is_(True),
                )
            )
            recipients = list(users_result.scalars().all())

            notifications_created = 0
            for user in recipients:
                notif = Notification(
                    tenant_id=employee.tenant_id,
                    user_id=user.id,
                    title=f"Offboarding: {employee.full_name} ({employee.employee_code})",
                    message=(
                        f"Employee {employee.full_name} has been offboarded. "
                        f"Reason: {reason or 'Not provided'}. "
                        f"Please complete IT, Finance, and HR clearance tasks."
                    ),
                    channel="in_app",
                    category="offboarding",
                    extra_data={
                        "employee_id":   employee_id,
                        "employee_code": employee.employee_code,
                        "reason":        reason,
                    },
                )
                db.add(notif)
                notifications_created += 1

            await db.commit()

            logger.info(
                "Offboarding workflow triggered",
                employee_id=employee_id,
                notifications_created=notifications_created,
            )
            return {
                "status":                "triggered",
                "employee_id":           employee_id,
                "notifications_created": notifications_created,
            }

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(
            "trigger_offboarding_workflow failed",
            employee_id=employee_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)

"""
AI-HRMS — Leave module Celery tasks.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

from celery import shared_task

logger = logging.getLogger(__name__)


# ─── Notify manager of new leave request ─────────────────────────────────────

@shared_task(name="leave.notify_manager_new_request", bind=True, max_retries=3)
def notify_manager_new_request(self, request_id: str) -> None:
    """Send in-app + email notification to employee's manager."""

    async def _run() -> None:
        from sqlalchemy import select as _select
        from app.core.database import AsyncSessionLocal
        from app.models import LeaveRequest, Employee, User, Notification
        from app.core.config import settings

        async with AsyncSessionLocal() as db:
            # Load the leave request with relations
            row = await db.execute(
                _select(LeaveRequest).where(LeaveRequest.id == request_id)
            )
            req = row.scalar_one_or_none()
            if not req:
                logger.warning("leave_request %s not found in notify_manager task", request_id)
                return

            # Load employee
            emp_row = await db.execute(
                _select(Employee).where(Employee.id == req.employee_id)
            )
            emp = emp_row.scalar_one_or_none()
            if not emp or not emp.manager_id:
                logger.info("Employee %s has no manager; skipping notification", req.employee_id)
                return

            # Load manager's user record
            mgr_row = await db.execute(
                _select(User).where(User.id == Employee.user_id, Employee.id == emp.manager_id)
            )
            # fallback: load manager employee then user
            mgr_emp_row = await db.execute(
                _select(Employee).where(Employee.id == emp.manager_id)
            )
            mgr_emp = mgr_emp_row.scalar_one_or_none()
            if not mgr_emp or not mgr_emp.user_id:
                return

            # Create in-app notification
            notification = Notification(
                tenant_id=req.tenant_id,
                user_id=mgr_emp.user_id,
                title="New Leave Request",
                message=(
                    f"{emp.first_name} {emp.last_name} has applied for leave "
                    f"from {req.start_date} to {req.end_date} ({req.days} day(s)). "
                    f"Please review and take action."
                ),
                category="leave",
                reference_id=req.id,
                reference_type="leave_request",
            )
            db.add(notification)
            await db.commit()

            # Email (SendGrid or log in dev)
            mgr_user_row = await db.execute(
                _select(User).where(User.id == mgr_emp.user_id)
            )
            mgr_user = mgr_user_row.scalar_one_or_none()
            if settings.SENDGRID_API_KEY and mgr_user:
                try:
                    import sendgrid
                    from sendgrid.helpers.mail import Mail
                    sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
                    message = Mail(
                        from_email=settings.FROM_EMAIL,
                        to_emails=mgr_user.email,
                        subject=f"[AI-HRMS] Leave Request from {emp.first_name} {emp.last_name}",
                        html_content=(
                            f"<p>Hi,</p>"
                            f"<p><strong>{emp.first_name} {emp.last_name}</strong> has submitted a "
                            f"leave request from <strong>{req.start_date}</strong> to "
                            f"<strong>{req.end_date}</strong> ({req.days} working day(s)).</p>"
                            f"<p>Reason: {req.reason}</p>"
                            f"<p>Please log in to AI-HRMS to approve or reject this request.</p>"
                        ),
                    )
                    sg.send(message)
                except Exception as exc:
                    logger.exception("SendGrid error in notify_manager_new_request: %s", exc)
            else:
                logger.info(
                    "[DEV] Would email manager %s about leave request %s",
                    mgr_user.email if mgr_user else "unknown",
                    request_id,
                )

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.exception("notify_manager_new_request failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


# ─── Notify employee of approval decision ────────────────────────────────────

@shared_task(name="leave.notify_employee_decision", bind=True, max_retries=3)
def notify_employee_decision(self, request_id: str, action: str) -> None:
    """Send in-app + email to employee when their request is approved/rejected."""

    async def _run() -> None:
        from sqlalchemy import select as _select
        from app.core.database import AsyncSessionLocal
        from app.models import LeaveRequest, Employee, User, Notification
        from app.core.config import settings

        async with AsyncSessionLocal() as db:
            row = await db.execute(
                _select(LeaveRequest).where(LeaveRequest.id == request_id)
            )
            req = row.scalar_one_or_none()
            if not req:
                return

            emp_row = await db.execute(
                _select(Employee).where(Employee.id == req.employee_id)
            )
            emp = emp_row.scalar_one_or_none()
            if not emp or not emp.user_id:
                return

            is_approved = action == "approve"
            title   = "Leave Request Approved" if is_approved else "Leave Request Rejected"
            message = (
                f"Your leave request from {req.start_date} to {req.end_date} "
                f"({req.days} day(s)) has been {'approved' if is_approved else 'rejected'}."
            )
            if not is_approved and req.rejection_reason:
                message += f" Reason: {req.rejection_reason}"

            notification = Notification(
                tenant_id=req.tenant_id,
                user_id=emp.user_id,
                title=title,
                message=message,
                category="leave",
                reference_id=req.id,
                reference_type="leave_request",
            )
            db.add(notification)
            await db.commit()

            # Email
            user_row = await db.execute(_select(User).where(User.id == emp.user_id))
            user = user_row.scalar_one_or_none()
            if settings.SENDGRID_API_KEY and user:
                try:
                    import sendgrid
                    from sendgrid.helpers.mail import Mail
                    sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
                    sg.send(Mail(
                        from_email=settings.FROM_EMAIL,
                        to_emails=user.email,
                        subject=f"[AI-HRMS] {title}",
                        html_content=f"<p>Hi {emp.first_name},</p><p>{message}</p>",
                    ))
                except Exception as exc:
                    logger.exception("SendGrid error in notify_employee_decision: %s", exc)
            else:
                logger.info("[DEV] Would email employee %s: %s", emp.user_id, title)

    try:
        asyncio.run(_run())
    except Exception as exc:
        logger.exception("notify_employee_decision failed: %s", exc)
        raise self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


# ─── Initialise annual leave balances (Celery beat: Jan 1) ───────────────────

@shared_task(name="leave.initialize_annual_leave_balances")
def initialize_annual_leave_balances(tenant_id: str, year: int | None = None) -> dict:
    """
    Create leave_balance rows for all active employees × all active leave types
    for the given year.  Applies carry-forward from previous year.
    Idempotent: skips employees that already have a balance record for that year.
    """

    async def _run() -> dict:
        from sqlalchemy import select as _select, and_ as _and
        from app.core.database import AsyncSessionLocal
        from app.models import LeaveType, LeaveBalance, Employee
        from datetime import datetime

        target_year = year or datetime.utcnow().year

        async with AsyncSessionLocal() as db:
            # Active leave types for tenant
            lt_rows = await db.execute(
                _select(LeaveType).where(
                    LeaveType.tenant_id == tenant_id,
                    LeaveType.is_active.is_(True),
                )
            )
            leave_types = lt_rows.scalars().all()

            # Active employees
            emp_rows = await db.execute(
                _select(Employee).where(
                    Employee.tenant_id == tenant_id,
                    Employee.employment_status == "active",
                )
            )
            employees = emp_rows.scalars().all()

            created = 0
            for emp in employees:
                for lt in leave_types:
                    # Check if balance already exists
                    exists = await db.execute(
                        _select(LeaveBalance).where(
                            _and(
                                LeaveBalance.tenant_id    == tenant_id,
                                LeaveBalance.employee_id  == emp.id,
                                LeaveBalance.leave_type_id == lt.id,
                                LeaveBalance.year         == target_year,
                            )
                        )
                    )
                    if exists.scalar_one_or_none():
                        continue

                    # Carry forward from previous year
                    carry = 0
                    if lt.carry_forward:
                        prev = await db.execute(
                            _select(LeaveBalance).where(
                                _and(
                                    LeaveBalance.tenant_id    == tenant_id,
                                    LeaveBalance.employee_id  == emp.id,
                                    LeaveBalance.leave_type_id == lt.id,
                                    LeaveBalance.year         == target_year - 1,
                                )
                            )
                        )
                        prev_bal = prev.scalar_one_or_none()
                        if prev_bal:
                            carry = min(
                                max(prev_bal.total_days - prev_bal.used_days, 0),
                                lt.max_carry_forward_days,
                            )

                    db.add(LeaveBalance(
                        tenant_id     = tenant_id,
                        employee_id   = emp.id,
                        leave_type_id = lt.id,
                        year          = target_year,
                        total_days    = lt.days_allowed + carry,
                        used_days     = 0,
                        carried_forward = carry,
                    ))
                    created += 1

            await db.commit()
            logger.info(
                "initialize_annual_leave_balances: tenant=%s year=%s created=%d",
                tenant_id, target_year, created,
            )
            return {"created": created, "year": target_year}

    return asyncio.run(_run())


# ─── Leave balance reminder (Celery beat: Dec 15) ────────────────────────────

@shared_task(name="leave.send_leave_balance_reminder")
def send_leave_balance_reminder(tenant_id: str) -> dict:
    """
    Send each active employee a reminder of their remaining leave balance
    so they can plan before year-end.
    """

    async def _run() -> dict:
        from sqlalchemy import select as _select
        from app.core.database import AsyncSessionLocal
        from app.models import LeaveBalance, Employee, User, Notification
        from datetime import datetime

        year = datetime.utcnow().year
        sent = 0

        async with AsyncSessionLocal() as db:
            emp_rows = await db.execute(
                _select(Employee).where(
                    Employee.tenant_id == tenant_id,
                    Employee.employment_status == "active",
                )
            )
            employees = emp_rows.scalars().all()

            for emp in employees:
                bal_rows = await db.execute(
                    _select(LeaveBalance).where(
                        LeaveBalance.tenant_id   == tenant_id,
                        LeaveBalance.employee_id == emp.id,
                        LeaveBalance.year        == year,
                    )
                )
                balances = bal_rows.scalars().all()
                if not balances or not emp.user_id:
                    continue

                lines = "\n".join(
                    f"• {b.leave_type_id}: {b.total_days - b.used_days} days remaining"
                    for b in balances
                )
                db.add(Notification(
                    tenant_id=tenant_id,
                    user_id=emp.user_id,
                    title="Year-End Leave Balance Reminder",
                    message=(
                        f"As the year draws to a close, here is your remaining leave balance:\n{lines}\n"
                        f"Please plan and apply for any leave before December 31."
                    ),
                    category="leave",
                ))
                sent += 1

            await db.commit()
        return {"sent": sent}

    return asyncio.run(_run())

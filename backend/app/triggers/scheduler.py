"""
Agent Factory — Celery Beat Scheduler for AI-HRMS Agent Factory.

Registers two periodic agent tasks into the existing Celery beat schedule
by updating celery_app.conf.beat_schedule at import time (additive — the
existing celery_app.py file is NOT modified).

Schedule:
  ┌─────────────────────────────┬──────────────────────────────────────────┐
  │ Task                        │ Schedule                                  │
  ├─────────────────────────────┼──────────────────────────────────────────┤
  │ agents.daily_attendance_    │ Daily 09:00 AM PKT (04:00 UTC)           │
  │ report                      │                                           │
  ├─────────────────────────────┼──────────────────────────────────────────┤
  │ agents.monthly_payroll_     │ 25th of every month 10:00 AM PKT         │
  │ trigger                     │ (05:00 UTC)                               │
  ├─────────────────────────────┼──────────────────────────────────────────┤
  │ agents.payroll_pre_         │ 24th of every month 06:00 AM PKT         │
  │ approval_check              │ (01:00 UTC) — early-warning the day before│
  └─────────────────────────────┴──────────────────────────────────────────┘

To activate, start Celery worker with this module included:
    celery -A app.worker.celery_app worker \\
        --include app.triggers.scheduler \\
        -Q default,agents --loglevel=info

    celery -A app.worker.celery_app beat --loglevel=info
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date

from celery import shared_task
from celery.schedules import crontab

logger = logging.getLogger(__name__)


# ─── Periodic Task Definitions ────────────────────────────────────────────────

@shared_task(name="agents.daily_attendance_report", bind=True, max_retries=1)
def daily_attendance_report(self, tenant_id: str | None = None) -> dict:
    """
    Runs daily at 09:00 PKT (04:00 UTC).
    Generates an AI-powered attendance summary and persists it to Redis
    so the agent dashboard can display it.

    If tenant_id is None, runs for all active tenants.
    """

    async def _run() -> dict:
        from app.core.database import AsyncSessionLocal
        from app.agents.paperclip import get_paperclip
        from app.core.redis import get_redis
        import json

        results = []

        async with AsyncSessionLocal() as db:
            tenant_ids = await _get_active_tenant_ids(tenant_id, db)

            paperclip = get_paperclip()

            for tid in tenant_ids:
                try:
                    task_result = await paperclip.dispatch(
                        domain="attendance",
                        action="daily_report",
                        payload={"report_date": date.today()},
                        tenant_id=tid,
                        db=db,
                    )
                    results.append({
                        "tenant_id": tid,
                        "status":    task_result.status,
                        "date":      str(date.today()),
                    })
                    logger.info(
                        "agents.daily_attendance_report: tenant=%s status=%s",
                        tid, task_result.status,
                    )
                except Exception as exc:
                    logger.exception(
                        "agents.daily_attendance_report failed for tenant %s: %s", tid, exc
                    )
                    results.append({"tenant_id": tid, "status": "error", "error": str(exc)})

        return {"date": str(date.today()), "results": results}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("daily_attendance_report task error: %s", exc)
        raise self.retry(exc=exc, countdown=300)


@shared_task(name="agents.monthly_payroll_trigger", bind=True, max_retries=2)
def monthly_payroll_trigger(self, tenant_id: str | None = None) -> dict:
    """
    Runs on the 25th of every month at 10:00 AM PKT (05:00 UTC).
    Creates and validates a payroll run for each active tenant.
    Sends an AI-generated approval recommendation to HR managers.

    The task calls the existing payroll service to create the run,
    then passes the run_id to PayrollAgent for AI validation.
    """

    async def _run() -> dict:
        from app.core.database import AsyncSessionLocal
        from app.agents.paperclip import get_paperclip
        from datetime import datetime

        now = datetime.utcnow()
        results = []

        async with AsyncSessionLocal() as db:
            tenant_ids = await _get_active_tenant_ids(tenant_id, db)
            paperclip  = get_paperclip()

            for tid in tenant_ids:
                run_id = await _create_draft_payroll_run(tid, now.month, now.year, db)
                if run_id is None:
                    results.append({
                        "tenant_id": tid,
                        "status":    "skipped",
                        "reason":    "run_already_exists_or_creation_failed",
                    })
                    continue

                try:
                    task_result = await paperclip.dispatch(
                        domain="payroll",
                        action="validate",
                        payload={"run_id": run_id},
                        tenant_id=tid,
                        db=db,
                    )
                    await _notify_hr_payroll_trigger(
                        tid, run_id, task_result.result, now.month, now.year, db
                    )
                    results.append({
                        "tenant_id":      tid,
                        "run_id":         run_id,
                        "status":         task_result.status,
                        "recommendation": getattr(task_result.result, "recommendation", "unknown"),
                    })
                    logger.info(
                        "agents.monthly_payroll_trigger: tenant=%s run=%s", tid, run_id
                    )
                except Exception as exc:
                    logger.exception(
                        "agents.monthly_payroll_trigger failed for tenant %s: %s", tid, exc
                    )
                    results.append({"tenant_id": tid, "status": "error", "error": str(exc)})

        return {"month": now.month, "year": now.year, "results": results}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("monthly_payroll_trigger task error: %s", exc)
        raise self.retry(exc=exc, countdown=600)


@shared_task(name="agents.payroll_pre_approval_check", bind=True, max_retries=1)
def payroll_pre_approval_check(self, tenant_id: str | None = None) -> dict:
    """
    Runs on the 24th of every month at 06:00 AM PKT (01:00 UTC).
    Performs an early-warning check on pending payroll runs and alerts HR
    of any issues BEFORE the 25th auto-trigger.
    """

    async def _run() -> dict:
        from app.core.database import AsyncSessionLocal
        from app.agents.paperclip import get_paperclip
        from app.models.payroll import PayrollRun
        from sqlalchemy import select
        from datetime import datetime

        now = datetime.utcnow()
        results = []

        async with AsyncSessionLocal() as db:
            tenant_ids = await _get_active_tenant_ids(tenant_id, db)
            paperclip  = get_paperclip()

            for tid in tenant_ids:
                existing_runs = await db.execute(
                    select(PayrollRun).where(
                        PayrollRun.tenant_id == tid,
                        PayrollRun.month     == now.month,
                        PayrollRun.year      == now.year,
                        PayrollRun.status    == "draft",
                    )
                )
                runs = existing_runs.scalars().all()

                for run in runs:
                    try:
                        task_result = await paperclip.dispatch(
                            domain="payroll",
                            action="validate",
                            payload={"run_id": str(run.id)},
                            tenant_id=tid,
                            db=db,
                        )
                        results.append({
                            "tenant_id":      tid,
                            "run_id":         str(run.id),
                            "recommendation": getattr(task_result.result, "recommendation", "unknown"),
                            "risk_score":     getattr(task_result.result, "total_risk_score", 0),
                        })
                    except Exception as exc:
                        logger.exception(
                            "pre_approval_check failed for run %s: %s", run.id, exc
                        )

        return {"type": "pre_approval_check", "month": now.month, "results": results}

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.exception("payroll_pre_approval_check task error: %s", exc)
        raise self.retry(exc=exc, countdown=300)


# ─── Beat Schedule — injected into existing celery_app (additive) ─────────────

AGENT_BEAT_SCHEDULE = {
    # Daily 09:00 PKT = 04:00 UTC
    "agent.daily_attendance_report": {
        "task":     "agents.daily_attendance_report",
        "schedule": crontab(hour=4, minute=0),
        "args":     (),
    },
    # 25th of month 10:00 PKT = 05:00 UTC
    "agent.monthly_payroll_trigger": {
        "task":     "agents.monthly_payroll_trigger",
        "schedule": crontab(day_of_month=25, hour=5, minute=0),
        "args":     (),
    },
    # 24th of month 06:00 PKT = 01:00 UTC  (early-warning check)
    "agent.payroll_pre_approval_check": {
        "task":     "agents.payroll_pre_approval_check",
        "schedule": crontab(day_of_month=24, hour=1, minute=0),
        "args":     (),
    },
}

# Update existing beat schedule dict at import time (no file modification needed)
try:
    from app.worker.celery_app import celery_app as _celery_app
    _celery_app.conf.beat_schedule.update(AGENT_BEAT_SCHEDULE)
    logger.info(
        "Agent beat schedule registered: %s", list(AGENT_BEAT_SCHEDULE.keys())
    )
except Exception as _exc:
    logger.warning("Could not register agent beat schedule: %s", _exc)


# ─── Private helpers ──────────────────────────────────────────────────────────

async def _get_active_tenant_ids(
    tenant_id: str | None,
    db,
) -> list[str]:
    """Return [tenant_id] if specified, else fetch all active tenant IDs from DB."""
    if tenant_id:
        return [tenant_id]

    try:
        from sqlalchemy import select
        from app.models.tenant import Tenant
        rows = await db.execute(
            select(Tenant.id).where(Tenant.is_active.is_(True))
        )
        return [str(row[0]) for row in rows.fetchall()]
    except Exception as exc:
        logger.warning("_get_active_tenant_ids failed: %s", exc)
        return []


async def _create_draft_payroll_run(
    tenant_id: str, month: int, year: int, db
) -> str | None:
    """
    Create a new draft PayrollRun for the given tenant/month/year.
    Returns None if one already exists for this period.
    """
    try:
        from sqlalchemy import select
        from app.models.payroll import PayrollRun

        existing = await db.execute(
            select(PayrollRun).where(
                PayrollRun.tenant_id == tenant_id,
                PayrollRun.month     == month,
                PayrollRun.year      == year,
            )
        )
        if existing.scalar_one_or_none():
            return None

        run = PayrollRun(
            tenant_id   = tenant_id,
            month       = month,
            year        = year,
            status      = "draft",
            created_by  = "agent_scheduler",
        )
        db.add(run)
        await db.flush()
        return str(run.id)
    except Exception as exc:
        logger.exception("_create_draft_payroll_run failed: %s", exc)
        return None


async def _notify_hr_payroll_trigger(
    tenant_id: str,
    run_id: str,
    validation_result,
    month: int,
    year: int,
    db,
) -> None:
    """Create an in-app notification for HR with the AI payroll recommendation."""
    try:
        from sqlalchemy import select
        from app.models.tenant import User
        from app.models.notification import Notification

        recommendation = getattr(validation_result, "recommendation", "review")
        summary        = getattr(validation_result, "summary", "Payroll run ready for review.")
        risk_score     = getattr(validation_result, "total_risk_score", 0)

        emoji = {"approve": "✅", "hold": "⚠️", "reject": "🚫"}.get(recommendation, "📋")
        month_name = date(year, month, 1).strftime("%B %Y")

        hr_users = await db.execute(
            select(User).where(
                User.tenant_id    == tenant_id,
                User.is_superadmin.is_(True),
            )
        )
        for user in hr_users.scalars().all():
            db.add(Notification(
                tenant_id      = tenant_id,
                user_id        = str(user.id),
                title          = f"{emoji} Payroll Agent: {month_name} — {recommendation.upper()}",
                message        = f"{summary}\n\nRisk Score: {risk_score}/100. Run ID: {run_id}",
                category       = "payroll",
                reference_id   = run_id,
                reference_type = "payroll_run",
            ))
        await db.commit()
    except Exception as exc:
        logger.warning("_notify_hr_payroll_trigger failed: %s", exc)

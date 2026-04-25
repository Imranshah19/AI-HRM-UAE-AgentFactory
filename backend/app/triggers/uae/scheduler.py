"""
UAE Celery Beat Schedules.

All times in UTC (UAE = UTC+4):
  04:00 UTC = 08:00 AM UAE
  05:00 UTC = 09:00 AM UAE
  06:00 UTC = 10:00 AM UAE

Inject into existing celery app — does NOT modify existing schedules.
Call inject_schedules() from celery_app.py or your setup.
"""

from __future__ import annotations

from celery.schedules import crontab

BEAT_SCHEDULES: dict = {
    # ── Daily schedules ──────────────────────────────────────────────────────

    # 08:00 AM UAE (04:00 UTC) — Document expiry check (all companies)
    "uae-document-expiry-check": {
        "task": "app.tasks.uae.document_tasks.check_all_document_expiries",
        "schedule": crontab(hour=4, minute=0),
        "kwargs": {},
        "options": {"queue": "uae_compliance"},
    },

    # 09:00 AM UAE (05:00 UTC) — Daily attendance report
    "uae-attendance-daily-report": {
        "task": "app.tasks.uae.attendance_tasks.generate_daily_attendance_report",
        "schedule": crontab(hour=5, minute=0),
        "kwargs": {},
        "options": {"queue": "uae_attendance"},
    },

    # 04:30 UTC — Insurance expiry check
    "uae-insurance-expiry-check": {
        "task": "app.tasks.uae.insurance_tasks.check_insurance_expiries",
        "schedule": crontab(hour=4, minute=30),
        "kwargs": {},
        "options": {"queue": "uae_compliance"},
    },

    # 05:00 UTC daily — WPS deadline alerts
    "uae-wps-deadline-alerts": {
        "task": "app.tasks.uae.wps_tasks.send_wps_deadline_alerts",
        "schedule": crontab(hour=5, minute=30),
        "kwargs": {},
        "options": {"queue": "uae_payroll"},
    },

    # ── Monthly schedules ─────────────────────────────────────────────────────

    # 25th of each month, 10:00 AM UAE (06:00 UTC) — Payroll generation
    "uae-payroll-generation": {
        "task": "app.tasks.uae.payroll_tasks.generate_payroll_all_companies",
        "schedule": crontab(hour=6, minute=0, day_of_month=25),
        "kwargs": {},
        "options": {"queue": "uae_payroll"},
    },

    # 24th of each month, 06:00 AM UAE (02:00 UTC) — Pre-payroll validation
    "uae-payroll-pre-validation": {
        "task": "app.tasks.uae.payroll_tasks.validate_payroll_all_companies",
        "schedule": crontab(hour=2, minute=0, day_of_month=24),
        "kwargs": {},
        "options": {"queue": "uae_payroll"},
    },

    # 1st of each month — Emiratisation compliance check
    "uae-emiratisation-monthly-check": {
        "task": "app.tasks.uae.emiratisation_tasks.run_monthly_emiratisation_check",
        "schedule": crontab(hour=5, minute=0, day_of_month=1),
        "kwargs": {},
        "options": {"queue": "uae_compliance"},
    },

    # 1st of each month — Gratuity accrual update
    "uae-gratuity-monthly-accrual": {
        "task": "app.tasks.uae.gratuity_tasks.update_monthly_accrual_all",
        "schedule": crontab(hour=5, minute=30, day_of_month=1),
        "kwargs": {},
        "options": {"queue": "uae_payroll"},
    },

    # ── Weekly schedules ──────────────────────────────────────────────────────

    # Every Sunday 09:00 AM UAE (05:00 UTC) — Contract expiry report
    "uae-contract-expiry-weekly": {
        "task": "app.tasks.uae.contract_tasks.send_weekly_contract_expiry_report",
        "schedule": crontab(hour=5, minute=0, day_of_week=0),  # 0=Sunday
        "kwargs": {},
        "options": {"queue": "uae_compliance"},
    },

    # Every Sunday — Air ticket utilization review
    "uae-air-ticket-weekly-review": {
        "task": "app.tasks.uae.air_ticket_tasks.weekly_utilization_review",
        "schedule": crontab(hour=5, minute=30, day_of_week=0),
        "kwargs": {},
        "options": {"queue": "uae_hr"},
    },

    # ── Ramadan detection ─────────────────────────────────────────────────────

    # Daily check: are we in Ramadan? If so activate 6-hour mode
    "uae-ramadan-mode-check": {
        "task": "app.tasks.uae.attendance_tasks.check_and_set_ramadan_mode",
        "schedule": crontab(hour=3, minute=0),  # 07:00 UAE
        "kwargs": {},
        "options": {"queue": "uae_attendance"},
    },
}


def inject_schedules(celery_app) -> None:
    """
    Inject UAE-specific Celery beat schedules into an existing Celery app.
    Call this from your celery app setup — does NOT overwrite existing schedules.
    """
    existing = getattr(celery_app.conf, "beat_schedule", {}) or {}
    merged = {**existing, **BEAT_SCHEDULES}
    celery_app.conf.beat_schedule = merged

    import structlog
    logger = structlog.get_logger(__name__)
    logger.info(
        "uae_scheduler.injected",
        new_tasks=len(BEAT_SCHEDULES),
        total_tasks=len(merged),
    )

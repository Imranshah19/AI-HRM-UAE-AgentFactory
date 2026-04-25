"""
AI-HRMS — Central Celery Application

All task modules are auto-discovered from app.tasks.*.
Run the worker with:
    celery -A app.worker.celery_app worker --loglevel=info -Q default,payroll,notifications,reports
"""

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "ai_hrms",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.employee_tasks",
        "app.tasks.attendance_tasks",
        "app.tasks.leave_tasks",
        "app.tasks.payroll_tasks",
        "app.tasks.recruitment_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_routes={
        "app.tasks.employee_tasks.*":   {"queue": "default"},
        "app.tasks.attendance_tasks.*": {"queue": "default"},
        "app.tasks.leave_tasks.*":      {"queue": "notifications"},
        "app.tasks.payroll_tasks.*":    {"queue": "payroll"},
        "app.tasks.recruitment_tasks.*": {"queue": "notifications"},
    },
    # Beat schedule (periodic tasks)
    beat_schedule={},
)

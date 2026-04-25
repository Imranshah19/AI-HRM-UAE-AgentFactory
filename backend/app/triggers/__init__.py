"""
Agent Factory — Trigger layer for AI-HRMS.

Triggers are the entry points that activate agents:
  - webhook.py     : HTTP webhooks (leave application events, external systems)
  - scheduler.py   : Celery beat periodic tasks (payroll 25th, attendance 9am)
  - api_trigger.py : Manual trigger REST endpoints (/agent/triggers/*)

All triggers route through Paperclip (orchestrator) to the specialist agents.
No existing files are modified.

HOW TO ACTIVATE SCHEDULED TRIGGERS
-----------------------------------
Add  app.triggers.scheduler  to Celery's include list at startup, OR run:

    celery -A app.worker.celery_app worker \\
        --include app.triggers.scheduler \\
        --loglevel=info -Q default,agents

    celery -A app.worker.celery_app beat --loglevel=info
"""

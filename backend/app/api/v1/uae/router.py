"""
UAE AI-HRM Master Router.

All routes under prefix: /api/v1/uae/
Registered in the main v1 router with 2 lines (non-destructive).

Sub-routers:
  companies   — Group + company management
  employees   — UAE employee profiles
  payroll     — AED payroll + WPS SIF
  compliance  — WPS, Emiratisation, documents, contracts
  leave       — 9 UAE leave types
  attendance  — UAE working hours + Ramadan
  agent       — All 15 agents status, logs, triggers
  webhooks    — Event-driven triggers (imported from triggers/uae)
"""

from fastapi import APIRouter

from app.api.v1.uae.companies_router import router as companies_router
from app.api.v1.uae.employees_router import router as employees_router
from app.api.v1.uae.payroll_router import router as payroll_router
from app.api.v1.uae.compliance_router import router as compliance_router
from app.api.v1.uae.leave_router import router as leave_router
from app.api.v1.uae.attendance_router import router as attendance_router
from app.triggers.uae.api_trigger import router as agent_trigger_router
from app.triggers.uae.webhook import router as webhook_router

uae_router = APIRouter(prefix="/uae", tags=["UAE AI-HRM"])

uae_router.include_router(companies_router)
uae_router.include_router(employees_router)
uae_router.include_router(payroll_router)
uae_router.include_router(compliance_router)
uae_router.include_router(leave_router)
uae_router.include_router(attendance_router)
uae_router.include_router(agent_trigger_router)
uae_router.include_router(webhook_router)

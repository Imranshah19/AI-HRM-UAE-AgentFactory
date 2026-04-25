"""
AI-HRMS — API v1 master router.

All domain routers are registered here and included into main.py
under the /api/v1 prefix.

Adding a new module:
  1. Create backend/app/api/v1/<module>/router.py
  2. Import its router below
  3. Include it via v1_router.include_router(...)
"""

from fastapi import APIRouter

from app.api.v1.auth.router         import router as auth_router
from app.api.v1.employees.router    import router as employees_router
from app.api.v1.departments.router  import router as departments_router
from app.api.v1.designations.router import router as designations_router
from app.api.v1.leave.router        import router as leave_router
from app.api.v1.attendance.router   import router as attendance_router
from app.api.v1.payroll.router      import router as payroll_router
from app.api.v1.recruitment.router  import router as recruitment_router, public_router as recruitment_public_router
from app.api.v1.performance.router    import router as performance_router
from app.api.v1.training.router       import router as training_router
from app.api.v1.assets.router         import router as assets_router
from app.api.v1.notifications.router  import router as notifications_router
from app.api.v1.reports.router        import router as reports_router
from app.api.v1.ai.attrition_router   import router as ai_attrition_router
from app.api.v1.ai.performance_router import router as ai_performance_router
from app.api.v1.ai.chatbot_router     import router as ai_chatbot_router
from app.api.v1.ai.analytics_router   import router as ai_analytics_router

# ─── Master v1 Router ─────────────────────────────────────────────────────────

v1_router = APIRouter(prefix="/api/v1")

# ── Auth ──────────────────────────────────────────────────────────────────────
v1_router.include_router(auth_router)

# ── Employee Management ───────────────────────────────────────────────────────
v1_router.include_router(employees_router)
v1_router.include_router(departments_router)
v1_router.include_router(designations_router)

# ── Leave Management ──────────────────────────────────────────────────────────
v1_router.include_router(leave_router)

# ── Attendance & Time Tracking ────────────────────────────────────────────────
v1_router.include_router(attendance_router)

# ── Payroll ───────────────────────────────────────────────────────────────────
v1_router.include_router(payroll_router)

# ── Recruitment / ATS ─────────────────────────────────────────────────────────
v1_router.include_router(recruitment_router)
v1_router.include_router(recruitment_public_router)

# ── Performance Management ────────────────────────────────────────────────────
v1_router.include_router(performance_router)

# ── Training Management ───────────────────────────────────────────────────────
v1_router.include_router(training_router)

# ── Asset Management ─────────────────────────────────────────────────────────
v1_router.include_router(assets_router)

# ── Notifications ─────────────────────────────────────────────────────────────
v1_router.include_router(notifications_router)

# ── Reports & Analytics ───────────────────────────────────────────────────────
v1_router.include_router(reports_router)

# ── AI Features ───────────────────────────────────────────────────────────────
v1_router.include_router(ai_attrition_router)
v1_router.include_router(ai_performance_router)
v1_router.include_router(ai_chatbot_router)
v1_router.include_router(ai_analytics_router)

# ── Agent Factory (/agent/*) ───────────────────────────────────────────────────
from app.api.v1.agents.router import agent_router  # noqa: E402
v1_router.include_router(agent_router)

# ── UAE AI-HRM Agent Factory (/uae/*) — new layer, zero existing code changed ──
from app.api.v1.uae.router import uae_router  # noqa: E402
v1_router.include_router(uae_router)

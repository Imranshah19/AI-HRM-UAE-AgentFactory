"""
UAE AI-HRM Agent Factory — 13 specialist LangGraph agents for UAE Labour Law compliance.

Framework: LangGraph StateGraph + Anthropic SDK (claude-opus-4-7, adaptive thinking).
Entry point: graph.run_uae_task(task_type, company_id, payload, employee_id)
Mock mode: graceful fallback when ANTHROPIC_API_KEY not set.

Agents (all in /backend/app/agents/uae/):
  1.  graph          — LangGraph master orchestrator + Claude API helpers
  2.  leave          — 9 UAE leave types (Federal Decree-Law No. 33/2021)
  3.  payroll        — AED payroll: ILOE, overtime, Ramadan hours, WPS
  4.  attendance     — Working hours tracking + Ramadan mode (6hr/day)
  5.  onboarding     — New employee onboarding: Emirates ID, visa, WPS
  6.  document       — Document expiry tracking + tiered alerts
  7.  gratuity       — End-of-service gratuity (21/30 days per year)
  8.  wps            — WPS SIF XML generator + MOHRE validation
  9.  contract       — Contract expiry + notice period enforcement
  10. insurance      — Medical insurance + ILOE compliance (DHA/HAAD)
  11. air_ticket     — Annual home-country air ticket entitlement
  12. emiratisation  — Emiratisation/Nafis quota compliance + fine risk
  13. offboarding    — Employee exit + 14-day final settlement law
  14. chatbot        — Multilingual HR chatbot (EN/AR/UR/HI/TL)

Folder structure:
  /agents/uae/   — UAE LangGraph agent modules
  /triggers/uae/ — Celery schedules, webhooks, API triggers
  /api/v1/uae/   — FastAPI routes (/api/v1/uae/*)
"""

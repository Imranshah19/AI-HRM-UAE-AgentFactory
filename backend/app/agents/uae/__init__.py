"""
UAE AI-HRM Agent Factory — 15 specialist agents for UAE Labour Law compliance.

Agents (all in /backend/app/agents/uae/):
  1.  openclaw        — Main Claude AI brain (UAE Labour Law aware)
  2.  paperclip       — Orchestrator + routing (priority queue, retry logic)
  3.  onboarding      — New employee onboarding (visa, WPS, bilingual docs)
  4.  document        — Document expiry tracking + tiered alerts
  5.  payroll         — AED payroll (ILOE, overtime, Ramadan hours)
  6.  wps             — WPS SIF file generator + MOHRE validation
  7.  gratuity        — Gratuity calculation (Federal Decree-Law 33/2021)
  8.  leave           — 9 UAE leave types (annual, sick, maternity, etc.)
  9.  attendance      — Working hours tracking + Ramadan mode
  10. contract        — Contract expiry + notice period enforcement
  11. insurance       — Medical insurance + ILOE compliance
  12. air_ticket      — Annual air ticket entitlement management
  13. emiratisation   — Emiratisation quota compliance + fine risk
  14. offboarding     — Employee exit + 14-day final settlement law
  15. chatbot         — Multilingual HR chatbot (EN/AR/UR/HI/TL)

Folder structure preserved:
  /agents/uae/   — UAE agent modules
  /triggers/uae/ — Celery schedules, webhooks, API triggers
  /api/v1/uae/   — FastAPI routes (/api/v1/uae/*)
"""

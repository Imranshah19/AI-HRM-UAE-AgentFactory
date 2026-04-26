# UAE AI-HRM Agent Factory

**Enterprise-grade AI-powered HR management system for UAE group of companies.**  
Built on LangGraph + Claude Opus 4.7 with full UAE Labour Law compliance (Federal Decree-Law No. 33/2021).

[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-1.1.9-orange)](https://github.com/langchain-ai/langgraph)
[![Claude](https://img.shields.io/badge/Claude-Opus%204.7-purple)](https://anthropic.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## Overview

The UAE AI-HRM Agent Factory is a multi-tenant HR automation platform built for UAE Group of Companies. It replaces manual HR processes with 13 intelligent LangGraph agents, each a specialist in a specific HR domain under UAE law.

**Key capabilities:**
- Multi-company group management (Dubai, Abu Dhabi, Sharjah, Free Zones)
- Full WPS (Wage Protection System) SIF file generation and submission tracking
- Emiratisation quota monitoring with NAFIS integration (AED 96,000/slot fine risk)
- Automatic document expiry alerts (Emirates ID, Visa, Labour Card, Passport)
- Ramadan mode — 6-hour working day detection and payroll adjustment
- Multilingual HR chatbot: English, Arabic, Urdu, Hindi, Tagalog
- Mock mode — all 13 agents work without `ANTHROPIC_API_KEY`; set key for live Claude AI

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│              /api/v1/uae/* (8 sub-routers)              │
└─────────────────────┬───────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────┐
│          LangGraph Master Orchestrator (graph.py)        │
│     run_uae_task(task_type, company_id, payload)         │
│     14 task types → 13 specialist sub-graphs             │
└──┬──────┬──────┬──────┬──────┬──────┬──────┬───────────┘
   │      │      │      │      │      │      │
 leave payroll attend onboard document gratuity  ...
   │      │      │      │      │      │      │
┌──▼──────▼──────▼──────▼──────▼──────▼──────▼──────────┐
│          Anthropic SDK — claude-opus-4-7                 │
│          thinking: {type: "adaptive"}                    │
│          Mock fallback when no API key                   │
└────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|-----------|
| AI Orchestration | LangGraph 1.1.9 StateGraph |
| AI Model | Claude Opus 4.7 (adaptive thinking) |
| AI SDK | Anthropic Python SDK >= 0.40.0 |
| Backend | FastAPI 0.115 + Python 3.11 |
| Database | PostgreSQL 15 (asyncpg + SQLAlchemy 2.0) |
| Migrations | Alembic (auto-run on container start) |
| Cache / Queue | Redis 7 + Celery 5.4 |
| Frontend | Next.js 14 (App Router, TypeScript) |
| UI | Tailwind CSS + shadcn/ui |
| Containerisation | Docker + Docker Compose |
| Logging | structlog + Redis log ring (1,000 entries) |

---

## 13 UAE AI Agents

Each agent is an independent LangGraph `StateGraph` with typed state, conditional edges, and a `run_agent()` async interface. Claude is invoked only at decision nodes when `ANTHROPIC_API_KEY` is set.

| # | Agent | Task Types | UAE Law / Domain |
|---|-------|-----------|-----------------|
| 1 | **Leave** | `leave_apply`, `leave_balance` | Federal Decree-Law 33/2021 — 9 leave types |
| 2 | **Payroll** | `payroll` | ILOE deduction, overtime 125%/150%, Ramadan hours |
| 3 | **Attendance** | `attendance` | 8hr/day standard, 6hr Ramadan, GPS/QR/WiFi/IP verify |
| 4 | **Onboarding** | `onboarding` | Emirates ID, Labour card, WPS registration, ILOE enroll |
| 5 | **Document** | `document_check` | Visa/Passport/EID expiry — CRITICAL/URGENT/WARNING tiers |
| 6 | **Gratuity** | `gratuity` | 21 days/yr (<=5yr), 30 days/yr (>5yr), 2yr salary cap |
| 7 | **WPS** | `wps` | MOHRE SIF XML generator, IBAN validation, deadline alerts |
| 8 | **Contract** | `contract` | Limited contract expiry, notice period, renewal alerts |
| 9 | **Insurance** | `insurance` | DHA/HAAD medical + ILOE compliance tracker |
| 10 | **Air Ticket** | `air_ticket` | Annual home-country ticket after 1yr service |
| 11 | **Emiratisation** | `emiratisation` | 2% Nafis quota, AED 96,000/slot fine risk calculation |
| 12 | **Offboarding** | `offboarding` | 14-day settlement law, gratuity + WPS final pay |
| 13 | **HR Chatbot** | `chat` | EN / AR / UR / HI / TL — 5 language support |

### Agent Call Pattern

```python
from app.agents.uae.graph import run_uae_task

result = await run_uae_task(
    task_type="leave_apply",
    company_id="co-001",
    employee_id="emp-001",
    payload={
        "leave_type": "annual",
        "start_date": "2026-05-01",
        "end_date": "2026-05-10",
    },
)
# result = {"decision": "approve", "balance_remaining": 20, "api_mode": "live", ...}
```

---

## UAE Labour Law Compliance

| Regulation | Implementation |
|-----------|---------------|
| Federal Decree-Law No. 33/2021 | Leave entitlements, contract types, gratuity formula |
| MOHRE WPS | SIF XML generation, IBAN validation (AE format), deadline tracking |
| ILOE (Oct 2023) | AED 5/month (basic < 16,000) or AED 10/month (>= 16,000) |
| Emiratisation | 2% annual quota, AED 96,000 fine per unfilled slot |
| Ramadan | Automatic 6-hr/day detection (2025-2027 periods built-in) |
| Gratuity cap | Maximum 24 months' basic salary |
| Offboarding | 14-day final settlement law |
| Overtime | Max 2 hrs/day — 125% normal, 150% night/Friday/holiday |
| Leave types | Annual (30d), Sick (90d), Maternity (60d), Paternity (5d), Bereavement, Hajj, Study, Parental, Unpaid |

---

## Database Schema (10 UAE Tables)

All tables are additive — zero modifications to existing base HRM tables.

```
companies                  — Multi-company group structure
employees_uae_profile      — UAE-specific data (extends existing employees)
salary_structure_uae       — AED salary breakdown (basic + allowances)
payroll_uae                — Monthly payroll records with WPS flag
wps_submissions            — SIF file submission tracking + MOHRE confirmations
gratuity_ledger            — Accrual entries + final settlement records
leave_balances_uae         — 9 leave types per employee per year
documents_tracker          — Expiry tracking + tiered alert flags
emiratisation_records      — Monthly quota compliance snapshots
agent_logs_uae             — LangGraph agent execution audit log
```

Applied via Alembic — runs automatically on container start:

```bash
alembic upgrade head && uvicorn app.main:app ...
```

---

## API Routes

All UAE routes are under `/api/v1/uae/` — registered non-destructively in the master router.

```
GET    /api/v1/uae/agent/status                    Agent health + mode (live/mock)
GET    /api/v1/uae/agent/logs?limit=50             Redis execution logs
POST   /api/v1/uae/agent/chat                      Multilingual HR chatbot

POST   /api/v1/uae/agent/trigger/payroll/{company_id}
POST   /api/v1/uae/agent/trigger/wps-validate/{company_id}
POST   /api/v1/uae/agent/trigger/wps-sif/{company_id}
POST   /api/v1/uae/agent/trigger/documents-check
POST   /api/v1/uae/agent/trigger/attendance-report
POST   /api/v1/uae/agent/trigger/emiratisation-check
POST   /api/v1/uae/agent/trigger/gratuity
POST   /api/v1/uae/agent/trigger/leave-balance
POST   /api/v1/uae/agent/trigger/insurance-check/{company_id}
POST   /api/v1/uae/agent/trigger/contract-check/{company_id}

POST   /api/v1/uae/webhooks/employee/joined
POST   /api/v1/uae/webhooks/employee/resigned
POST   /api/v1/uae/webhooks/employee/terminated
POST   /api/v1/uae/webhooks/leave/applied
POST   /api/v1/uae/webhooks/attendance/checkin
POST   /api/v1/uae/webhooks/attendance/checkout
POST   /api/v1/uae/webhooks/document/uploaded
POST   /api/v1/uae/webhooks/contract/expiring
```

Interactive docs: `http://localhost:8000/docs`

---

## Frontend — 6 UAE Dashboard Pages

All pages support **Arabic RTL toggle** (`EN | عربي`), AED currency, and Green/Yellow/Red status colours.

| Route | Page | Features |
|-------|------|---------|
| `/uae/group-dashboard` | Group Overview | All companies, WPS status, Emiratisation %, critical alerts |
| `/uae/company/[id]/dashboard` | Company Dashboard | Per-company metrics, payroll summary, document alerts |
| `/uae/employees/[id]/profile` | Employee Profile | UAE docs, visa/EID expiry, leave balances, gratuity |
| `/uae/payroll` | Payroll | AED payslips, ILOE deduction, WPS readiness, Ramadan mode |
| `/uae/compliance` | Compliance | WPS, Emiratisation, documents, contracts — all in one view |
| `/uae/agent-dashboard` | Agent Control | 13 LangGraph agents status, execution logs, manual triggers |

---

## Quick Start

### Prerequisites

- Docker Desktop 4.x
- Docker Compose v2

### 1. Clone

```bash
git clone https://github.com/Imranshah19/AI-HRM-UAE-AgentFactory.git
cd AI-HRM-UAE-AgentFactory
```

### 2. Environment

```bash
cp .env.example backend/.env
```

Edit `backend/.env`:

```env
ANTHROPIC_API_KEY=sk-ant-...        # leave blank for mock mode
JWT_SECRET_KEY=<openssl rand -hex 64>
```

`ANTHROPIC_API_KEY` is optional — all 13 agents work in mock mode without it.

### 3. Start

```bash
docker-compose up -d
```

This starts: PostgreSQL → Redis → Backend (runs `alembic upgrade head` then uvicorn) → Celery Worker → Celery Beat → Next.js Frontend.

### 4. Open

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| UAE Routes | http://localhost:8000/docs#/UAE%20AI-HRM |

Default login: `admin@hrms.local` / `Admin@1234!`

---

## Project Structure

```
AI-HRM-UAE-AgentFactory/
├── backend/
│   ├── app/
│   │   ├── agents/uae/              # 13 LangGraph agents
│   │   │   ├── graph.py             # Master orchestrator + Claude helpers
│   │   │   ├── leave.py
│   │   │   ├── payroll.py
│   │   │   ├── attendance.py
│   │   │   ├── onboarding.py
│   │   │   ├── document.py
│   │   │   ├── gratuity.py
│   │   │   ├── wps.py
│   │   │   ├── contract.py
│   │   │   ├── insurance.py
│   │   │   ├── air_ticket.py
│   │   │   ├── emiratisation.py
│   │   │   ├── offboarding.py
│   │   │   └── chatbot.py
│   │   ├── api/v1/uae/              # FastAPI routers
│   │   │   ├── router.py
│   │   │   ├── companies_router.py
│   │   │   ├── employees_router.py
│   │   │   ├── payroll_router.py
│   │   │   ├── compliance_router.py
│   │   │   ├── leave_router.py
│   │   │   └── attendance_router.py
│   │   ├── triggers/uae/            # Celery + webhook triggers
│   │   │   ├── api_trigger.py
│   │   │   ├── webhook.py
│   │   │   └── scheduler.py
│   │   └── models/                  # SQLAlchemy ORM models
│   ├── alembic/versions/            # DB migrations
│   └── requirements.txt
├── frontend/src/app/(dashboard)/uae/
│   ├── group-dashboard/page.tsx
│   ├── company/[id]/dashboard/page.tsx
│   ├── employees/[id]/profile/page.tsx
│   ├── payroll/page.tsx
│   ├── compliance/page.tsx
│   └── agent-dashboard/page.tsx
├── docker-compose.yml
└── .env.example
```

---

## Environment Variables

Key variables (full list in `.env.example`):

```env
# Claude AI — leave blank for mock mode
ANTHROPIC_API_KEY=

# Database
DATABASE_URL=postgresql+asyncpg://hrms_user:hrms_password@postgres:5432/hrms_db

# Redis / Celery
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# UAE Compliance Thresholds
UAE_DOCUMENT_ALERT_CRITICAL_DAYS=7
UAE_DOCUMENT_ALERT_URGENT_DAYS=30
UAE_EMIRATISATION_ANNUAL_FINE_AED=96000
UAE_GRATUITY_CAP_MONTHS=24
```

---

## Celery Scheduled Jobs

| Schedule | Job | Queue |
|----------|-----|-------|
| Daily 08:00 UAE | Document expiry check | uae_compliance |
| Daily 09:00 UAE | Attendance daily report | uae_attendance |
| Daily 08:30 UAE | Insurance expiry check | uae_compliance |
| Daily 09:30 UAE | WPS deadline alerts | uae_payroll |
| 25th monthly | Payroll generation | uae_payroll |
| 24th monthly | Pre-payroll validation | uae_payroll |
| 1st monthly | Emiratisation check | uae_compliance |
| 1st monthly | Gratuity accrual update | uae_payroll |
| Every Sunday | Contract expiry report | uae_compliance |
| Every Sunday | Air ticket utilisation | uae_hr |
| Daily 07:00 UAE | Ramadan mode detection | uae_attendance |

---

## Development

```bash
# Install backend dependencies locally
cd backend
pip install -r requirements.txt

# Install LangGraph (required for local StateGraph execution)
pip install "langgraph>=0.2.0" "anthropic>=0.40.0"

# Run backend locally (requires PostgreSQL + Redis running)
uvicorn app.main:app --reload

# Run frontend locally
cd frontend
npm install
npm run dev

# Run tests (requires Docker DB)
cd backend
pytest tests/ -v
```

---

## License

MIT

---

*Built with LangGraph + Claude Opus 4.7 — UAE Federal Decree-Law No. 33/2021 compliant*

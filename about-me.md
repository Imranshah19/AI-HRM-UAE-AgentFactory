# About Me — Syed Imran Shah

## Who I Am

HR professional turned AI developer. 10+ years in human resources (MPA in HRM, University of Karachi), Gulf experience in Saudi Arabia, business owner of AlSyed Autoparts in Karachi.

I build AI-powered HR systems — not prototypes, actual production systems with real databases, real queues, real compliance rules baked in. I know both sides: what HR managers actually need, and how to build it with code.

Currently pursuing GIAIC AI & Computing certification. Freelancing on Fiverr (syedio). Based in Karachi, available worldwide remote.

**Contact:** Syed.Is1990@gmail.com · WhatsApp: +92 333 2455770 · GitHub: Imranshah19

---

## This Project — UAE AI-HRM Agent Factory V2.0

**What it is:** Enterprise HR automation system for UAE Group of Companies. Built for real multi-company UAE operations — not a demo.

**Why it exists:** UAE Labour Law (Federal Decree-Law No. 33/2021) has strict, specific rules — WPS deadlines, Emiratisation quotas, ILOE deductions, Ramadan hour adjustments, 14-day settlement law. Manual HR can't keep up across multiple companies. This system automates all of it.

**Repository:** github.com/Imranshah19/AI-HRM-UAE-AgentFactory

---

## Technical Stack — Exact Versions

### Backend (Python)
```
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy[asyncio]==2.0.35
alembic==1.13.3
asyncpg==0.29.0
psycopg2-binary==2.9.9
pydantic==2.9.2
pydantic-settings==2.5.2
celery==5.4.0
redis==5.1.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
structlog==24.4.0
sentry-sdk[fastapi]==2.14.0
boto3==1.35.20
httpx==0.27.2
sendgrid==6.11.0
twilio==9.3.2
slowapi==0.1.9
orjson==3.10.7
```

### AI / LangGraph Stack
```
anthropic>=0.40.0        (installed: 0.84.0)
langgraph>=0.2.0         (installed: 1.1.9)
langchain-anthropic>=0.3.0
langsmith>=0.1.0
langchain==0.3.1
langchain-openai==0.2.1
openai==1.47.0
scikit-learn==1.5.2
xgboost==2.1.1
shap==0.46.0
```

### Frontend (Node/TypeScript)
```
next: ^14.2.35
react: ^18.3.1
typescript: ^5.6.2
tailwindcss: ^3.4.12
zustand: ^4.5.5
@tanstack/react-query: 5.56.2
axios: ^1.7.7
react-hook-form: ^7.53.0
zod: ^3.23.8
recharts: ^2.12.7
lucide-react: ^0.447.0
@radix-ui/* (full shadcn/ui component set)
date-fns: ^3.6.0
node: >=20.0.0
```

### Infrastructure
```
PostgreSQL 15 (Docker: postgres:15-alpine)
Redis 7       (Docker: redis:7-alpine)
Docker Compose v2
Celery 5.4 workers + beat scheduler
Alembic migrations (auto-run on container start)
```

---

## Architecture

### Request Flow
```
HTTP Request
    → FastAPI (/api/v1/uae/*)
    → LangGraph Master Orchestrator (graph.py)
    → run_uae_task(task_type, company_id, payload)
    → Specialist Agent StateGraph (e.g. leave.py)
    → Claude Opus 4.7 at decision nodes (if ANTHROPIC_API_KEY set)
    → Return structured dict
```

### AI Decision Pattern
Every agent works in two modes:
- **Mock mode** (no API key): deterministic logic, instant response
- **Live mode** (API key set): Claude Opus 4.7 with `thinking: {type: "adaptive"}` for complex decisions

```python
# Pattern used in every agent
if is_live_mode() and flags_present:
    response = claude_invoke(system=UAE_EXPERT_PROMPT, user_message=context)
else:
    response = rule_based_fallback()
```

### LangGraph Agent Structure
Each agent is a `StateGraph` with:
- Typed `TypedDict` state
- Sequential nodes (each does one thing)
- Conditional edges where decisions branch
- Single async `run_agent(company_id, employee_id, payload, api_mode)` entry point

---

## 13 UAE LangGraph Agents

| Agent file | Nodes | Claude node | Task types |
|-----------|-------|-------------|-----------|
| `graph.py` | validate → route → run → log | — | all (orchestrator) |
| `leave.py` | check_balance → check_overlap → check_holidays → check_ramadan → make_decision → update_balance → notify | make_decision | leave_apply, leave_balance |
| `payroll.py` | fetch_employees → calculate_earnings → calculate_overtime → apply_iloe → validate_totals → generate_outputs | validate_totals | payroll |
| `attendance.py` | receive_event → verify_location → check_hours → detect_ramadan → flag_anomalies → update_record → generate_report | generate_report | attendance |
| `onboarding.py` | validate_data → create_profile → generate_checklist → setup_salary → register_wps → notify_it → notify_pro → send_welcome → log_done | log_done | onboarding |
| `document.py` | fetch_docs → calculate_expiry → categorize_urgency → send_alerts → generate_report | generate_report | document_check |
| `gratuity.py` | fetch_service → determine_scenario → calculate_gratuity → calculate_settlement → generate_report | generate_report | gratuity |
| `wps.py` | fetch_payroll → validate_banks → check_coverage → generate_sif → validate_sif → check_deadline → send_alerts | send_alerts | wps |
| `contract.py` | fetch_contracts → calculate_timelines → send_renewal_alerts → generate_report | generate_report | contract |
| `insurance.py` | fetch_insurance → check_expiry → check_iloe → send_alerts → generate_report | generate_report | insurance |
| `air_ticket.py` | fetch_entitlement → check_eligibility → process_request → calculate_value → send_approval → track_return → generate_report → log_done | generate_report | air_ticket |
| `emiratisation.py` | fetch_headcount → calculate_pct → calculate_fine → send_alert → identify_nafis → generate_report → log_done | generate_report | emiratisation |
| `offboarding.py` | receive_exit → calculate_settlement → generate_documents → create_checklist → send_deadline_alerts → log_done | log_done | offboarding |
| `chatbot.py` | detect_language → parse_intent → fetch_data → generate_response → send_response | generate_response | chat |

---

## Database

### Core HRM Tables (Pakistan base — not modified)
Tenant, User, Role, Permission, Employee, Department, Designation, EmployeeDocument, SalaryStructure, BankDetails, AttendanceRecord, Shift, LeaveType, LeaveBalance, LeaveRequest, PublicHoliday, PayrollRun, PayrollRecord, TaxSlab, JobPosting, JobApplication, Interview, AppraisalCycle, Appraisal, Goal, TrainingProgram, TrainingEnrollment, Asset, AssetAssignment, Notification, AuditLog, AgentLog

### UAE-Specific Tables (10 additive tables)
```
companies                  — group_name, trade_license_number, mohre_establishment_id,
                             emirate, is_freezone, freezone_name
employees_uae_profile      — extends employees: passport, visa, emirates_id, labour_card,
                             bank_iban, contract dates, insurance, iloe_enrolled,
                             air_ticket_entitlement, is_emirati, nafis_enrolled
salary_structure_uae       — basic + housing + transport + food + phone + other allowances
payroll_uae                — monthly records with overtime, iloe_deduction, wps_included flag
wps_submissions            — sif_file_path, total_amount_aed, mohre_confirmation_number,
                             late_days, fine_risk_amount
gratuity_ledger            — service_years, gratuity_scenario, is_final_settlement,
                             paid_date, paid_amount
leave_balances_uae         — 9 leave types × employee × year, carried_forward_days
documents_tracker          — expiry_date, alert_sent_90/30/14/7 flags, status
emiratisation_records      — monthly snapshot: emirati_count, required_percentage,
                             compliance_gap, fine_risk_amount_aed
agent_logs_uae             — agent_name, task_type, input_data(JSONB), output_data(JSONB),
                             execution_time_ms, api_mode, triggered_by
```

### ORM Pattern
```python
# SQLAlchemy 2.0 DeclarativeBase + async engine
from app.models.base import Base, TimestampMixin, TenantScopeMixin

class MyModel(Base, TenantScopeMixin):
    __tablename__ = "my_table"
    # TenantScopeMixin gives: id (UUID), created_at, updated_at
```

---

## API Structure

### UAE Routes — `/api/v1/uae/`
```
companies_router    → /uae/companies/*
employees_router    → /uae/employees/*
payroll_router      → /uae/payroll/*
compliance_router   → /uae/compliance/*
leave_router        → /uae/leave/*
attendance_router   → /uae/attendance/*
api_trigger router  → /uae/agent/* (triggers + status + chat)
webhook_router      → /uae/webhooks/*
```

All UAE routes registered with 2 non-destructive lines in `v1_router`. Zero changes to existing Pakistan HRM routes.

### Auth
JWT (python-jose) with access tokens (15min) + refresh tokens (7 days). Cookie-based. Multi-tenant via `TenantScopeMixin`. Rate limiting via `slowapi`.

---

## Frontend Structure

### UAE Pages (6)
```
(dashboard)/uae/
├── group-dashboard/page.tsx      — all companies, WPS, Emiratisation, alerts
├── company/[id]/dashboard/       — per-company metrics
├── employees/[id]/profile/       — UAE profile: docs, visas, leave, gratuity
├── payroll/page.tsx              — AED payslips, ILOE, WPS readiness
├── compliance/page.tsx           — WPS + Emiratisation + docs + contracts
└── agent-dashboard/page.tsx      — 13 agents status, logs, manual triggers
```

### State Management
- **Zustand** — global auth store, user state
- **React Query** — server state, API calls, caching
- **React Hook Form + Zod** — form validation

### UI Pattern (all UAE pages)
```tsx
const [lang, setLang] = useState<"en" | "ar">("en");
const dir = isAr ? "rtl" : "ltr";
// Applied as <div dir={dir}> at root
// Every text: {isAr ? "النص" : "English"}
```

---

## Celery Queues

```
default          — general tasks
payroll          — Pakistan HRM payroll
notifications    — email/SMS/push
reports          — report generation
uae_compliance   — document/insurance/contract/emiratisation checks
uae_payroll      — WPS/payroll/gratuity tasks
uae_attendance   — daily reports, Ramadan detection
uae_hr           — air ticket, onboarding, offboarding
```

---

## Key Business Rules (Hard-coded, not configurable)

```python
# Payroll
ILOE_THRESHOLD = Decimal("16000")     # AED basic salary threshold
ILOE_LOW       = Decimal("5.00")      # monthly deduction < threshold
ILOE_HIGH      = Decimal("10.00")     # monthly deduction >= threshold
OT_NORMAL      = Decimal("1.25")      # 125% overtime rate
OT_PREMIUM     = Decimal("1.50")      # 150% night/Friday/holiday

# Gratuity
# < 1yr: no gratuity
# 1-5yr: 21 days basic per year
# > 5yr: 30 days basic per year
# Cap: 24 months basic salary
# Resignation 1-3yr: 1/3 of full; 3-5yr: 2/3; >5yr: full

# Emiratisation
ANNUAL_FINE_PER_SLOT = Decimal("96000")  # AED per unfilled Emirati slot/yr
QUOTA_THRESHOLD_EMPLOYEES = 50           # companies >= 50 must comply
ANNUAL_QUOTA_PCT = Decimal("0.02")       # 2% target

# Ramadan periods
RAMADAN_PERIODS = {
    2025: (date(2025, 3, 1),  date(2025, 3, 30)),
    2026: (date(2026, 2, 18), date(2026, 3, 19)),
    2027: (date(2027, 2, 7),  date(2027, 3, 8)),
}

# Offboarding
SETTLEMENT_DEADLINE_DAYS = 14  # UAE law: final pay within 14 days

# Attendance
LATE_GRACE_MINUTES = 15
MAX_OVERTIME_HOURS_PER_DAY = 2
STANDARD_HOURS = 8
RAMADAN_HOURS  = 6
```

---

## Git History (recent commits)

```
dcb9f9b  docs: license updated to private
7c0fa58  docs: professional README added
6db379f  fix: group-dashboard — remove unused imports, update to 13 LangGraph agents
cbc4974  fix: UAE env vars, Alembic auto-run, Celery UAE queues
a1c7f03  feat: UAE AI-HRM V2.0 — LangGraph + Claude Agent SDK + DB + API + Frontend
68785b4  feat: UAE AI-HRM Agent Factory Complete + refactor: clean code
```

---

## How to Work on This Project

**Quick start (Docker):**
```bash
cp .env.example backend/.env
# Add ANTHROPIC_API_KEY if you want live Claude
docker-compose up -d
# Backend auto-runs: alembic upgrade head && uvicorn
```

**Local dev (no Docker):**
```bash
cd backend && pip install -r requirements.txt
uvicorn app.main:app --reload   # needs local PG + Redis

cd frontend && npm install && npm run dev
```

**Add a new UAE agent:**
1. Create `backend/app/agents/uae/myagent.py` with `StateGraph` + `run_agent()`
2. Add task type → agent name mapping in `graph.py` `TASK_TO_AGENT`
3. Add router endpoint in `api/v1/uae/` if needed

**Run tests:**
```bash
cd backend && pytest tests/ -v  # requires Docker DB on port 5432
```

# AI-HRMS — Intelligent Human Resource Management System

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-14-black?logo=next.js)](https://nextjs.org)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://docker.com)

A full-featured, AI-powered Human Resource Management System built for modern organizations. AI-HRMS covers the complete employee lifecycle — from recruitment through retirement — in a single, multi-tenant platform. It combines a high-performance FastAPI backend, a responsive Next.js frontend, and OpenAI-powered intelligence to deliver actionable workforce insights.

---

## Features

- **Employee Management** — Complete employee profiles, org chart, document vault, salary structures, and employment lifecycle management
- **Attendance & Shifts** — Clock-in/clock-out with GPS verification, shift management, overtime calculation, and a real-time WebSocket attendance feed
- **Leave Management** — Multi-type leave policies, accrual rules, approval workflows, team calendar, and public holiday management
- **Payroll Engine** — Automated payroll runs with Pakistani FBR tax slabs, configurable salary components, and one-click payslip generation
- **Recruitment Pipeline** — Job postings, public job board, multi-stage candidate pipeline, interview scheduling, and AI-powered CV scoring
- **Performance Management** — Appraisal cycles, 360-degree reviews, goal tracking with progress updates, and department-level analytics
- **Training & Development** — Training program catalog, enrollment management, completion tracking, and material uploads
- **Asset Management** — Asset registry, assignment/return workflow, and per-employee asset history
- **AI Attrition Prediction** — Machine learning model predicts employee flight risk with contributing factor explanations
- **AI HR Chatbot** — Natural language HR assistant answers workforce questions, generates reports, and surfaces insights
- **AI Performance Analysis** — Automatically identifies top performers, skill gaps, and improvement areas across appraisal cycles
- **Departments & Designations** — Hierarchical org structure with department heads and nested sub-departments
- **Notifications** — In-app and real-time WebSocket notifications for all workflow events; email + SMS via SendGrid and Twilio
- **Reports & Analytics** — Headcount, turnover, payroll cost, attendance, leave utilization, and recruitment funnel reports with export to CSV/Excel
- **Multi-Tenant Architecture** — Full data isolation per tenant with subdomain routing and per-tenant configuration
- **RBAC Permissions** — 9 granular roles from SUPER_ADMIN to EMPLOYEE with permission-level access control

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | FastAPI 0.115, Python 3.11, SQLAlchemy 2.0 (async) |
| Database | PostgreSQL 15 |
| Cache / Queue Broker | Redis 7 |
| Background Tasks | Celery 5 + RedBeat scheduler |
| Frontend | Next.js 14, React 18, TypeScript |
| UI Components | shadcn/ui, Tailwind CSS |
| State Management | TanStack Query v5, Zustand |
| Authentication | JWT (access + refresh tokens), HTTP-only cookies |
| AI / LLM | OpenAI GPT-4o-mini, scikit-learn (attrition model) |
| Real-time | WebSocket (FastAPI native) |
| File Storage | Local volume (S3-compatible swap-out) |
| Email | SendGrid |
| SMS | Twilio |
| Containerization | Docker, Docker Compose |
| Reverse Proxy | Nginx |
| SSL | Let's Encrypt (Certbot) |
| Migrations | Alembic |
| Testing | pytest, pytest-asyncio, httpx |

---

## Quick Start (Docker — 3 commands)

```bash
git clone https://github.com/your-org/ai-hrms.git && cd ai-hrms
cp .env.example .env   # Edit with your settings (see Environment Variables below)
docker-compose up -d
```

Then open:
- **Frontend:** http://localhost:3000
- **API Docs (Swagger):** http://localhost:8000/api/v1/docs
- **API Docs (Redoc):** http://localhost:8000/api/v1/redoc

**Demo credentials:** `demo@hrms.local` / `Demo@1234!`

After the containers start, run the first-time setup:

```bash
# Apply database migrations
docker-compose exec backend alembic upgrade head

# Seed superadmin (uses values from .env)
docker-compose exec backend python -m scripts.seed_superadmin
```

---

## Environment Variables

Copy `.env.example` to `.env` and set the following key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `POSTGRES_USER` | Yes | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | PostgreSQL password (use a strong random value) |
| `POSTGRES_DB` | Yes | Database name (default: `hrms_db`) |
| `JWT_SECRET_KEY` | Yes | Secret for signing JWTs — generate with `openssl rand -hex 64` |
| `SECRET_KEY` | Yes | Application secret — generate with `openssl rand -hex 32` |
| `REDIS_PASSWORD` | Yes | Redis auth password |
| `FRONTEND_URL` | Yes | Public URL of the frontend (e.g., `https://your-domain.com`) |
| `BACKEND_URL` | Yes | Public URL of the API (e.g., `https://api.your-domain.com`) |
| `CORS_ORIGINS` | Yes | Comma-separated allowed origins |
| `FIRST_SUPERADMIN_EMAIL` | Yes | Email for the seeded superadmin account |
| `FIRST_SUPERADMIN_PASSWORD` | Yes | Password for the seeded superadmin account |
| `SENDGRID_API_KEY` | No | SendGrid key for transactional emails |
| `TWILIO_ACCOUNT_SID` | No | Twilio SID for SMS notifications |
| `TWILIO_AUTH_TOKEN` | No | Twilio auth token |
| `OPENAI_API_KEY` | No | OpenAI API key for AI features (attrition, chatbot, CV scoring) |
| `OPENAI_MODEL` | No | Model name (default: `gpt-4o-mini`) |
| `STORAGE_BACKEND` | No | `local` (default) or `s3` |
| `AWS_ACCESS_KEY_ID` | No | Required if `STORAGE_BACKEND=s3` |
| `AWS_SECRET_ACCESS_KEY` | No | Required if `STORAGE_BACKEND=s3` |
| `AWS_S3_BUCKET` | No | S3 bucket name for file uploads |

---

## Module Overview

| Module | Key Features |
|--------|-------------|
| **Auth** | JWT login/refresh/logout, profile management, password change, RBAC enforcement |
| **Employees** | Full employee lifecycle, org chart, salary management, document uploads, CSV/Excel export |
| **Departments** | Hierarchical structure, department heads, employee count reporting |
| **Designations** | Job titles linked to departments, grade levels |
| **Attendance** | GPS check-in/out, shift assignment, overtime tracking, manual HR adjustments, live WebSocket feed |
| **Leave** | Multi-type leave policies, accrual, carry-forward, team calendar, public holidays, approval workflow |
| **Payroll** | Automated calculation, Pakistani FBR tax slabs, allowances/deductions, payslip PDF generation |
| **Recruitment** | Job postings, public board, multi-stage pipeline, interview scheduling, offer letters, AI CV scoring |
| **Performance** | Appraisal cycles, self + manager review, goal tracking, AI-powered cycle analysis |
| **Training** | Program catalog, enrollment, capacity limits, completion tracking, material library |
| **Assets** | Asset registry, assignment/return workflow, condition tracking, employee asset history |
| **Notifications** | Real-time in-app notifications via WebSocket, email, and SMS triggers |
| **Reports** | 8 built-in reports (headcount, turnover, payroll, attendance, leave, recruitment, training), CSV/Excel export |
| **AI Features** | Attrition risk prediction, performance analysis, HR chatbot, workforce analytics, CV scoring |

---

## API Documentation

| Interface | URL | Description |
|-----------|-----|-------------|
| Swagger UI | http://localhost:8000/api/v1/docs | Interactive API explorer |
| Redoc | http://localhost:8000/api/v1/redoc | Clean API reference |
| OpenAPI JSON | http://localhost:8000/api/v1/openapi.json | Machine-readable schema |

For the full API reference with all endpoints, see [docs/API_REFERENCE.md](docs/API_REFERENCE.md).

---

## Project Structure

```
ai-hrms/
├── backend/                        # FastAPI application
│   ├── app/
│   │   ├── main.py                 # Application entry point, CORS, routers
│   │   ├── core/
│   │   │   ├── config.py           # Settings (pydantic-settings)
│   │   │   ├── security.py         # JWT helpers, password hashing
│   │   │   ├── database.py         # Async SQLAlchemy engine + session
│   │   │   └── dependencies.py     # FastAPI dependency injection
│   │   ├── models/                 # SQLAlchemy ORM models
│   │   │   ├── tenant.py
│   │   │   ├── user.py
│   │   │   ├── employee.py
│   │   │   ├── department.py
│   │   │   ├── attendance.py
│   │   │   ├── leave.py
│   │   │   ├── payroll.py
│   │   │   ├── recruitment.py
│   │   │   ├── performance.py
│   │   │   ├── training.py
│   │   │   ├── asset.py
│   │   │   └── notification.py
│   │   ├── schemas/                # Pydantic request/response schemas
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py
│   │   │       ├── employees.py
│   │   │       ├── departments.py
│   │   │       ├── designations.py
│   │   │       ├── attendance.py
│   │   │       ├── leave.py
│   │   │       ├── payroll.py
│   │   │       ├── recruitment.py
│   │   │       ├── performance.py
│   │   │       ├── training.py
│   │   │       ├── assets.py
│   │   │       ├── notifications.py
│   │   │       ├── reports.py
│   │   │       ├── ai.py
│   │   │       └── admin.py
│   │   ├── services/               # Business logic layer
│   │   │   ├── auth_service.py
│   │   │   ├── employee_service.py
│   │   │   ├── payroll_service.py
│   │   │   ├── attendance_service.py
│   │   │   ├── leave_service.py
│   │   │   ├── recruitment_service.py
│   │   │   ├── ai_service.py
│   │   │   └── notification_service.py
│   │   ├── worker/
│   │   │   ├── celery_app.py       # Celery application factory
│   │   │   ├── tasks/
│   │   │   │   ├── payroll_tasks.py
│   │   │   │   ├── notification_tasks.py
│   │   │   │   ├── report_tasks.py
│   │   │   │   └── ai_tasks.py
│   │   │   └── schedules.py        # Periodic task definitions (RedBeat)
│   │   └── websockets/
│   │       ├── attendance_ws.py    # Real-time attendance WebSocket
│   │       └── notifications_ws.py # Real-time notifications WebSocket
│   ├── alembic/                    # Database migrations
│   │   ├── versions/
│   │   └── env.py
│   ├── scripts/
│   │   ├── seed_superadmin.py      # First-run superadmin seeding
│   │   ├── init_db.sql             # PostgreSQL init script
│   │   └── backup.sh               # Database backup script
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_employees.py
│   │   ├── test_payroll.py
│   │   └── test_attendance.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   └── pytest.ini
│
├── frontend/                       # Next.js application
│   ├── app/                        # Next.js 14 App Router
│   │   ├── (auth)/
│   │   │   └── login/
│   │   ├── (dashboard)/
│   │   │   ├── employees/
│   │   │   ├── attendance/
│   │   │   ├── leave/
│   │   │   ├── payroll/
│   │   │   ├── recruitment/
│   │   │   ├── performance/
│   │   │   ├── training/
│   │   │   ├── assets/
│   │   │   ├── reports/
│   │   │   └── ai/
│   │   └── public/                 # Public job board (no auth)
│   ├── components/
│   │   ├── ui/                     # shadcn/ui components
│   │   ├── layouts/
│   │   ├── charts/
│   │   └── modules/                # Module-specific components
│   ├── lib/
│   │   ├── api.ts                  # Axios API client
│   │   ├── auth.ts                 # Auth helpers
│   │   └── utils.ts
│   ├── hooks/                      # Custom React hooks
│   ├── stores/                     # Zustand state stores
│   ├── types/                      # TypeScript type definitions
│   └── public/
│
├── docs/
│   ├── API_REFERENCE.md            # Complete API endpoint reference
│   ├── DEPLOYMENT.md               # Production deployment guide
│   └── architecture/               # Architecture diagrams and docs
│
├── nginx/
│   ├── nginx.prod.conf             # Production Nginx main config
│   └── conf.d/
│       └── hrms.conf               # Virtual host configuration
│
├── docker-compose.yml              # Development environment
├── docker-compose.prod.yml         # Production environment
├── Dockerfile.frontend             # Frontend Docker build
├── .env.example                    # Environment variable template
├── package.json                    # Frontend package manifest
├── requirements.txt                # Python dependencies (top-level reference)
└── README.md                       # This file
```

---

## Screenshots

> Screenshots and demo GIFs will be added here.

| Screen | Description |
|--------|-------------|
| Dashboard | KPI overview — headcount, attendance %, open positions, payroll cost |
| Employee Directory | Searchable employee list with department/status filters |
| Attendance Live Feed | Real-time clock-in/out board with WebSocket updates |
| Leave Calendar | Team leave calendar with monthly view |
| Payroll Run | Step-by-step payroll processing with tax breakdown |
| Recruitment Pipeline | Kanban-style candidate pipeline view |
| AI Attrition Dashboard | Risk heatmap with employee risk scores and factors |
| HR Chatbot | Conversational HR assistant with suggested actions |

---

## Development

### Prerequisites

- Docker 24+ and Docker Compose v2
- Git

### Run in Development Mode

```bash
# Start all services with hot reload
docker-compose up -d

# View logs
docker-compose logs -f backend

# Run backend tests
docker-compose exec backend pytest tests/ -v

# Run a specific test file
docker-compose exec backend pytest tests/test_payroll.py -v

# Open a shell in the backend container
docker-compose exec backend bash

# Create a new migration after model changes
docker-compose exec backend alembic revision --autogenerate -m "add_new_table"

# Apply migrations
docker-compose exec backend alembic upgrade head
```

### Run Frontend in Standalone Mode (without Docker)

```bash
cd frontend
npm install
cp .env.local.example .env.local   # set NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

---

## Production Deployment

See the complete production deployment guide: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

Quick summary:
1. Ubuntu 22.04 server with Docker and Nginx installed
2. Clone repo, populate `.env` from `.env.example`
3. `docker compose -f docker-compose.prod.yml up -d`
4. `docker compose -f docker-compose.prod.yml exec backend alembic upgrade head`
5. Configure Nginx reverse proxy and SSL with Certbot

---

## Contributing

Contributions are welcome. Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature-name`
3. Make your changes with clear, descriptive commits
4. Write or update tests for new functionality
5. Ensure all tests pass: `docker-compose exec backend pytest`
6. Push to your fork: `git push origin feature/your-feature-name`
7. Open a Pull Request against `main` with a clear description of the changes

### Code Style

- **Python:** Black formatter, isort imports, flake8 linting
- **TypeScript:** ESLint + Prettier
- **Commits:** Conventional Commits format (`feat:`, `fix:`, `docs:`, `refactor:`, etc.)

### Reporting Issues

Please open a GitHub Issue with:
- A clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or screenshots

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

```
MIT License

Copyright (c) 2025 AI-HRMS Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

---

## Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com) — modern, high-performance Python web framework
- [Next.js](https://nextjs.org) — React framework for production
- [shadcn/ui](https://ui.shadcn.com) — accessible component library
- [SQLAlchemy](https://sqlalchemy.org) — Python SQL toolkit and ORM
- [Celery](https://docs.celeryq.dev) — distributed task queue
- [OpenAI](https://openai.com) — AI language model API

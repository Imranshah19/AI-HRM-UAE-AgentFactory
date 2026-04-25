# AI-HRMS API Reference

**Base URL:** `https://your-domain.com/api/v1`
**API Version:** v1
**Authentication:** Bearer JWT token in `Authorization` header, unless marked **No Auth**
**Content-Type:** `application/json` (multipart/form-data for file uploads)

---

## Authentication

All protected endpoints require the header:
```
Authorization: Bearer <access_token>
```

Access tokens expire in **15 minutes**. Use `POST /auth/refresh` (via HTTP-only cookie) to obtain a new one.

---

## Response Envelope

```json
{
  "success": true,
  "data": { ... },
  "message": "Operation completed",
  "meta": { "page": 1, "per_page": 20, "total": 150 }
}
```

Error responses:
```json
{
  "success": false,
  "error": { "code": "VALIDATION_ERROR", "detail": "..." }
}
```

---

## HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK — request succeeded |
| 201 | Created — resource created |
| 204 | No Content — deletion succeeded |
| 400 | Bad Request — validation error |
| 401 | Unauthorized — missing or invalid token |
| 403 | Forbidden — insufficient permissions |
| 404 | Not Found — resource not found |
| 409 | Conflict — duplicate resource |
| 422 | Unprocessable Entity — schema error |
| 500 | Internal Server Error |

---

## Pagination

List endpoints accept:
- `page` (default: 1)
- `per_page` (default: 20, max: 100)
- `sort` field name
- `order` — `asc` or `desc`

---

## Modules

### Auth

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/auth/login | Login with email + password; returns `access_token` (body) and `refresh_token` (HTTP-only cookie) | No |
| POST | /api/v1/auth/refresh | Issue a new access token using the `refresh_token` cookie | No |
| POST | /api/v1/auth/logout | Revoke the current refresh token and clear the cookie | Yes |
| GET | /api/v1/auth/me | Get the authenticated user's profile, roles, and tenant info | Yes |
| PATCH | /api/v1/auth/me | Update own profile fields (first_name, last_name, phone, avatar) | Yes |
| POST | /api/v1/auth/change-password | Change own password (requires `current_password` + `new_password`) | Yes |

**POST /api/v1/auth/login — Request Body:**
```json
{ "email": "user@company.com", "password": "Secret@123" }
```
**Response:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900,
  "user": { "id": "uuid", "email": "...", "role": "HR_MANAGER" }
}
```

---

### Employees

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /api/v1/employees | List employees with filters: `search`, `department_id`, `designation_id`, `status`, `employment_type` | Yes |
| POST | /api/v1/employees | Create a new employee record with personal info, job info, and salary | Yes |
| GET | /api/v1/employees/{id} | Get full employee profile including job, salary, documents, emergency contacts | Yes |
| PATCH | /api/v1/employees/{id} | Update employee fields (partial update) | Yes |
| DELETE | /api/v1/employees/{id} | Soft-delete / archive employee record | Yes |
| POST | /api/v1/employees/{id}/status | Change employment status: `active`, `on_leave`, `terminated`, `probation` | Yes |
| GET | /api/v1/employees/{id}/salary | Get current salary structure (basic, allowances, deductions) | Yes |
| PATCH | /api/v1/employees/{id}/salary | Update salary structure with effective date | Yes |
| POST | /api/v1/employees/{id}/documents | Upload employee document (CNIC, degree, contract); multipart/form-data | Yes |
| GET | /api/v1/employees/{id}/documents | List all documents for an employee | Yes |
| DELETE | /api/v1/employees/{id}/documents/{doc_id} | Delete a specific document | Yes |
| GET | /api/v1/employees/org-chart | Return hierarchical org chart JSON based on `reports_to` relationships | Yes |
| GET | /api/v1/employees/export | Export employee list as CSV or Excel; accepts `format=csv\|xlsx` query param | Yes |

**GET /api/v1/employees — Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| search | string | Search by name, email, or employee code |
| department_id | uuid | Filter by department |
| designation_id | uuid | Filter by designation |
| status | string | `active`, `terminated`, `on_leave`, `probation` |
| employment_type | string | `full_time`, `part_time`, `contract`, `intern` |
| page | int | Page number (default: 1) |
| per_page | int | Results per page (default: 20) |

---

### Departments

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /api/v1/departments | List all departments for the tenant (with employee count) | Yes |
| POST | /api/v1/departments | Create a new department (`name`, `code`, `head_id`, `parent_id`) | Yes |
| GET | /api/v1/departments/{id} | Get department details including head employee and sub-departments | Yes |
| PATCH | /api/v1/departments/{id} | Update department name, head, or parent | Yes |
| DELETE | /api/v1/departments/{id} | Delete department (only if no active employees) | Yes |

---

### Designations

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /api/v1/designations | List all designations with optional `department_id` filter | Yes |
| POST | /api/v1/designations | Create designation (`title`, `department_id`, `grade`, `description`) | Yes |
| GET | /api/v1/designations/{id} | Get designation details and linked employees count | Yes |
| PATCH | /api/v1/designations/{id} | Update designation fields | Yes |
| DELETE | /api/v1/designations/{id} | Delete designation (only if no active employees hold it) | Yes |

---

### Attendance

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/attendance/check-in | Record clock-in timestamp; optional body fields: `latitude`, `longitude`, `device_id` | Yes |
| POST | /api/v1/attendance/check-out | Record clock-out timestamp; calculates work hours automatically | Yes |
| GET | /api/v1/attendance/today | Get today's attendance status for the current authenticated user | Yes |
| GET | /api/v1/attendance | List attendance records with filters: `employee_id`, `from_date`, `to_date`, `status` | Yes |
| GET | /api/v1/attendance/{employee_id}/summary | Monthly attendance summary: present, absent, late, overtime hours | Yes |
| POST | /api/v1/attendance/shifts | Create a new work shift (`name`, `start_time`, `end_time`, `grace_minutes`) | Yes |
| GET | /api/v1/attendance/shifts | List all shifts for the tenant | Yes |
| PATCH | /api/v1/attendance/shifts/{id} | Update shift timings | Yes |
| PATCH | /api/v1/attendance/{id}/adjust | Manual adjustment of an attendance record with reason (HR only) | Yes |
| GET | /api/v1/attendance/live | Get live attendance stats for today (total in, total out, currently working) | Yes |
| WS | /ws/attendance | WebSocket endpoint — real-time attendance feed; emits events on check-in/check-out | Yes |

**WebSocket /ws/attendance:**
- Connect with `Authorization` query param: `wss://host/ws/attendance?token=<access_token>`
- Emits JSON events: `{ "event": "check_in", "employee_id": "uuid", "name": "...", "timestamp": "..." }`

---

### Leave

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/leave/requests | Apply for leave (`leave_type_id`, `from_date`, `to_date`, `reason`) | Yes |
| GET | /api/v1/leave/requests | List leave requests; HR sees all, employee sees own; filters: `status`, `employee_id`, `from_date` | Yes |
| GET | /api/v1/leave/requests/{id} | Get leave request details including approval history | Yes |
| PATCH | /api/v1/leave/requests/{id}/approve | Approve a pending leave request; optional `comment` in body | Yes |
| PATCH | /api/v1/leave/requests/{id}/reject | Reject a leave request with mandatory `reason` | Yes |
| PATCH | /api/v1/leave/requests/{id}/cancel | Cancel own pending or approved leave request | Yes |
| GET | /api/v1/leave/balances | Get current user's leave balances per leave type | Yes |
| GET | /api/v1/leave/balances/{employee_id} | Get leave balances for a specific employee (HR/Manager only) | Yes |
| GET | /api/v1/leave/types | List all leave types (annual, sick, casual, maternity, etc.) | Yes |
| POST | /api/v1/leave/types | Create a new leave type with rules (accrual, carry-forward, max days) | Yes |
| PATCH | /api/v1/leave/types/{id} | Update leave type configuration | Yes |
| GET | /api/v1/leave/calendar | Team leave calendar for a given month; shows who is on leave on each date | Yes |
| POST | /api/v1/leave/holidays | Add a public holiday (`date`, `name`, `is_optional`) | Yes |
| GET | /api/v1/leave/holidays | List public holidays for the year; accepts `year` query param | Yes |
| DELETE | /api/v1/leave/holidays/{id} | Remove a public holiday | Yes |

---

### Payroll

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/payroll/runs | Create a new payroll run (`period_start`, `period_end`, `name`) | Yes |
| GET | /api/v1/payroll/runs | List all payroll runs for the tenant with status (`draft`, `processing`, `approved`, `paid`) | Yes |
| GET | /api/v1/payroll/runs/{id} | Get payroll run details: period, status, totals, employee count | Yes |
| POST | /api/v1/payroll/runs/{id}/process | Trigger payroll calculation: applies salary, attendance deductions, taxes, allowances | Yes |
| POST | /api/v1/payroll/runs/{id}/approve | Approve the processed payroll run (requires PAYROLL_APPROVER role) | Yes |
| POST | /api/v1/payroll/runs/{id}/pay | Mark payroll run as paid and generate payslips | Yes |
| GET | /api/v1/payroll/runs/{id}/records | List individual payroll records (payslips) within a run; paginated | Yes |
| GET | /api/v1/payroll/payslip/{employee_id} | Get the latest processed payslip for an employee | Yes |
| GET | /api/v1/payroll/payslip/{employee_id}/{run_id} | Get payslip for a specific payroll run | Yes |
| GET | /api/v1/payroll/tax-slabs | Get current income tax slab configuration (Pakistani FBR slabs by default) | Yes |
| POST | /api/v1/payroll/tax-slabs | Update or replace tax slab configuration (SUPER_ADMIN only) | Yes |
| GET | /api/v1/payroll/components | List all salary components (basic, HRA, transport, etc.) | Yes |
| POST | /api/v1/payroll/components | Create a new salary component | Yes |

---

### Recruitment

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/recruitment/jobs | Create a job posting (`title`, `department_id`, `designation_id`, `description`, `requirements`, `vacancies`) | Yes |
| GET | /api/v1/recruitment/jobs | List all job postings; filters: `status`, `department_id` | Yes |
| GET | /api/v1/recruitment/jobs/{id} | Get full job posting details | Yes |
| PATCH | /api/v1/recruitment/jobs/{id} | Update job posting fields | Yes |
| DELETE | /api/v1/recruitment/jobs/{id} | Delete a draft job posting | Yes |
| POST | /api/v1/recruitment/jobs/{id}/publish | Publish the job posting (makes it visible on public job board) | Yes |
| POST | /api/v1/recruitment/jobs/{id}/close | Close the job posting (no new applications accepted) | Yes |
| GET | /api/v1/recruitment/applications | List all applications; filters: `job_id`, `stage`, `source` | Yes |
| POST | /api/v1/recruitment/applications | Submit application internally (HR submitting on behalf of candidate) | Yes |
| GET | /api/v1/recruitment/applications/{id} | Get application details including stage history, interviews, notes | Yes |
| PATCH | /api/v1/recruitment/applications/{id}/stage | Move application to new pipeline stage: `applied`, `screening`, `interview`, `offer`, `hired`, `rejected` | Yes |
| POST | /api/v1/recruitment/applications/{id}/interviews | Schedule an interview (`type`, `scheduled_at`, `interviewers`, `location_or_link`) | Yes |
| PATCH | /api/v1/recruitment/applications/{id}/interviews/{interview_id} | Update interview result and feedback | Yes |
| POST | /api/v1/recruitment/applications/{id}/offer | Generate and send offer letter to candidate | Yes |
| POST | /api/v1/recruitment/applications/{id}/cv | Upload candidate CV/resume (multipart/form-data) | Yes |
| POST | /api/v1/recruitment/applications/{id}/notes | Add a note to an application | Yes |
| GET | /api/v1/public/jobs | Public job board listing (no auth, only published open jobs) | No |
| GET | /api/v1/public/jobs/{id} | Public job detail page | No |
| POST | /api/v1/public/jobs/{id}/apply | Public application submission form with CV upload | No |

---

### Performance

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/performance/cycles | Create an appraisal cycle (`name`, `start_date`, `end_date`, `type`: annual/mid-year/quarterly) | Yes |
| GET | /api/v1/performance/cycles | List appraisal cycles with status | Yes |
| GET | /api/v1/performance/cycles/{id} | Get cycle details and overall stats | Yes |
| PATCH | /api/v1/performance/cycles/{id} | Update cycle configuration or close it | Yes |
| POST | /api/v1/performance/cycles/{id}/launch | Launch cycle — auto-create appraisal records for all active employees | Yes |
| GET | /api/v1/performance/cycles/{id}/appraisals | List all appraisals within a cycle; filters: `department_id`, `status` | Yes |
| GET | /api/v1/performance/appraisals/{id} | Get individual appraisal details (self-assessment, manager review, ratings, comments) | Yes |
| PATCH | /api/v1/performance/appraisals/{id} | Submit or update appraisal (self or manager section depending on role) | Yes |
| POST | /api/v1/performance/goals | Create a goal linked to an employee (`title`, `description`, `target_date`, `weight`) | Yes |
| GET | /api/v1/performance/goals | List goals; employee sees own, manager sees reportees' goals; filter by `status` | Yes |
| GET | /api/v1/performance/goals/{id} | Get goal details and progress history | Yes |
| PATCH | /api/v1/performance/goals/{id} | Update goal progress (`progress_percentage`, `status`, `comment`) | Yes |
| DELETE | /api/v1/performance/goals/{id} | Delete a draft goal | Yes |

---

### Training

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/training/programs | Create a training program (`title`, `description`, `trainer`, `start_date`, `end_date`, `capacity`) | Yes |
| GET | /api/v1/training/programs | List all training programs; filters: `status`, `from_date`, `to_date` | Yes |
| GET | /api/v1/training/programs/{id} | Get program details including enrollment count and materials | Yes |
| PATCH | /api/v1/training/programs/{id} | Update training program details | Yes |
| DELETE | /api/v1/training/programs/{id} | Delete a training program (only if no enrollments) | Yes |
| POST | /api/v1/training/programs/{id}/enroll | Enroll one or more employees in a program (`employee_ids: [...]`) | Yes |
| GET | /api/v1/training/enrollments | List enrollments; employee sees own, HR sees all; filters: `program_id`, `status` | Yes |
| GET | /api/v1/training/enrollments/{id} | Get enrollment details | Yes |
| PATCH | /api/v1/training/enrollments/{id}/complete | Mark enrollment as completed with optional `score` and `feedback` | Yes |
| PATCH | /api/v1/training/enrollments/{id}/cancel | Cancel an enrollment | Yes |
| POST | /api/v1/training/programs/{id}/materials | Upload training material (PDF, video link, etc.) | Yes |

---

### Assets

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/assets | Add a new asset (`name`, `asset_tag`, `category`, `serial_number`, `purchase_date`, `purchase_value`) | Yes |
| GET | /api/v1/assets | List all assets; filters: `category`, `status`, `assigned_to` | Yes |
| GET | /api/v1/assets/{id} | Get asset details including assignment history | Yes |
| PATCH | /api/v1/assets/{id} | Update asset information (category, value, condition) | Yes |
| DELETE | /api/v1/assets/{id} | Delete asset record (only if unassigned and not in use) | Yes |
| POST | /api/v1/assets/{id}/assign | Assign asset to an employee (`employee_id`, `assigned_date`, `notes`) | Yes |
| POST | /api/v1/assets/{id}/return | Return asset from employee (`return_date`, `condition`, `notes`) | Yes |
| GET | /api/v1/assets/employee/{employee_id} | List all assets currently assigned to a specific employee | Yes |
| GET | /api/v1/assets/categories | List asset categories | Yes |
| POST | /api/v1/assets/categories | Create a new asset category | Yes |

---

### Notifications

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /api/v1/notifications | List notifications for current user; filters: `is_read`, `type`; paginated | Yes |
| GET | /api/v1/notifications/unread-count | Get count of unread notifications (lightweight, for badge display) | Yes |
| PATCH | /api/v1/notifications/{id}/read | Mark a specific notification as read | Yes |
| POST | /api/v1/notifications/read-all | Mark all notifications as read for current user | Yes |
| DELETE | /api/v1/notifications/{id} | Delete a specific notification | Yes |
| DELETE | /api/v1/notifications | Bulk delete read notifications for current user | Yes |
| WS | /ws/notifications | WebSocket endpoint for real-time notification delivery | Yes |

---

### Reports

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /api/v1/reports/dashboard | Dashboard statistics: headcount, open positions, today's attendance %, monthly turnover | Yes |
| GET | /api/v1/reports/headcount | Headcount report by department, designation, employment type; accepts `as_of_date` param | Yes |
| GET | /api/v1/reports/turnover | Turnover/attrition report for a date range; shows monthly trend and department breakdown | Yes |
| GET | /api/v1/reports/attendance | Attendance summary report: present %, late %, absent % per department for a period | Yes |
| GET | /api/v1/reports/payroll | Payroll cost report: total cost, department breakdown, month-over-month comparison | Yes |
| GET | /api/v1/reports/leave | Leave utilization report: total leaves taken vs balance, by type and department | Yes |
| GET | /api/v1/reports/recruitment | Recruitment funnel report: applications, shortlisted, interviewed, offered, hired per job | Yes |
| GET | /api/v1/reports/training | Training completion rates per program and department | Yes |
| GET | /api/v1/reports/export/{report_type} | Export any report as CSV or Excel; `report_type`: headcount, payroll, attendance, etc. | Yes |

**Common Query Parameters for Reports:**
| Param | Description |
|-------|-------------|
| from_date | Start of report period (YYYY-MM-DD) |
| to_date | End of report period (YYYY-MM-DD) |
| department_id | Filter by department |
| format | `json` (default), `csv`, or `xlsx` |

---

### AI Features

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /api/v1/ai/attrition/predict | Run attrition risk prediction model for all active employees in the tenant; returns job_id for async result | Yes |
| GET | /api/v1/ai/attrition/risk-employees | Get list of high-risk employees with attrition scores and contributing factors | Yes |
| GET | /api/v1/ai/attrition/employee/{employee_id} | Get detailed attrition risk analysis for a specific employee | Yes |
| POST | /api/v1/ai/performance/analyze | Analyze an appraisal cycle: identify top performers, underperformers, skill gaps | Yes |
| POST | /api/v1/ai/chat | Chat with the HR AI assistant; body: `{ "message": "...", "context": {} }` | Yes |
| GET | /api/v1/ai/chat/history | Get chat history for current user (last 50 messages) | Yes |
| GET | /api/v1/ai/analytics/workforce | Get AI-generated workforce insights: diversity, experience distribution, tenure analysis | Yes |
| POST | /api/v1/ai/recruitment/score-cv | Score/rank a candidate's CV against a job description using AI | Yes |
| GET | /api/v1/ai/jobs/{id}/status | Get status of an async AI job (predict, analyze) | Yes |

**POST /api/v1/ai/chat — Request Body:**
```json
{
  "message": "How many employees are on leave this week?",
  "context": { "employee_id": null }
}
```
**Response:**
```json
{
  "reply": "There are 7 employees on approved leave this week...",
  "sources": ["leave_requests", "calendar"],
  "suggested_actions": [{ "label": "View Leave Calendar", "url": "/leave/calendar" }]
}
```

---

## Tenant & Admin Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | /api/v1/admin/tenants | List all tenants (SUPER_ADMIN only) | Yes |
| POST | /api/v1/admin/tenants | Create new tenant (onboarding) | Yes |
| GET | /api/v1/admin/tenants/{id} | Get tenant details | Yes |
| PATCH | /api/v1/admin/tenants/{id} | Update tenant settings | Yes |
| GET | /api/v1/admin/users | List all users for current tenant | Yes |
| POST | /api/v1/admin/users | Create a system user account | Yes |
| PATCH | /api/v1/admin/users/{id}/role | Assign or change user role | Yes |
| POST | /api/v1/admin/users/{id}/deactivate | Deactivate user account | Yes |

---

## RBAC Roles

| Role | Description |
|------|-------------|
| SUPER_ADMIN | Full system access across all tenants |
| TENANT_ADMIN | Full access within own tenant |
| HR_MANAGER | Access to all HR modules |
| HR_STAFF | Read/write access to core HR; no payroll approval |
| MANAGER | Manage own team (leave approval, attendance, reviews) |
| EMPLOYEE | Self-service access only |
| RECRUITER | Recruitment module only |
| PAYROLL_OFFICER | Payroll module read/write |
| PAYROLL_APPROVER | Can approve payroll runs |

---

## Changelog

| Version | Date | Notes |
|---------|------|-------|
| v1.0.0 | 2025-01 | Initial release |
| v1.1.0 | 2025-04 | AI attrition prediction added |
| v1.2.0 | 2025-07 | Real-time WebSocket attendance + notifications |
| v1.3.0 | 2026-01 | AI HR chatbot, CV scoring, performance analysis |

# Section 3: API Design

## 3.1 API Conventions

```
Base URL:        https://api.hrms.company.com/api/v1
Authentication:  Bearer JWT token in Authorization header
Content-Type:    application/json
Pagination:      ?page=1&page_size=20 (default 20, max 100)
Filtering:       ?department_id=uuid&status=active
Sorting:         ?sort_by=created_at&sort_order=desc
Response format:
  {
    "success": true,
    "data": { ... } | [ ... ],
    "meta": { "page": 1, "page_size": 20, "total": 150, "total_pages": 8 },
    "message": "Success"
  }

Error format:
  {
    "success": false,
    "error_code": "LEAVE_BALANCE_INSUFFICIENT",
    "message": "Insufficient leave balance. Available: 2 days, Requested: 5 days",
    "details": { ... }
  }
```

---

## 3.2 API Routes — All Modules

### MODULE 1: Employee Management

---

**`GET /api/v1/employees`**
- Description: List all employees with filtering and pagination
- Auth: Required (HR Manager, Super Admin, Dept Manager — own dept)
- Query params: `department_id`, `status`, `contract_type`, `hire_date_from`, `hire_date_to`, `search` (name/code/email)
- Response:
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "employee_code": "EMP-0042",
      "full_name": "Ahmed Khan",
      "work_email": "ahmed.khan@company.com",
      "department": { "id": "uuid", "name": "Engineering" },
      "job_grade": { "id": "uuid", "title": "Senior Engineer", "grade_code": "L4" },
      "status": "active",
      "hire_date": "2022-03-15",
      "profile_photo_url": "https://cdn.hrms.com/photos/abc123.jpg"
    }
  ],
  "meta": { "page": 1, "page_size": 20, "total": 243 }
}
```
- Error codes: `403 FORBIDDEN`, `400 INVALID_FILTER`

---

**`POST /api/v1/employees`**
- Description: Create new employee record (onboarding)
- Auth: Required — HR Manager, Super Admin
- Permission: `employee:create`
- Request body:
```json
{
  "first_name": "Sara",
  "last_name": "Ahmed",
  "work_email": "sara.ahmed@company.com",
  "department_id": "uuid",
  "job_grade_id": "uuid",
  "reporting_manager_id": "uuid",
  "hire_date": "2024-02-01",
  "contract_type": "permanent",
  "national_id": "3520212345679"
}
```
- Response: `201 Created` with full employee object
- Error codes: `409 EMAIL_ALREADY_EXISTS`, `422 VALIDATION_ERROR`

---

**`GET /api/v1/employees/{employee_id}`**
- Description: Get full employee profile
- Auth: Required — Employee (own), Manager (own team), HR, Admin
- Field-level permissions: salary fields only visible to HR/Finance/Admin
- Response: Full employee object with sensitive fields redacted by role

---

**`PATCH /api/v1/employees/{employee_id}`**
- Description: Update employee profile fields
- Auth: Required — Employee (limited own fields), HR Manager (all fields), Admin
- Request body: Partial employee object (only changed fields)
- Audit log: Every field change recorded
- Response: Updated employee object

---

**`DELETE /api/v1/employees/{employee_id}`**
- Description: Soft delete (set is_active=false, trigger offboarding workflow)
- Auth: Super Admin only
- Response: `200 OK`

---

**`POST /api/v1/employees/bulk-import`**
- Description: Import employees from Excel/CSV
- Auth: HR Manager, Super Admin
- Request: `multipart/form-data` with file
- Response: `{ "total": 50, "success": 48, "errors": [{"row": 3, "error": "email exists"}] }`

---

**`GET /api/v1/employees/{employee_id}/org-chart`**
- Description: Get org chart subtree rooted at employee
- Auth: All authenticated users
- Response: Nested hierarchy JSON

---

**`GET /api/v1/employees/directory`**
- Description: Searchable employee directory (limited fields)
- Auth: All employees
- Query: `?q=ahmed` (fuzzy search via Elasticsearch)
- Response: `[{id, name, title, department, email, phone, photo_url}]`

---

### MODULE 2: Attendance

---

**`POST /api/v1/attendance/check-in`**
- Description: Employee check-in (mobile GPS or web)
- Auth: Employee (own)
- Request body:
```json
{
  "latitude": 24.8607,
  "longitude": 67.0011,
  "source": "mobile_gps",
  "device_id": "device-abc-123"
}
```
- Response: `{ "status": "checked_in", "time": "2024-01-15T09:02:00Z", "late_minutes": 2 }`
- Error codes: `409 ALREADY_CHECKED_IN`, `403 OUTSIDE_GEOFENCE`

---

**`POST /api/v1/attendance/check-out`**
- Description: Employee check-out
- Auth: Employee (own)
- Response: `{ "status": "checked_out", "working_hours": 8.5, "overtime_hours": 0.5 }`

---

**`GET /api/v1/attendance`**
- Description: List attendance records with filters
- Auth: HR Manager (all), Manager (own team), Employee (own)
- Query: `employee_id`, `date_from`, `date_to`, `status`
- Response: Paginated attendance list

---

**`GET /api/v1/attendance/live`**
- Description: WebSocket endpoint — real-time attendance dashboard
- Auth: HR Manager, Super Admin
- Protocol: `WSS /ws/attendance?token=jwt_token`
- Messages: `{ "event": "check_in", "employee_id": "uuid", "time": "ISO8601", "employee_name": "..." }`

---

**`GET /api/v1/attendance/monthly-report`**
- Description: Monthly attendance summary per employee
- Auth: HR Manager, Manager (own team)
- Query: `month=2024-01&department_id=uuid`
- Response: Summary with present days, absent, overtime, late counts

---

**`PATCH /api/v1/attendance/{record_id}/override`**
- Description: HR manual override of attendance record
- Auth: HR Manager
- Request body: `{ "status": "present", "check_in_time": "09:00", "reason": "System error" }`
- Audit log: Recorded with override flag

---

### MODULE 3: Payroll

---

**`POST /api/v1/payroll/runs`**
- Description: Initiate new payroll run (async — Celery task)
- Auth: HR Manager
- Permission: `payroll:run`
- Request body:
```json
{
  "pay_period_start": "2024-01-01",
  "pay_period_end": "2024-01-31",
  "payment_date": "2024-02-05",
  "department_ids": [],
  "include_all": true
}
```
- Response: `202 Accepted` — `{ "task_id": "celery-task-uuid", "status_url": "/api/v1/payroll/runs/task/uuid" }`

---

**`GET /api/v1/payroll/runs`**
- Description: List all payroll runs
- Auth: HR Manager, Finance, CEO
- Response: Paginated list with status, totals

---

**`GET /api/v1/payroll/runs/{run_id}`**
- Description: Get payroll run details including all records
- Auth: HR Manager, Finance, CEO

---

**`POST /api/v1/payroll/runs/{run_id}/approve`**
- Description: Approve payroll at current stage (HR → Finance → CEO)
- Auth: Depends on current stage
- Request body: `{ "action": "approve", "comments": "Reviewed and approved" }`
- Response: Updated run status

---

**`GET /api/v1/payroll/runs/{run_id}/payslips/{employee_id}`**
- Description: Get payslip PDF for specific employee
- Auth: Employee (own), HR, Finance
- Response: PDF file or signed S3 URL

---

**`POST /api/v1/payroll/runs/{run_id}/bank-file`**
- Description: Generate IBFT bank transfer file
- Auth: Finance only
- Response: Download URL for bank file

---

**`GET /api/v1/payroll/employees/{employee_id}/history`**
- Description: Salary history for employee
- Auth: Employee (own — no absolute amounts), HR Manager (full), Finance (full)

---

### MODULE 4: Recruitment (ATS)

---

**`POST /api/v1/recruitment/postings`**
- Description: Create job posting
- Auth: HR Manager, Recruiter
- Request body: Full job posting object
- Response: Created posting with ID

---

**`GET /api/v1/recruitment/postings`**
- Description: List job postings
- Auth: HR Manager, Recruiter (all) | Employees (internal open positions)
- Query: `status=open&department_id=uuid`

---

**`POST /api/v1/recruitment/postings/{posting_id}/applications`**
- Description: Submit job application (candidate or internal)
- Auth: Public (external candidates via API key) | Employees (internal)
- Request: `multipart/form-data` with cv_file + JSON fields

---

**`GET /api/v1/recruitment/postings/{posting_id}/applications`**
- Description: Get all applications for a posting
- Auth: HR Manager, Recruiter, Hiring Manager
- Query: `stage=screened&sort_by=ai_score&sort_order=desc`

---

**`POST /api/v1/recruitment/applications/{app_id}/score`**
- Description: Trigger AI CV scoring for application
- Auth: HR Manager, Recruiter
- Response: `{ "task_id": "uuid" }` (async Celery task)

---

**`PATCH /api/v1/recruitment/applications/{app_id}/stage`**
- Description: Move application to next stage
- Auth: HR Manager, Recruiter, Hiring Manager
- Request: `{ "stage": "interview_scheduled", "notes": "...", "scheduled_date": "..." }`

---

**`POST /api/v1/recruitment/applications/{app_id}/offer`**
- Description: Generate and send offer letter
- Auth: HR Manager
- Request: `{ "offer_amount": 150000, "start_date": "2024-02-01", "template_id": "uuid" }`
- Response: PDF URL + email sent confirmation

---

### MODULE 5: Leave Management

---

**`POST /api/v1/leave/requests`**
- Description: Apply for leave
- Auth: Any employee (own)
- Request body:
```json
{
  "leave_type_id": "uuid",
  "start_date": "2024-01-20",
  "end_date": "2024-01-22",
  "reason": "Family trip",
  "is_half_day": false
}
```
- Validation: Check balance, check conflicts, check blackout dates
- Response: Created leave request with status

---

**`GET /api/v1/leave/requests`**
- Description: List leave requests
- Auth: Employee (own) | Manager (own team) | HR (all)
- Query: `status=pending&employee_id=uuid&month=2024-01`

---

**`POST /api/v1/leave/requests/{request_id}/action`**
- Description: Approve or reject leave request
- Auth: Manager (first approval), HR (second approval)
- Request: `{ "action": "approve", "comments": "Approved" }`

---

**`GET /api/v1/leave/balances/{employee_id}`**
- Description: Get leave balance summary for employee
- Auth: Employee (own), Manager, HR
- Response:
```json
{
  "year": 2024,
  "balances": [
    { "type": "Annual Leave", "code": "AL", "entitled": 20, "taken": 5, "pending": 2, "balance": 13 }
  ]
}
```

---

**`GET /api/v1/leave/calendar`**
- Description: Team leave calendar with conflict view
- Auth: Manager, HR
- Query: `team_id=uuid&month=2024-01`

---

### MODULE 6: Performance Management

---

**`POST /api/v1/performance/cycles`**
- Description: Create review cycle
- Auth: HR Manager
- Request: Full review cycle config object

---

**`POST /api/v1/performance/goals`**
- Description: Set KPI/OKR goals for employee
- Auth: Employee (own), Manager (for team)
- Request: `{ "review_cycle_id": "uuid", "goals": [{ "title": "...", "target_value": 100, ... }] }`

---

**`POST /api/v1/performance/reviews`**
- Description: Submit performance review
- Auth: Reviewer (self/manager/peer as appropriate)
- Request: Full review with ratings and competency scores

---

**`GET /api/v1/performance/employees/{employee_id}/history`**
- Description: Full performance history for employee
- Auth: Employee (own), Manager, HR

---

**`GET /api/v1/performance/analytics/bell-curve`**
- Description: Bell curve distribution for current cycle
- Auth: HR Manager
- Query: `cycle_id=uuid&department_id=uuid`

---

### MODULE 7: Training

---

**`GET /api/v1/training/programs`**
- Description: Training catalog
- Auth: All authenticated
- Query: `category=technical&is_mandatory=true`

---

**`POST /api/v1/training/enrollments`**
- Description: Enroll employee in training program
- Auth: Employee (self), Manager (team), HR (any)

---

**`POST /api/v1/training/enrollments/{id}/complete`**
- Description: Mark training complete, generate certificate
- Auth: HR Manager, Training Admin
- Response: Certificate PDF URL

---

**`GET /api/v1/training/skill-matrix/{employee_id}`**
- Description: Current vs required skills for employee
- Auth: Employee (own), Manager, HR

---

### MODULE 8: Self-Service

---

**`GET /api/v1/self-service/dashboard`**
- Description: Employee dashboard — balances, upcoming, announcements
- Auth: Employee

---

**`POST /api/v1/self-service/requests`**
- Description: Raise internal request (IT, HR, Admin, Finance)
- Auth: Employee
- Request: `{ "type": "it_request", "title": "Laptop replacement", "description": "...", "priority": "medium" }`

---

**`GET /api/v1/self-service/payslips`**
- Description: Employee's own payslip history
- Auth: Employee (own only)

---

**`POST /api/v1/self-service/letters`**
- Description: Request HR letter (employment, salary, experience)
- Auth: Employee
- Request: `{ "letter_type": "salary_certificate", "purpose": "bank_loan" }`
- Response: Generated PDF URL within 30 seconds (or webhook)

---

### MODULE 9: Assets

---

**`POST /api/v1/assets`**
- Description: Add new asset to register
- Auth: IT Admin, Super Admin

---

**`POST /api/v1/assets/{asset_id}/assign`**
- Description: Assign asset to employee
- Auth: IT Admin, HR
- Request: `{ "employee_id": "uuid", "condition": "good", "notes": "..." }`

---

**`POST /api/v1/assets/{asset_id}/return`**
- Description: Process asset return
- Auth: IT Admin, HR
- Request: `{ "condition": "fair", "damage_notes": "Screen scratch" }`

---

### MODULE 10: Offboarding

---

**`POST /api/v1/offboarding/initiate`**
- Description: Start offboarding workflow for employee
- Auth: HR Manager
- Request: `{ "employee_id": "uuid", "resignation_date": "...", "last_working_date": "...", "reason": "..." }`

---

**`GET /api/v1/offboarding/{offboarding_id}/checklist`**
- Description: Get clearance checklist with completion status
- Auth: HR, Dept Managers, IT, Finance (own tasks)

---

**`PATCH /api/v1/offboarding/{offboarding_id}/checklist/{task_id}`**
- Description: Mark clearance task complete
- Auth: Assigned department head

---

**`POST /api/v1/offboarding/{offboarding_id}/settlement`**
- Description: Calculate final settlement (async)
- Auth: Finance Manager

---

### MODULE 11: Compliance

---

**`GET /api/v1/compliance/audit-logs`**
- Description: Query audit logs with filters
- Auth: Super Admin only
- Query: `resource_type=employee&user_id=uuid&date_from=...&date_to=...`

---

**`POST /api/v1/compliance/data-erasure-request`**
- Description: GDPR right-to-erasure request
- Auth: Super Admin, Data Protection Officer
- Request: `{ "employee_id": "uuid", "reason": "employee_request", "scheduled_date": "..." }`

---

**`GET /api/v1/compliance/reports/regulatory`**
- Description: Generate EOBI/SESSI/Tax regulatory reports
- Auth: Finance, HR Manager
- Query: `type=eobi&period=2024-01`

---

### MODULE 12: Notifications

---

**`GET /api/v1/notifications`**
- Description: Get notifications for current user
- Auth: All authenticated
- Query: `unread_only=true&channel=in_app`

---

**`PATCH /api/v1/notifications/{id}/read`**
- Description: Mark notification as read
- Auth: Recipient only

---

**`PATCH /api/v1/notifications/preferences`**
- Description: Update notification preferences
- Auth: Employee (own)
- Request: `{ "email_enabled": true, "sms_enabled": false, "whatsapp_enabled": true }`

---

### MODULE 13: Analytics

---

**`GET /api/v1/analytics/headcount`**
- Description: Headcount by department with trend
- Auth: HR Manager, Super Admin, Dept Manager (own)
- Query: `date_from=2023-01&date_to=2024-01&group_by=department`

---

**`GET /api/v1/analytics/attrition`**
- Description: Attrition rate by period, department
- Auth: HR Manager, Super Admin

---

**`POST /api/v1/analytics/query`**
- Description: Natural language query → auto chart
- Auth: HR Manager, Super Admin
- Request: `{ "query": "Show me attrition by department in Q3 2024" }`
- Response: `{ "chart_type": "bar", "data": [...], "sql_generated": "...", "explanation": "..." }`

---

**`POST /api/v1/analytics/reports/schedule`**
- Description: Schedule automated report delivery
- Auth: HR Manager
- Request: `{ "report_type": "headcount", "frequency": "monthly", "recipients": ["email@..."], "format": "excel" }`

---

### MODULE 14: AI Endpoints

---

**`POST /api/v1/ai/cv-score`**
- Description: Score CV against job description
- Auth: HR Manager, Recruiter
- Request: `{ "application_id": "uuid" }`
- Response: `{ "score": 84, "breakdown": {...}, "explanation": "...", "bias_flags": [] }`

---

**`GET /api/v1/ai/attrition-risk`**
- Description: Get attrition risk scores for employees
- Auth: HR Manager
- Query: `department_id=uuid&risk_tier=high`

---

**`POST /api/v1/ai/chatbot/query`**
- Description: HR chatbot query
- Auth: All authenticated
- Request: `{ "message": "How many annual leaves do I have?", "session_id": "uuid" }`
- Response: `{ "response": "You have 13 annual leave days remaining...", "actions": [...], "escalated": false }`

---

**`GET /api/v1/ai/performance-prediction/{employee_id}`**
- Description: Get performance prediction for next cycle
- Auth: HR Manager, Dept Manager (own team)
- Response: `{ "predicted_band": "High", "confidence": 0.78, "factors": [...] }`

---

## 3.3 Error Code Reference

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or expired JWT |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VALIDATION_ERROR` | 422 | Request body fails Pydantic validation |
| `EMAIL_EXISTS` | 409 | Duplicate email in tenant |
| `LEAVE_BALANCE_INSUFFICIENT` | 400 | Not enough leave balance |
| `LEAVE_CONFLICT` | 400 | Another approved leave overlaps |
| `BLACKOUT_DATE` | 400 | Leave blocked during blackout period |
| `PAYROLL_ALREADY_RUNNING` | 409 | Only one payroll run at a time |
| `GEOFENCE_VIOLATION` | 403 | Check-in outside allowed location |
| `BIOMETRIC_MISMATCH` | 401 | Biometric verification failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `AI_SERVICE_UNAVAILABLE` | 503 | AI model service down |
| `TENANT_LIMIT_EXCEEDED` | 402 | Employee count exceeds subscription |

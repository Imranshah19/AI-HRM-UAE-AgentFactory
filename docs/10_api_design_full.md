# SECTION 3 — API DESIGN (50+ Routes)

## 3.1 Conventions

- Base URL: `https://api.hrms.company.com/api/v1/`
- Auth: JWT Bearer token (15-min access token) on all routes except /auth/*
- Tenant: resolved from JWT claim `tenant_id` — never in URL or body
- Pagination: `?page=1&per_page=25` with `X-Total-Count` response header
- Rate limits annotated as `[RL: X/min]` per endpoint
- All responses wrap data: `{"success": true, "data": {...}, "meta": {...}}`
- Error format: `{"success": false, "error": {"code": "...", "message": "...", "details": [...]}}`

---

## 3.2 Authentication Module `/auth`

```
POST   /api/v1/auth/login
  Description : Authenticate user, return access + refresh token
  Auth        : None
  Rate Limit  : [RL: 10/min per IP]
  Request     : {"email": "str", "password": "str", "mfa_code": "str?"}
  Response    : {
    "access_token": "eyJ...", "token_type": "bearer",
    "expires_in": 900,
    "user": {"id": "uuid", "email": "str", "role": "str", "tenant_id": "uuid"}
  }
  Errors      : 401 INVALID_CREDENTIALS, 403 MFA_REQUIRED, 429 RATE_LIMIT_EXCEEDED,
                423 ACCOUNT_LOCKED

POST   /api/v1/auth/refresh
  Description : Exchange refresh token for new access token
  Auth        : httpOnly cookie (refresh_token)
  Rate Limit  : [RL: 20/min per user]
  Request     : {} (token from cookie)
  Response    : {"access_token": "eyJ...", "expires_in": 900}
  Errors      : 401 TOKEN_EXPIRED, 401 TOKEN_INVALID

POST   /api/v1/auth/logout
  Description : Revoke refresh token, clear cookie
  Auth        : Bearer
  Rate Limit  : [RL: 10/min per user]
  Response    : {"success": true, "message": "Logged out"}

POST   /api/v1/auth/mfa/setup
  Description : Generate TOTP secret + QR code for Google Authenticator
  Auth        : Bearer
  Response    : {"qr_code_url": "data:image/png;base64,...", "secret": "BASE32SECRET"}

POST   /api/v1/auth/mfa/verify
  Description : Verify TOTP code and activate MFA
  Auth        : Bearer
  Request     : {"code": "123456"}
  Response    : {"success": true, "backup_codes": ["...", ...]}

POST   /api/v1/auth/password/change
  Description : Change own password
  Auth        : Bearer
  Rate Limit  : [RL: 5/min per user]
  Request     : {"current_password": "str", "new_password": "str"}
  Errors      : 400 WEAK_PASSWORD, 401 CURRENT_PASSWORD_WRONG

POST   /api/v1/auth/password/reset-request
  Description : Send password reset email
  Auth        : None
  Rate Limit  : [RL: 5/min per IP]
  Request     : {"email": "str"}
  Response    : {"message": "Reset link sent if email exists"}

POST   /api/v1/auth/password/reset-confirm
  Description : Reset password with token from email
  Auth        : None
  Request     : {"token": "str", "new_password": "str"}
  Errors      : 400 TOKEN_EXPIRED, 400 TOKEN_INVALID
```

---

## 3.3 Employee Module `/employees`

```
GET    /api/v1/employees
  Description : List all employees with filters, search, pagination
  Auth        : Bearer | Roles: HR_MANAGER, ADMIN, DEPT_MANAGER (own dept)
  Rate Limit  : [RL: 100/min]
  Query Params: ?search=str&department_id=uuid&branch_id=uuid&status=str
                &contract_type=str&page=1&per_page=25&sort=full_name&order=asc
  Response    : {
    "data": [{"id": "uuid", "employee_number": "str", "full_name": "str",
              "designation": "str", "department": {...}, "status": "str",
              "joining_date": "date", "avatar_url": "str?"}],
    "meta": {"total": 245, "page": 1, "per_page": 25, "pages": 10}
  }

POST   /api/v1/employees
  Description : Create new employee (multi-step form final submit)
  Auth        : Bearer | Roles: HR_MANAGER, ADMIN
  Rate Limit  : [RL: 20/min]
  Request     : {full AddEmployee payload — all 5 form steps merged}
  Response    : {
    "data": {
      "id": "uuid", "employee_number": "EMP-0042",
      "work_email": "ahmed@company.com",
      "onboarding_checklist_id": "uuid",
      "welcome_email_sent": true
    }
  }
  Errors      : 409 EMPLOYEE_NUMBER_EXISTS, 409 EMAIL_EXISTS,
                422 VALIDATION_ERROR, 403 PERMISSION_DENIED

GET    /api/v1/employees/{employee_id}
  Description : Get full employee profile (field-level RBAC applied)
  Auth        : Bearer | Own profile or HR_MANAGER+
  Rate Limit  : [RL: 200/min]
  Response    : {Full employee object — salary fields masked unless Finance/HR}

PATCH  /api/v1/employees/{employee_id}
  Description : Partial update employee (audited — every change logged)
  Auth        : Bearer | HR_MANAGER+ or employee (restricted fields only)
  Rate Limit  : [RL: 50/min]
  Request     : {partial fields to update}
  Response    : {updated employee object}
  Errors      : 403 FIELD_UPDATE_FORBIDDEN, 409 CONCURRENT_EDIT_CONFLICT

DELETE /api/v1/employees/{employee_id}
  Description : Soft-delete employee (sets deleted_at, triggers offboarding)
  Auth        : Bearer | Roles: ADMIN only
  Rate Limit  : [RL: 5/min]
  Errors      : 400 ACTIVE_PAYROLL_RUN_EXISTS, 400 PENDING_APPROVALS

GET    /api/v1/employees/{employee_id}/compensation
  Description : Get salary history (current + previous revisions)
  Auth        : Bearer | FINANCE, HR_MANAGER, ADMIN (employee sees limited)
  Rate Limit  : [RL: 50/min]
  Response    : {current_compensation: {...}, history: [...]}

POST   /api/v1/employees/{employee_id}/compensation
  Description : Create new compensation revision (triggers approval workflow)
  Auth        : Bearer | Roles: HR_MANAGER, ADMIN
  Rate Limit  : [RL: 20/min]
  Request     : {salary structure, effective_date, revision_reason}

GET    /api/v1/employees/{employee_id}/documents
  Description : List employee documents with expiry status
  Auth        : Bearer | HR_MANAGER+ or own documents
  Rate Limit  : [RL: 100/min]

POST   /api/v1/employees/{employee_id}/documents
  Description : Upload employee document (multipart/form-data)
  Auth        : Bearer | HR_MANAGER+ or employee (own non-sensitive docs)
  Rate Limit  : [RL: 20/min]
  Request     : multipart: {doc_type, file, expiry_date?, doc_name}
  Response    : {doc_id, file_url, upload_status}

POST   /api/v1/employees/bulk-import
  Description : Bulk import employees from CSV/Excel
  Auth        : Bearer | Roles: HR_MANAGER, ADMIN
  Rate Limit  : [RL: 2/min — slow endpoint]
  Request     : multipart: {file, mapping_config}
  Response    : {
    "job_id": "celery-task-uuid",
    "status": "processing",
    "message": "Import started. You will be notified on completion."
  }

GET    /api/v1/employees/bulk-import/{job_id}/status
  Description : Poll import job status
  Auth        : Bearer
  Response    : {status, processed, success_count, error_count, errors: [...]}

GET    /api/v1/employees/org-chart
  Description : Get org chart data (hierarchical)
  Auth        : Bearer | All roles (filtered by visibility)
  Rate Limit  : [RL: 100/min]
  Query Params: ?root_id=uuid&depth=3
  Response    : {tree: [{employee, children: [...]}, ...]}
```

---

## 3.4 Attendance Module `/attendance`

```
POST   /api/v1/attendance/checkin
  Description : Employee check-in (manual, geo, or biometric)
  Auth        : Bearer
  Rate Limit  : [RL: 5/min per user — prevent double punch]
  Request     : {
    "method": "geo_fence|manual|biometric",
    "latitude": 24.8607, "longitude": 67.0011,
    "device_id": "str?", "photo_base64": "str?"
  }
  Response    : {
    "attendance_id": "uuid", "check_in_time": "ISO8601",
    "geofence_status": "within|outside", "shift_expected_start": "08:00"
  }
  Errors      : 409 ALREADY_CHECKED_IN, 403 OUTSIDE_GEOFENCE, 400 INVALID_LOCATION

POST   /api/v1/attendance/checkout
  Description : Employee check-out
  Auth        : Bearer
  Rate Limit  : [RL: 5/min per user]
  Request     : {"latitude": 24.8607, "longitude": 67.0011, "method": "str"}
  Response    : {
    "check_out_time": "ISO8601", "total_hours": 8.5,
    "overtime_minutes": 30, "early_leave_minutes": 0
  }
  Errors      : 409 NOT_CHECKED_IN

GET    /api/v1/attendance
  Description : Get attendance records with filters
  Auth        : Bearer | HR_MANAGER+ (all), DEPT_MANAGER (own dept), EMPLOYEE (own)
  Rate Limit  : [RL: 100/min]
  Query Params: ?employee_id=uuid&from=2024-01-01&to=2024-01-31
                &status=present|absent|late&department_id=uuid&page=1

GET    /api/v1/attendance/live
  Description : Current day live attendance status (REST snapshot)
  Auth        : Bearer | HR_MANAGER+
  Rate Limit  : [RL: 60/min]
  Response    : {
    "date": "2024-01-15",
    "total_employees": 245,
    "present": 198, "absent": 22, "late": 15, "on_leave": 10,
    "live_data": [{employee_id, name, status, check_in_time}]
  }

PATCH  /api/v1/attendance/{record_id}/regularize
  Description : HR override/regularize attendance record
  Auth        : Bearer | Roles: HR_MANAGER, ADMIN
  Rate Limit  : [RL: 50/min]
  Request     : {"reason": "str", "check_in_time": "ISO8601?", "check_out_time": "ISO8601?", "status": "str?"}

GET    /api/v1/attendance/report/monthly
  Description : Monthly attendance summary by department
  Auth        : Bearer | HR_MANAGER+
  Rate Limit  : [RL: 20/min]
  Query Params: ?month=2024-01&department_id=uuid?&export=pdf|excel

WebSocket WS /ws/attendance
  Description : Real-time attendance feed (see Bonus 3c)
  Auth        : JWT token in query param ?token=...
  Events      : employee_checked_in, employee_checked_out, attendance_override
```

---

## 3.5 Payroll Module `/payroll`

```
GET    /api/v1/payroll/runs
  Description : List all payroll runs
  Auth        : Bearer | Roles: HR_MANAGER, FINANCE, ADMIN
  Rate Limit  : [RL: 60/min]
  Query Params: ?year=2024&month=1&status=approved&page=1

POST   /api/v1/payroll/runs
  Description : Create new payroll run (triggers Celery task)
  Auth        : Bearer | Roles: HR_MANAGER, ADMIN
  Rate Limit  : [RL: 1/hour — prevent duplicate runs]
  Request     : {
    "period_month": 1, "period_year": 2024,
    "scope_type": "all|department|branch",
    "scope_department_id": "uuid?",
    "notes": "str?"
  }
  Response    : {
    "run_id": "uuid", "job_id": "celery-uuid",
    "status": "processing", "estimated_employee_count": 245
  }
  Errors      : 409 RUN_ALREADY_EXISTS_FOR_PERIOD, 400 EMPLOYEES_ON_HOLD

GET    /api/v1/payroll/runs/{run_id}
  Description : Get payroll run detail with employee breakdown
  Auth        : Bearer | HR_MANAGER, FINANCE, ADMIN
  Rate Limit  : [RL: 100/min]

POST   /api/v1/payroll/runs/{run_id}/approve
  Description : Approve payroll run (stage-gated: HR → Finance → CEO)
  Auth        : Bearer | Roles: HR_MANAGER (stage 1), FINANCE (stage 2), ADMIN/CEO (stage 3)
  Rate Limit  : [RL: 10/min]
  Request     : {"action": "approve|reject", "comments": "str?"}
  Errors      : 403 WRONG_APPROVAL_STAGE, 400 ALREADY_APPROVED

GET    /api/v1/payroll/runs/{run_id}/bank-file
  Description : Download IBFT/BACS/ACH bank export file
  Auth        : Bearer | Roles: FINANCE, ADMIN
  Rate Limit  : [RL: 5/min]
  Response    : File download (text/plain or application/zip)

GET    /api/v1/payroll/{employee_id}/payslips
  Description : List payslips for employee
  Auth        : Bearer | HR_MANAGER+ or own payslips
  Rate Limit  : [RL: 100/min]

GET    /api/v1/payroll/{employee_id}/payslips/{run_id}
  Description : Get/download specific payslip PDF
  Auth        : Bearer | HR_MANAGER+ or own payslip
  Rate Limit  : [RL: 60/min]
  Response    : PDF file or JSON with payslip_pdf_url

GET    /api/v1/payroll/tax-certificates/{employee_id}/{year}
  Description : Generate/download year-end tax certificate
  Auth        : Bearer | HR_MANAGER+ or own certificate
  Rate Limit  : [RL: 20/min]
```

---

## 3.6 Recruitment Module `/recruitment`

```
GET    /api/v1/recruitment/jobs
  Description : List job postings (filterable)
  Auth        : Bearer | All authenticated (internal); public endpoint for external
  Rate Limit  : [RL: 100/min]
  Query Params: ?status=open&department_id=uuid&search=str&page=1

POST   /api/v1/recruitment/jobs
  Description : Create job posting
  Auth        : Bearer | Roles: HR_MANAGER, RECRUITER, ADMIN
  Rate Limit  : [RL: 20/min]

PATCH  /api/v1/recruitment/jobs/{job_id}
  Description : Update job posting (publish, pause, close)
  Auth        : Bearer | Roles: HR_MANAGER, RECRUITER (own jobs)
  Rate Limit  : [RL: 30/min]

GET    /api/v1/recruitment/jobs/{job_id}/applications
  Description : Get application pipeline for a job (Kanban data)
  Auth        : Bearer | Roles: HR_MANAGER, RECRUITER, DEPT_MANAGER
  Rate Limit  : [RL: 100/min]

POST   /api/v1/recruitment/applications
  Description : Submit job application (internal or external candidate)
  Auth        : None (public) or Bearer
  Rate Limit  : [RL: 10/min per IP — prevent spam]
  Request     : {candidate info + cv file multipart}

GET    /api/v1/recruitment/applications/{application_id}
  Description : Get full candidate profile + AI score
  Auth        : Bearer | HR_MANAGER, RECRUITER
  Rate Limit  : [RL: 100/min]

PATCH  /api/v1/recruitment/applications/{application_id}/stage
  Description : Move application to new pipeline stage
  Auth        : Bearer | HR_MANAGER, RECRUITER
  Rate Limit  : [RL: 50/min]
  Request     : {"stage": "screening|interview_1|offered|hired|rejected", "reason": "str?"}

POST   /api/v1/recruitment/applications/{application_id}/ai-score
  Description : Trigger AI CV scoring (async — returns job_id)
  Auth        : Bearer | HR_MANAGER, RECRUITER
  Rate Limit  : [RL: 20/min]
  Response    : {"job_id": "celery-uuid", "status": "processing"}

GET    /api/v1/recruitment/applications/{application_id}/ai-score
  Description : Get AI score result + explanation
  Auth        : Bearer | HR_MANAGER, RECRUITER
  Rate Limit  : [RL: 100/min]

POST   /api/v1/recruitment/interviews
  Description : Schedule interview for application
  Auth        : Bearer | HR_MANAGER, RECRUITER
  Rate Limit  : [RL: 30/min]
  Request     : {
    "application_id": "uuid", "interviewers": ["uuid"],
    "scheduled_at": "ISO8601", "duration_minutes": 60,
    "type": "video|phone|in_person", "location": "str?",
    "send_calendar_invite": true
  }
```

---

## 3.7 Leave Module `/leave`

```
GET    /api/v1/leave/types
  Description : List all leave types for tenant
  Auth        : Bearer | All roles
  Rate Limit  : [RL: 100/min]

GET    /api/v1/leave/balance/{employee_id}
  Description : Get leave balances for all leave types
  Auth        : Bearer | Own or HR_MANAGER+
  Rate Limit  : [RL: 100/min]
  Query Params: ?year=2024
  Response    : [
    {"leave_type": "Annual", "allocated": 20, "used": 8, "pending": 2, "remaining": 10,
     "carry_forward": 5, "encashable": 3}
  ]

GET    /api/v1/leave/requests
  Description : List leave requests (HR sees all, manager sees team, employee sees own)
  Auth        : Bearer | RBAC filtered
  Rate Limit  : [RL: 100/min]
  Query Params: ?status=pending&employee_id=uuid&from=date&to=date&page=1

POST   /api/v1/leave/requests
  Description : Submit leave request
  Auth        : Bearer | All employees
  Rate Limit  : [RL: 10/min per user]
  Request     : {
    "leave_type_id": "uuid", "start_date": "2024-01-20",
    "end_date": "2024-01-22", "reason": "str",
    "is_half_day": false, "document": "file?"
  }
  Response    : {request_id, status, total_days, balance_remaining}
  Errors      : 400 INSUFFICIENT_BALANCE, 400 BLACKOUT_DATE, 400 CONFLICT_WITH_TEAM,
                400 BELOW_MIN_SERVICE_DAYS

POST   /api/v1/leave/requests/{request_id}/action
  Description : Manager/HR approve or reject leave request
  Auth        : Bearer | Roles by stage (Manager → HR)
  Rate Limit  : [RL: 50/min]
  Request     : {"action": "approve|reject", "comments": "str?"}

DELETE /api/v1/leave/requests/{request_id}
  Description : Cancel leave request (employee own, if still pending)
  Auth        : Bearer | Own leave only
  Rate Limit  : [RL: 10/min]
  Errors      : 400 LEAVE_ALREADY_STARTED, 400 LEAVE_APPROVED_CONTACT_HR

GET    /api/v1/leave/calendar
  Description : Team leave calendar for conflict detection
  Auth        : Bearer | All (own team visible)
  Rate Limit  : [RL: 100/min]
  Query Params: ?month=2024-01&department_id=uuid

GET    /api/v1/leave/public-holidays
  Description : Get public holidays for location/year
  Auth        : Bearer | All
  Rate Limit  : [RL: 100/min]
  Query Params: ?year=2024&country=Pakistan&branch_id=uuid?
```

---

## 3.8 Performance Module `/performance`

```
GET    /api/v1/performance/cycles
  Auth: HR_MANAGER+  | List appraisal cycles
POST   /api/v1/performance/cycles
  Auth: HR_MANAGER+  | Create new appraisal cycle
GET    /api/v1/performance/cycles/{cycle_id}
  Auth: All          | Get cycle progress summary
PATCH  /api/v1/performance/cycles/{cycle_id}/advance
  Auth: HR_MANAGER+  | Move cycle to next stage

GET    /api/v1/performance/goals/{employee_id}
  Auth: Own or manager+ | Get goals for employee in current cycle
POST   /api/v1/performance/goals
  Auth: Employee (own), Manager (team), HR  | Create goal
PATCH  /api/v1/performance/goals/{goal_id}
  Auth: Goal owner or manager  | Update goal progress

GET    /api/v1/performance/reviews/{employee_id}
  Auth: Own, reviewer, HR_MANAGER+ (with field masking)
POST   /api/v1/performance/reviews
  Auth: Self/Manager/Peer (by review type)  | Submit review
PATCH  /api/v1/performance/reviews/{review_id}/acknowledge
  Auth: Employee (own review)  | Acknowledge final review

GET    /api/v1/performance/pips
  Auth: HR_MANAGER+  | List all active PIPs
POST   /api/v1/performance/pips
  Auth: HR_MANAGER+  | Create PIP for employee
PATCH  /api/v1/performance/pips/{pip_id}/milestone
  Auth: Manager, HR  | Update milestone status

GET    /api/v1/performance/predictions/{employee_id}
  Auth: HR_MANAGER+  | Get AI performance prediction
```

---

## 3.9 Notifications & System

```
GET    /api/v1/notifications
  Description : Get in-app notifications for current user
  Auth        : Bearer | Own notifications
  Rate Limit  : [RL: 120/min]
  Query Params: ?unread=true&page=1&per_page=20
  Response    : {notifications: [...], unread_count: 5}

PATCH  /api/v1/notifications/{notification_id}/read
  Auth        : Bearer | Own
  Rate Limit  : [RL: 120/min]

PATCH  /api/v1/notifications/read-all
  Auth        : Bearer | Own
  Rate Limit  : [RL: 30/min]

GET    /api/v1/notifications/preferences
  Auth        : Bearer | Own
  Response    : {email: true, sms: false, push: true, whatsapp: false, ...per event type}

PATCH  /api/v1/notifications/preferences
  Auth        : Bearer | Own
  Request     : {channel preferences per event type}

GET    /api/v1/system/health
  Description : Service health check
  Auth        : None
  Rate Limit  : [RL: unlimited]
  Response    : {"status": "ok", "db": "ok", "redis": "ok", "version": "1.2.3"}

GET    /api/v1/admin/audit-logs
  Auth        : Bearer | ADMIN only
  Rate Limit  : [RL: 30/min]
  Query Params: ?actor_id=uuid&resource_type=str&from=date&to=date&action=str

GET    /api/v1/admin/feature-flags
  Auth        : Bearer | ADMIN only
  Rate Limit  : [RL: 60/min]

PATCH  /api/v1/admin/feature-flags/{flag_key}
  Auth        : Bearer | ADMIN only  | Toggle or update feature flag
  Request     : {"is_enabled": true, "rollout_percentage": 50.0, ...}
```

---

## 3.10 AI Endpoints

```
POST   /api/v1/ai/cv-score
  Description : Score CV against job description (async)
  Auth        : Bearer | HR_MANAGER, RECRUITER
  Rate Limit  : [RL: 30/min]
  Request     : {"application_id": "uuid", "job_id": "uuid"}
  Response    : {"job_id": "celery-uuid", "eta_seconds": 15}

GET    /api/v1/ai/cv-score/{job_id}
  Description : Get CV score result
  Auth        : Bearer
  Rate Limit  : [RL: 100/min]
  Response    : See Bonus 5 cv_score_result JSON

POST   /api/v1/ai/attrition-risk
  Description : Calculate attrition risk for employee(s)
  Auth        : Bearer | HR_MANAGER, ADMIN
  Rate Limit  : [RL: 10/min]
  Request     : {"employee_ids": ["uuid"], "force_refresh": false}

GET    /api/v1/ai/attrition-risk/{employee_id}
  Auth        : Bearer | HR_MANAGER, ADMIN
  Rate Limit  : [RL: 60/min]
  Response    : See Bonus 5 attrition_risk JSON

POST   /api/v1/ai/chatbot/query
  Description : HR chatbot query (RAG)
  Auth        : Bearer | All employees
  Rate Limit  : [RL: 30/min per user]
  Request     : {"query": "What is the leave policy?", "session_id": "uuid?"}
  Response    : {
    "answer": "According to HR Policy v3.2, annual leave entitlement...",
    "sources": [{"document": "Leave Policy 2024.pdf", "page": 3, "excerpt": "..."}],
    "session_id": "uuid",
    "escalated": false
  }

POST   /api/v1/ai/analytics/query
  Description : Natural language query → chart data
  Auth        : Bearer | HR_MANAGER, ADMIN
  Rate Limit  : [RL: 20/min]
  Request     : {"query": "Show attrition by department in Q3 2024"}
  Response    : {
    "chart_type": "bar",
    "title": "Attrition by Department — Q3 2024",
    "data": [...recharts-compatible dataset...],
    "sql_generated": "SELECT ...",
    "ai_notes": "Q3 shows Engineering dept highest at 12%"
  }
```

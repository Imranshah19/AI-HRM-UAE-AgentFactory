# Section 7: Workflow Diagrams

## Workflow 1: Monthly Payroll Run (End-to-End)

```
TRIGGER: HR Manager clicks "Run Payroll" on Dashboard
    │
    ▼
STEP 1: PAYROLL RUN INITIATION
    ├── HR selects pay period (2024-01-01 to 2024-01-31)
    ├── System validates: no active run exists for period
    ├── INSERT payroll_runs (status='processing')
    └── Celery task: process_payroll_run.delay(run_id)
                                │
                                ▼
STEP 2: DATA COLLECTION (Celery Worker — async)
    ├── Fetch all active employees for tenant
    ├── For each employee:
    │   ├── Get salary_structure (components, rates)
    │   ├── Get attendance_records (present_days, overtime_hours, late_minutes)
    │   ├── Get leave_records (leave_days by type, unpaid leave)
    │   ├── Get loan/advance balances (outstanding deductions)
    │   └── Get previous payroll for comparison
    │
    ▼
STEP 3: CALCULATION ENGINE
    For each employee:
    ├── Calculate gross:
    │   ├── Basic salary
    │   ├── + HRA (% of basic)
    │   ├── + Transport, Medical, Meal allowances (fixed)
    │   ├── + Overtime pay (overtime_hours × hourly_rate × multiplier)
    │   ├── + Performance bonus (if applicable this month)
    │   └── - Absent deduction (absent_days × daily_rate)
    │
    ├── Calculate deductions:
    │   ├── Income tax (apply slab from tenant tax config)
    │   ├── EOBI employee contribution (gross × 1%)
    │   ├── SESSI employee contribution (if applicable)
    │   ├── Loan deduction (monthly installment from loans table)
    │   ├── Advance recovery
    │   └── Late arrival deduction (late_minutes / 60 × hourly_rate)
    │
    ├── Net salary = Gross - Total Deductions
    ├── Store calculation_log (step-by-step audit trail)
    └── INSERT payroll_records for employee
    │
    ▼
STEP 4: TOTALS & VALIDATION
    ├── Sum all gross, deductions, net across all records
    ├── UPDATE payroll_runs (total_employees, total_gross, total_net)
    ├── Variance check: compare with last month (flag >20% individual change)
    └── UPDATE payroll_runs (status='pending_hr')
                                │
                                ▼
STEP 5: NOTIFICATIONS
    ├── Email to HR Manager: "Payroll run complete — 243 employees. PKR 12,450,000 net. Pending your review."
    ├── In-app notification to HR Manager
    └── Payroll approval task appears on HR dashboard
                                │
                                ▼
STEP 6: HR REVIEW & APPROVAL
    ├── HR Manager reviews:
    │   ├── Employee-wise breakdown table
    │   ├── Department totals
    │   ├── Variance highlights (red/yellow/green)
    │   └── Exception list (new joiners, resigned, salary changes)
    │
    ├── HR approves or sends back with comments
    │   ├── [APPROVED] → UPDATE status='pending_finance', notify Finance Manager
    │   └── [REJECTED] → UPDATE status='draft', notify Payroll Admin with comments
                                │
                                ▼
STEP 7: FINANCE REVIEW & APPROVAL
    ├── Finance Manager reviews totals and bank transfer breakdown
    ├── Approves or rejects
    └── [APPROVED] → UPDATE status='pending_ceo', notify CEO
                                │
                                ▼
STEP 8: CEO FINAL APPROVAL
    ├── CEO receives approval request (email + in-app)
    ├── Reviews executive summary (total headcount, total cost, variance)
    ├── [APPROVED] → UPDATE status='approved'
    └── Celery task: generate_payslips.delay(run_id)
                                │
                                ▼
STEP 9: PAYSLIP GENERATION (Celery Batch)
    ├── For each employee:
    │   ├── Render payslip HTML template with employee data
    │   ├── Generate PDF (WeasyPrint)
    │   ├── Apply digital signature (if configured)
    │   ├── Upload to S3: payslips/{tenant}/{year}/{month}/{employee_id}.pdf
    │   └── UPDATE payroll_records.payslip_url
    │
    └── Celery task: generate_bank_file.delay(run_id)
                                │
                                ▼
STEP 10: BANK FILE GENERATION
    ├── Fetch all employee bank account snapshots
    ├── Generate IBFT batch file (Pakistan format):
    │   format: DEBIT_ACCOUNT|EMPLOYEE_IBAN|AMOUNT|REFERENCE|NAME
    ├── Upload to S3 (restricted access)
    ├── UPDATE payroll_runs.bank_file_url
    └── UPDATE status='bank_file_generated'
                                │
                                ▼
STEP 11: EMPLOYEE NOTIFICATIONS
    ├── Celery task: notify_employees_payslip.delay(run_id)
    ├── For each employee:
    │   ├── Email: "Your payslip for January 2024 is ready"
    │   ├── In-app notification with download link
    │   └── WhatsApp (if configured): "Payslip ready — PKR {net_amount}"
    └── UPDATE status='paid' when transfers confirmed
```

---

## Workflow 2: Recruitment Pipeline (Job Post to Hire)

```
TRIGGER: HR Manager or Dept Manager requests new hire
    │
    ▼
STEP 1: JOB REQUISITION
    ├── Dept Manager: "Request New Hire" → fills requisition form
    │   (department, role, budget, justification, start date)
    ├── HR Manager reviews and approves requisition
    └── HR/Recruiter creates Job Posting from approved requisition
                                │
                                ▼
STEP 2: JOB POSTING CREATION
    ├── Recruiter fills: title, JD, requirements, salary range, locations
    ├── System generates JD embedding (async) → stores in job_postings.description_embedding
    ├── Configure: vacancies, hiring manager, referral bonus
    └── Select posting channels:
        ├── Internal portal (immediate)
        ├── LinkedIn (via API, requires business account)
        └── Indeed (via API)
                                │
                                ▼
STEP 3: APPLICATIONS INFLOW
    ├── External candidates: public apply page (no auth required)
    │   └── Upload CV → Tika text extraction → store in candidates table
    ├── Internal candidates: employee portal application
    ├── Referrals: employee uses "Refer a Friend" → link to specific job
    └── ATS stores all in job_applications (stage='applied')
                                │
                                ▼
STEP 4: AUTOMATED AI SCREENING
    ├── Celery task triggered per application: score_cv_task
    ├── CV parsed: skills, experience, education extracted
    ├── CV embedding generated → cosine similarity with JD embedding
    ├── Weighted score (0-100) computed
    ├── Bias detection check (anonymized re-scoring)
    └── Store ai_score, ai_score_breakdown, explanation
                                │
                                ▼
STEP 5: RECRUITER REVIEW & SHORTLISTING
    ├── Recruiter views pipeline sorted by AI score
    ├── Reviews AI explanation for each candidate
    ├── Can override AI score with manual rating (recorded)
    ├── Moves qualified candidates: stage='screened'
    └── Sends rejection emails to unqualified (templated, personalized)
                                │
                                ▼
STEP 6: PHONE/VIDEO SCREENING
    ├── Recruiter schedules phone screen
    │   └── Sends calendar invite via Google Calendar / Outlook API
    ├── Phone screen completed, recruiter adds notes
    └── Move to: 'phone_screen' → 'interview_scheduled' or 'rejected'
                                │
                                ▼
STEP 7: INTERVIEW SCHEDULING
    ├── Recruiter selects interviewers from employee directory
    ├── System checks interviewer availability (calendar API)
    ├── Creates interview: time, mode (in-person/virtual), room booking
    ├── Calendar invites sent to all participants + candidate
    └── Automated reminder (24h, 1h before)
                                │
                                ▼
STEP 8: INTERVIEW EVALUATION
    ├── Each interviewer submits structured evaluation:
    │   (competency ratings, recommendation: hire/no-hire/maybe)
    ├── Hiring manager consolidates feedback
    ├── Debrief meeting (if configured — triggers team calendar invite)
    └── Decision: move to 'offered' or 'rejected'
                                │
                                ▼
STEP 9: OFFER GENERATION
    ├── HR Manager creates offer:
    │   (salary, start date, designation, benefits, probation period)
    ├── Offer letter auto-generated from template (PDF via WeasyPrint)
    ├── Optional: Finance approval if offer exceeds grade salary band
    ├── Offer emailed to candidate with accept/decline link
    └── Offer expiry timer set (default: 7 days)
                                │
                                ▼
STEP 10: OFFER DECISION
    ├── [ACCEPTED] → stage='offer_accepted'
    │   ├── Trigger background check workflow (if configured)
    │   └── Schedule onboarding: trigger onboarding wizard
    └── [DECLINED / EXPIRED] → stage='offer_rejected'
        ├── HR decides: extend offer, revise, or go to next candidate
        └── If referral: update referral bonus status
                                │
                                ▼
STEP 11: PRE-ONBOARDING
    ├── Create employee record: stage='onboarding'
    ├── Send pre-onboarding form (personal details, documents upload)
    ├── IT: trigger laptop/access provisioning
    ├── Manager notified of new team member start date
    └── Onboarding buddy assigned (if policy configured)
                                │
                                ▼
STEP 12: ANALYTICS UPDATE
    ├── Update cost-per-hire (advertising cost / hires for this period)
    ├── Update time-to-hire (apply_date to offer_accepted_date)
    ├── Update source effectiveness report
    └── Referral bonus triggered in next payroll run
```

---

## Workflow 3: Leave Approval (Employee to HR)

```
TRIGGER: Employee applies for leave via self-service portal or mobile app
    │
    ▼
STEP 1: EMPLOYEE APPLIES
    ├── Selects leave type (Annual, Sick, Casual, etc.)
    ├── Selects date range
    ├── System real-time calculations:
    │   ├── Balance check: available_days ≥ requested_days?
    │   ├── Conflict check: any team member approved leave same dates?
    │   ├── Blackout check: dates in blackout period?
    │   └── Notice period check: applied ≥ required_notice_days in advance?
    │
    ├── [VALIDATION FAILED] → Error shown, employee corrects
    └── [VALIDATION PASSED] → Enters reason, submits
                                │
                                ▼
STEP 2: SYSTEM PROCESSING
    ├── INSERT leave_requests (status='pending')
    ├── UPDATE leave_balances (pending_days += requested_days)
    ├── INSERT audit_log
    └── Celery: notify_leave_pending.delay(request_id)
                                │
                                ▼
STEP 3: MANAGER NOTIFICATION
    ├── Email to Line Manager: "Ahmed Khan has applied for 3 days Annual Leave (Jan 20-22)"
    │   Contains: approve/reject buttons (magic link with JWT)
    ├── In-app notification on manager's dashboard
    └── Task appears in manager's "Pending Approvals" widget
                                │
                                ▼
STEP 4: MANAGER REVIEW
    ├── Manager views team leave calendar (conflict visualization)
    ├── Reviews pending requests with employee history
    │
    ├── [APPROVED BY MANAGER]
    │   ├── UPDATE leave_requests.manager_action='approved'
    │   ├── Status → 'approved_by_manager'
    │   └── Notify HR for second approval
    │
    └── [REJECTED BY MANAGER]
        ├── Manager provides reason (required)
        ├── UPDATE status='rejected'
        ├── UPDATE leave_balances (pending_days -= requested_days)
        └── Email employee: "Your leave request has been rejected. Reason: {reason}"
                                │
                                ▼
STEP 5: HR FINAL APPROVAL
    ├── HR receives notification
    ├── HR can:
    │   ├── Auto-approve (if policy: manager approval sufficient) → status='approved'
    │   └── Manual review and approve/reject
    │
    ├── [APPROVED BY HR]
    │   ├── UPDATE leave_requests.status='approved'
    │   ├── UPDATE leave_balances: pending_days-=n, taken_days+=n
    │   ├── Email employee: "Leave Approved"
    │   ├── Update team calendar
    │   └── For sick leave: log for monthly absenteeism report
    │
    └── [REJECTED BY HR] (rare)
        ├── UPDATE status='rejected'
        ├── UPDATE leave_balances (pending_days -= requested_days)
        └── Email employee with HR comment
                                │
                                ▼
STEP 6: RETURN FROM LEAVE
    ├── Attendance system marks employee absent during leave dates
    │   (auto-linked to leave_request, not counted as absent)
    ├── If sick leave >2 days: reminder to upload medical certificate
    └── If attendance after return date marked absent without leave:
        Celery alert task → HR notification
```

---

## Workflow 4: Employee Offboarding (Resignation to Final Settlement)

```
TRIGGER: Employee submits resignation OR HR initiates offboarding
    │
    ▼
STEP 1: RESIGNATION RECEIPT
    ├── Employee submits resignation via self-service (or email → HR manually records)
    ├── HR records:
    │   ├── resignation_date
    │   ├── notice_period (from contract, e.g., 30 days)
    │   └── last_working_date = resignation_date + notice_period
    │
    ├── INSERT offboarding_records
    ├── UPDATE employees.status = 'offboarding'
    └── Notify: Employee's manager, HR, IT, Finance
                                │
                                ▼
STEP 2: EXIT INTERVIEW
    ├── Automated email to employee: "Please complete your exit interview"
    ├── Digital exit interview form sent (structured questions):
    │   Reason for leaving, satisfaction scores, manager feedback,
    │   would you recommend company, suggestions for improvement
    ├── Employee completes form (deadline: last working day -5 days)
    ├── AI sentiment analysis on free-text responses
    └── HR reviews exit interview insights dashboard
                                │
                                ▼
STEP 3: KNOWLEDGE TRANSFER
    ├── HR creates knowledge transfer checklist with employee and manager
    ├── Employee assigns pending tasks to successor (via self-service)
    ├── Document handover tracked with deadline
    └── Manager confirms knowledge transfer completion
                                │
                                ▼
STEP 4: MULTI-DEPARTMENT CLEARANCE
    ├── System auto-creates clearance tasks for each department:
    │
    │   IT Department:
    │   ├── [ ] Laptop returned and inspected
    │   ├── [ ] Mobile phone returned
    │   ├── [ ] Access card deactivated
    │   └── [ ] All system accounts flagged for revocation
    │
    │   Finance Department:
    │   ├── [ ] All loans/advances reviewed
    │   ├── [ ] Outstanding expenses settled
    │   └── [ ] Final settlement calculation initiated
    │
    │   HR Department:
    │   ├── [ ] Leave balance finalized (encashment or forfeiture)
    │   ├── [ ] Gratuity calculation verified
    │   └── [ ] Documents returned to employee
    │
    │   Library/Admin:
    │   ├── [ ] Books/equipment returned
    │   └── [ ] Parking permit cancelled
    │
    ├── Each department head marks tasks complete
    └── HR can see clearance dashboard (% complete per dept)
                                │
                                ▼
STEP 5: FINAL SETTLEMENT CALCULATION
    Finance calculates:
    ├── Basic salary for worked days in final month
    ├── Leave encashment: encashable_balance × daily_basic_rate
    ├── Gratuity: (basic_salary / 26) × 30 × years_of_service
    │   (or per jurisdiction formula in tenant settings)
    ├── Notice period:
    │   ├── If employee served full notice: +0
    │   ├── If company waived notice: +notice_days_pay
    │   └── If employee left early: -shortfall_days_deduction
    ├── Pro-rated bonus (if policy)
    ├── Any outstanding loan recovery
    └── Final net settlement amount
    │
    ├── Finance submits for HR approval
    └── HR approves → CEO approves (if amount > threshold)
                                │
                                ▼
STEP 6: SYSTEM ACCESS REVOCATION
    ├── IT Admin triggers: "Revoke All Access" button
    ├── Automated:
    │   ├── Disable HRMS user account (immediate on last_working_date)
    │   ├── Create IT ticket for AD/Azure AD account deactivation
    │   ├── Generate access revocation certificate
    │   └── Log all revoked access in audit_log
    └── Biometric device: remove employee fingerprint enrollment
                                │
                                ▼
STEP 7: DOCUMENT GENERATION
    ├── Experience Letter: auto-generated with:
    │   employee name, designation, tenure, performance attestation
    ├── Relieving Letter: auto-generated with:
    │   last working date, "relieved of duties", wishing well
    ├── Salary Certificate: final month payslip
    └── All documents emailed to personal_email (not work email)
                                │
                                ▼
STEP 8: OFFBOARDING COMPLETION
    ├── UPDATE employees.status = 'terminated'/'resigned'
    ├── Final audit log entry
    └── Alumni portal access offered (optional — read-only)
        Employee can access: payslips, letters, training certificates
```

---

## Workflow 5: Performance Appraisal Cycle (Goal-Setting to Increment)

```
TRIGGER: HR Manager creates new Review Cycle (e.g., Annual 2024)
    │
    ▼
STEP 1: CYCLE CONFIGURATION
    ├── HR defines:
    │   ├── Review period (Jan 2024 - Dec 2024)
    │   ├── Rating scale (1-5 with behavioral anchors)
    │   ├── Weightings: KPI 60%, Competencies 40%
    │   ├── 360 degree or manager-only
    │   └── Deadlines for each phase
    └── Publish cycle → employees notified
                                │
                                ▼
STEP 2: GOAL SETTING PHASE
    ├── Employees + Managers set KPI goals (deadline: Jan 31)
    │   ├── Employee proposes goals in self-service
    │   ├── Manager reviews, edits, approves
    │   └── Cascaded from dept OKRs → individual KPIs
    │
    ├── Celery beat: daily reminder to employees without goals set
    └── Phase closes → goals locked (no edits after deadline)
                                │
                                ▼
STEP 3: CONTINUOUS TRACKING (Throughout Year)
    ├── Employees update goal actual values monthly
    ├── Manager can add mid-year check-in notes
    ├── System flags employees with 0% goal achievement at 6 months
    └── Q2/Q3 check-ins tracked in review system
                                │
                                ▼
STEP 4: SELF-REVIEW PHASE
    ├── Employees complete self-assessment:
    │   ├── Rate own performance on each goal
    │   ├── Rate competencies with evidence
    │   └── Free text: achievements, challenges, development needs
    │
    ├── Deadline: Dec 15
    ├── Daily reminder Celery task for incomplete self-reviews
    └── After deadline: self-reviews locked
                                │
                                ▼
STEP 5: PEER REVIEW PHASE (if 360)
    ├── System identifies peer reviewers (configurable: self-select, manager-select, auto)
    ├── Each peer receives anonymous review form
    ├── Peer reviews are aggregated (min 3 peers to show average — privacy)
    └── Deadline: Dec 20
                                │
                                ▼
STEP 6: MANAGER REVIEW PHASE
    ├── Manager completes review for each team member:
    │   ├── Rate each goal (with comments)
    │   ├── Rate competencies
    │   ├── Overall rating
    │   └── Development plan for next year
    │
    ├── Manager can see: self-review, peer aggregated scores, attendance, training data
    ├── Cannot see: other manager's ratings (prevents anchoring)
    └── Deadline: Dec 31
                                │
                                ▼
STEP 7: CALIBRATION SESSION
    ├── HR exports all ratings to calibration view
    ├── Bell curve generated: forced distribution view
    │   (e.g., 10% Outstanding, 20% Exceeds, 40% Meets, 20% Below, 10% Unsatisfactory)
    ├── Department heads discuss outliers in calibration meeting
    ├── Ratings adjusted in system post-calibration (tracked — old rating saved)
    └── AI performance predictions shown alongside calibration
                                │
                                ▼
STEP 8: EMPLOYEE COMMUNICATION
    ├── Manager schedules 1:1 appraisal discussion meeting
    ├── Employee can view final ratings in self-service
    ├── Employee acknowledges review (digital signature)
    └── Can add comments/rebuttal (tracked, not modifiable by manager)
                                │
                                ▼
STEP 9: INCREMENT & PROMOTION DECISIONS
    ├── HR generates increment recommendation matrix:
    │   Rating Band → Increment % range (policy-driven)
    │   ├── Outstanding: 20-30%
    │   ├── Exceeds: 12-20%
    │   ├── Meets: 5-12%
    │   ├── Below: 0-5%
    │   └── Unsatisfactory: 0% + PIP initiated
    │
    ├── Dept Managers recommend increments within band for each employee
    ├── Finance validates total increment budget
    ├── HR Manager approves
    └── CEO final approval for promotions
                                │
                                ▼
STEP 10: IMPLEMENTATION
    ├── Salary changes effective date configured
    ├── Payroll module notified: UPDATE salary_structures for affected employees
    ├── Promotion: UPDATE employees.job_grade_id, UPDATE employees.designation
    ├── Increment letters auto-generated (PDF, e-signed)
    ├── Employee notified via email + in-app
    └── PIP initiated for "Unsatisfactory" ratings with 90-day improvement plan
```

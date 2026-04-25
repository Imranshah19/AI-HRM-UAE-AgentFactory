# SECTION 7 — WORKFLOW DIAGRAMS (5 Critical Flows)

---

## WORKFLOW 1: MONTHLY PAYROLL RUN (End-to-End)

```
ACTORS: HR Manager, Celery Worker, Finance Manager, CEO/Admin, Employee

─────────────────────────────────────────────────────────────────────────────
STAGE 1: INITIATION
─────────────────────────────────────────────────────────────────────────────

[HR Manager]
  Step 1 ──► Opens "New Payroll Run" on dashboard
             Selects: Period (Jan 2024), Scope (All / Dept / Branch), Currency
             System shows: estimated employee count, last run comparison
  Step 2 ──► Clicks "Start Payroll Run"
             POST /api/v1/payroll/runs
             ╔══════════════════════════════════════╗
             ║ Feature flag check:                  ║
             ║ "new_payroll_engine_v2" → YES/NO     ║
             ╚══════════════════════════════════════╝
  Step 3 ──► System creates PayrollRun record (status: "processing")
             Dispatches Celery task: process_payroll_run.delay()
             Returns: run_id + job_id (202 Accepted)
  Step 4 ──► UI shows progress bar (polls /payroll/runs/{id} every 5s)

─────────────────────────────────────────────────────────────────────────────
STAGE 2: CALCULATION (Celery Worker — async background)
─────────────────────────────────────────────────────────────────────────────

[Celery Payroll Worker]
  Step 5 ──► Fetches all employees in scope (excludes: on_hold, terminated)
  Step 6 ──► For EACH employee:
             ┌─────────────────────────────────────────────────────────────┐
             │ a) Fetch current compensation record (salary structure)     │
             │ b) Calculate working days:                                  │
             │    working_days = calendar_days - weekends - public_holidays│
             │ c) Fetch attendance records for period:                     │
             │    present_days, absent_days, leave_days, overtime_hours    │
             │ d) Pro-rate salary if joining mid-month:                    │
             │    pro_rated = (basic / working_days) × present_days       │
             │ e) Calculate earnings:                                      │
             │    basic + HRA + medical + transport + fuel + utility      │
             │    + overtime_pay + festival_bonus (if month matches)       │
             │ f) Calculate deductions:                                    │
             │    income_tax = tax_slab_engine(taxable_income, jurisdiction)│
             │    eobi = MIN(basic × 5%, 370) [Pakistan 2024]             │
             │    sessi = basic × 0.5% [if Sindh branch]                  │
             │    loan_deduction = EMI from active loans                   │
             │    salary_advance = recovery amount if any                  │
             │ g) Calculate net:                                           │
             │    net = gross_earnings - total_deductions                  │
             │ h) Insert payroll_records row                               │
             │ i) Update progress counter in Redis                         │
             └─────────────────────────────────────────────────────────────┘
  Step 7 ──► All employees processed → update PayrollRun:
             status = "calculated"
             total_gross, total_net, employee_count updated

  Step 8 ──► Celery task triggers notification:
             → HR Manager: "Payroll calculated. Ready for review."

─────────────────────────────────────────────────────────────────────────────
STAGE 3: REVIEW & APPROVAL WORKFLOW
─────────────────────────────────────────────────────────────────────────────

[HR Manager] ←── Receives in-app + email notification
  Step 9 ──► Opens Payroll Run Detail page
             Reviews: total gross, individual breakdowns, comparisons vs last month
             Flags anomalies (salary jumps > 20%, new employees, etc.)
 Step 10 ──► Clicks "Submit for Finance Approval"
             POST /api/v1/payroll/runs/{id}/approve
             {action: "approve", role: "hr"}
             PayrollRun.status = "pending_finance"
             Finance team notified via email + in-app

[Finance Manager] ←── Receives approval request
 Step 11 ──► Reviews: totals, bank transfer amounts, deduction accuracy
             ┌─────────────────────────────────┐
             │ DECISION POINT                  │
             │ Approve → status: pending_ceo   │
             │ Reject → status: calculated     │
             │          (returns to HR)        │
             └─────────────────────────────────┘
 Step 12 ──► Finance clicks "Approve"
             POST /api/v1/payroll/runs/{id}/approve
             {action: "approve", role: "finance"}
             PayrollRun.status = "pending_ceo"
             CEO/Admin notified

[CEO / Super Admin] ←── Final approval request
 Step 13 ──► Reviews executive summary (total salary expense, headcount)
             Clicks "Final Approve"
             PayrollRun.status = "approved"

─────────────────────────────────────────────────────────────────────────────
STAGE 4: PAYMENT PROCESSING
─────────────────────────────────────────────────────────────────────────────

[Finance Manager]
 Step 14 ──► Clicks "Generate Bank File"
             GET /api/v1/payroll/runs/{id}/bank-file
             Celery task: generate_ibft_file.delay()
             ┌──────────────────────────────────────────────────────────┐
             │ IBFT File Format (Pakistan):                              │
             │ Record 1: Batch Header (company, date, total amount)     │
             │ Records: Employee IBAN/Account, Name, Amount, Purpose    │
             │ Record N: Batch Footer (record count, control sum)       │
             └──────────────────────────────────────────────────────────┘
             File uploaded to S3, download link provided
             PayrollRun.bank_file_url = "s3://..."
             PayrollRun.bank_file_generated_at = NOW()

 Step 15 ──► Finance uploads file to bank portal manually
             (or via SFTP/API if bank integration available)
             After payment confirmation:
             PATCH /api/v1/payroll/runs/{id}
             {status: "paid", payment_date: "2024-02-01"}

─────────────────────────────────────────────────────────────────────────────
STAGE 5: PAYSLIP DISTRIBUTION
─────────────────────────────────────────────────────────────────────────────

[Celery Worker] ←── Triggered on status = "paid"
 Step 16 ──► For each employee in run:
             a) Generate PDF payslip (WeasyPrint/ReportLab)
             b) Apply digital signature hash
             c) Upload to S3: /payslips/{tenant}/{year}/{month}/{emp_id}.pdf
             d) Update payroll_records: payslip_pdf_url, payslip_sent_at
             e) Send notification to employee:
                Channel: email (PDF attached) + in-app + push
                Template: "Your payslip for January 2024 is ready"

[Employee]
 Step 17 ──► Receives email / push notification
             Logs into Self-Service portal → My Payslips
             Downloads PDF or views online

─────────────────────────────────────────────────────────────────────────────
TOTAL FLOW DURATION: 15 min (calculation) + 1-2 days (approval) + 1 day (payment)
─────────────────────────────────────────────────────────────────────────────
```

---

## WORKFLOW 2: RECRUITMENT PIPELINE (Job Post → Hire)

```
ACTORS: HR Manager, Recruiter, Dept Manager, Candidate, AI Worker, Interviewer

─────────────────────────────────────────────────────────────────────────────
STAGE 1: JOB CREATION & PUBLISHING
─────────────────────────────────────────────────────────────────────────────

[HR Manager / Recruiter]
  Step 1 ──► Creates Job Posting:
             Title, Department, Requirements, Skills[], Salary Range,
             Min Experience, Education, Deadline
             POST /api/v1/recruitment/jobs  → status: "draft"

  Step 2 ──► Configures publishing:
             ☑ Internal portal
             ☑ LinkedIn Jobs API → POST to linkedin_jobs endpoint
             ☑ Indeed Publisher API → POST to indeed endpoint
             ☐ External career page (auto-published via public endpoint)

  Step 3 ──► Dept Manager reviews and gives verbal approval (no system gate)
             Recruiter clicks "Publish"
             PATCH /jobs/{id} {status: "open", published_at: NOW()}

─────────────────────────────────────────────────────────────────────────────
STAGE 2: APPLICATION INTAKE
─────────────────────────────────────────────────────────────────────────────

[Candidate] (anonymous / authenticated)
  Step 4 ──► Submits application via:
             a) Internal portal (authenticated employee referral)
             b) Career page (anonymous — rate limited: 10/min per IP)
             c) LinkedIn Easy Apply (webhook from LinkedIn API)
             d) Indeed Apply (webhook from Indeed API)
             POST /api/v1/recruitment/applications (multipart: CV file)
             Application created: stage = "applied"

  Step 5 ──► System auto-actions:
             a) Store CV in S3
             b) Trigger Celery: parse_cv.delay(application_id)
             c) Send acknowledgement email to candidate
             d) Increment job_postings.application_count

[Celery CV Worker]
  Step 6 ──► CV parsing:
             a) Download CV from S3
             b) Extract text (pdfplumber for PDF, python-docx for DOCX)
             c) Run SpaCy NER: extract {skills, experience, education}
             d) Store in job_applications.cv_parsed_data (JSONB)
             e) Trigger AI scoring: score_cv.delay(application_id, job_id)

  Step 7 ──► AI scoring:
             a) Load JD text + required_skills from job_postings
             b) Compute sentence-transformer embeddings
             c) Calculate composite score (0-100)
             d) Generate explanation + bias flags
             e) Store: ai_score, ai_score_breakdown, ai_explanation
             f) Notify recruiter: "New application scored: Ali Hassan — 84/100"

─────────────────────────────────────────────────────────────────────────────
STAGE 3: SCREENING & PIPELINE MOVEMENT
─────────────────────────────────────────────────────────────────────────────

[Recruiter]
  Step 8 ──► Opens Applications Pipeline (Kanban board)
             Sees columns: Applied → Screening → Phone Screen →
                           Technical → Interview 1 → Interview Final →
                           Offered → Hired / Rejected

  Step 9 ──► Reviews AI-scored candidates
             Drags cards to "Screening" for top candidates
             PATCH /applications/{id}/stage {stage: "screening"}
             Bulk rejects low-score candidates with reason

 Step 10 ──► Phone screen completed → moves to "Interview Scheduled"
             OR rejects with reason → candidate notified by email

─────────────────────────────────────────────────────────────────────────────
STAGE 4: INTERVIEW SCHEDULING
─────────────────────────────────────────────────────────────────────────────

[Recruiter]
 Step 11 ──► Clicks "Schedule Interview" on candidate card
             POST /api/v1/recruitment/interviews
             {
               application_id, interviewers: [dept_mgr_id, tech_lead_id],
               scheduled_at: "2024-01-20T10:00Z", duration: 60,
               type: "video", meeting_link: "https://meet.google.com/..."
             }

             Celery task: schedule_interview.delay()
             a) Create Google Calendar event via Google Calendar API
             b) Add interviewers as attendees
             c) Send calendar invites to all parties
             d) Send interview prep email to candidate
             e) Create interview_feedback rows for each interviewer

 Step 12 ──► Interviewers submit feedback (within 24h of interview):
             POST /api/v1/recruitment/interviews/{id}/feedback
             {rating: 4, technical_score: 3.5, communication: 4,
              recommendation: "proceed", notes: "..."}

─────────────────────────────────────────────────────────────────────────────
STAGE 5: OFFER MANAGEMENT
─────────────────────────────────────────────────────────────────────────────

[HR Manager / Recruiter]
 Step 13 ──► After final interview positive feedback:
             Opens "Generate Offer" workflow
             Sets: salary, start date, grade, benefits, offer expiry

 Step 14 ──► System generates offer letter PDF from template
             POST /api/v1/recruitment/applications/{id}/offer
             ┌────────────────────────────────────────────────┐
             │ PDF Template Variables:                         │
             │ {{candidate_name}}, {{designation}},           │
             │ {{department}}, {{salary}}, {{start_date}},    │
             │ {{benefits_list}}, {{offer_expiry}},           │
             │ {{hr_signature}}, {{company_seal}}             │
             └────────────────────────────────────────────────┘
             Offer saved to S3, status: "pending_approval"

 Step 15 ──► HR Manager approves offer
             POST /offers/{id}/approve
             Stage → "offered"
             Email sent to candidate with offer letter PDF attached

[Candidate]
 Step 16 ──► Reviews offer
             ┌─────────────────────────────┐
             │ DECISION POINT              │
             │ Accept → stage: "hired"     │
             │ Reject → stage: "withdrawn" │
             │ Negotiate → stay: "offered" │
             └─────────────────────────────┘

─────────────────────────────────────────────────────────────────────────────
STAGE 6: HIRING & ONBOARDING TRIGGER
─────────────────────────────────────────────────────────────────────────────

[HR Manager]
 Step 17 ──► Candidate accepts offer (verbal or via portal)
             PATCH /applications/{id}/stage {stage: "hired"}

 Step 18 ──► System auto-triggers:
             a) Mark job_posting slot as filled
             b) If openings_count filled → close job posting
             c) Reject all remaining "applied" candidates politely
             d) Create draft Employee record (pre-populate from application)
             e) Trigger "Add Employee" form pre-filled for HR to complete
             f) Update recruitment analytics:
                time_to_hire, cost_per_hire, source_attribution

─────────────────────────────────────────────────────────────────────────────
TOTAL FLOW: 2-6 weeks (typical) | Automated steps: 1,5,6,7,11,18
─────────────────────────────────────────────────────────────────────────────
```

---

## WORKFLOW 3: LEAVE APPROVAL (Employee → Manager → HR)

```
ACTORS: Employee, Line Manager, HR Manager, System (Celery)

─────────────────────────────────────────────────────────────────────────────
STAGE 1: LEAVE APPLICATION
─────────────────────────────────────────────────────────────────────────────

[Employee]
  Step 1 ──► Opens "Apply for Leave" (web or mobile PWA)
             Selects: Leave Type (Annual / Sick / Casual / etc.)
             Selects: Start Date, End Date
             System shows LIVE:
             ┌─────────────────────────────────────────────────────┐
             │ Balance Preview:                                     │
             │   Available: 12 days                                │
             │   This request: 3 days                              │
             │   After approval: 9 days remaining                  │
             │                                                     │
             │ Conflict Check:                                     │
             │   ⚠ Ahmed Ali is also on leave Jan 20-21           │
             │   ✅ No blackout dates in selected range            │
             │   ✅ 3 days notice given (required: 1 day)          │
             └─────────────────────────────────────────────────────┘
  Step 2 ──► Enters reason, uploads document if required (sick leave cert)
             Clicks "Submit"
             POST /api/v1/leave/requests

  Step 3 ──► System validates:
             ✅ Sufficient balance?          → ERROR if insufficient
             ✅ Not a blackout date?         → ERROR if blackout
             ✅ Notice period met?           → ERROR if insufficient notice
             ✅ Max consecutive days OK?     → ERROR if exceeded
             ✅ Not overlapping approved leave?
             ✅ Min service days met?

             On validation pass:
             leave_requests row created, status = "pending"
             Employee receives: confirmation in-app notification

─────────────────────────────────────────────────────────────────────────────
STAGE 2: MANAGER REVIEW (Level 1)
─────────────────────────────────────────────────────────────────────────────

[Celery Notification Worker]
  Step 4 ──► Sends to Line Manager:
             Email: "Leave Request Pending — Muhammad Ahmed"
             In-App: badge on pending approvals
             Template variables: name, dates, days, type, reason, link

[Line Manager]
  Step 5 ──► Opens pending approval (web or mobile)
             Reviews:
             - Employee details + leave history
             - Team calendar (who else is on leave same days)
             - Workload / project impact note
             ┌─────────────────────────────────────────────────────┐
             │ DECISION POINT                                      │
             │                                                     │
             │ Approve → status: "manager_approved"               │
             │ Reject  → status: "rejected" (final)               │
             │           Must provide rejection reason             │
             │ Delegate → reassign to peer manager                │
             └─────────────────────────────────────────────────────┘

  Step 6a ──► Manager APPROVES:
              POST /leave/requests/{id}/action {action: "approve"}
              status → "manager_approved"
              System notifies HR for Level 2 review
              System notifies Employee: "Approved by manager, pending HR"

  Step 6b ──► Manager REJECTS:
              POST /leave/requests/{id}/action
              {action: "reject", comments: "Critical sprint in progress"}
              status → "rejected"
              Employee notified immediately with reason
              ─── END OF FLOW ───

─────────────────────────────────────────────────────────────────────────────
STAGE 3: HR REVIEW (Level 2)
─────────────────────────────────────────────────────────────────────────────

[HR Manager] ←── Notification received
  Step 7 ──► For most standard leave types:
             ┌─────────────────────────────────────────────────────┐
             │ AUTO-APPROVE RULES (configurable per leave type):   │
             │ If leave_type.auto_approve_after_manager = True     │
             │ AND leave_type.requires_hr_review = False           │
             │ → Auto-approve after manager approval               │
             │ → Skip HR step                                      │
             └─────────────────────────────────────────────────────┘

             For leave types requiring HR review (maternity, study, etc.):
             HR reviews: documentation uploaded, policy compliance
             ┌────────────────────────────────────────┐
             │ DECISION POINT                         │
             │ Approve → status: "approved"           │
             │ Reject  → status: "rejected"           │
             └────────────────────────────────────────┘

  Step 8 ──► HR APPROVES:
             POST /leave/requests/{id}/action
             {action: "approve", role: "hr"}
             status → "approved"

─────────────────────────────────────────────────────────────────────────────
STAGE 4: POST-APPROVAL SYSTEM ACTIONS
─────────────────────────────────────────────────────────────────────────────

[System — triggered on status = "approved"]
  Step 9 ──► Deduct leave balance:
             UPDATE leave_balances SET used = used + 3 WHERE ...
             INSERT leave_balance_transactions (debit, reason: "approved_leave")

 Step 10 ──► Update attendance records for the leave period:
             For each day in range: INSERT/UPDATE attendance_records
             status = "on_leave", leave_request_id = this request

 Step 11 ──► Update team leave calendar (cached in Redis for fast UI)

 Step 12 ──► Notify Employee:
             Email + Push: "Your Annual Leave (Jan 20-22) has been approved"
             Include: Updated balance, contact info during leave

 Step 13 ──► If leave spans a pay period:
             Flag in payroll engine: is_leave_paid_or_unpaid?
             Unpaid leave → create payroll_adjustment record

─────────────────────────────────────────────────────────────────────────────
TOTAL FLOW: 15 min (standard) to 2 days (HR review required)
SLA: Manager must act within 48h | HR within 24h (configurable per tenant)
─────────────────────────────────────────────────────────────────────────────
```

---

## WORKFLOW 4: EMPLOYEE OFFBOARDING (Resignation → Final Settlement)

```
ACTORS: Employee, HR Manager, Line Manager, IT, Finance, Admin, Security, System

─────────────────────────────────────────────────────────────────────────────
STAGE 1: RESIGNATION TRIGGER
─────────────────────────────────────────────────────────────────────────────

[Employee]
  Step 1 ──► Submits resignation via portal:
             "Raise Request" → Type: Resignation
             Last working day, reason, notice period acknowledgement
             OR
             HR Manager receives verbal/email resignation and creates it

[HR Manager]
  Step 2 ──► Receives resignation notification
             Verifies notice period requirement:
             notice_period_days = 30 (from employee record)
             last_working_day = submission_date + 30 days

  Step 3 ──► Creates Offboarding record:
             POST /api/v1/offboarding
             employee.lifecycle_status → "offboarding"

             System auto-creates clearance checklist with tasks:
             ┌────────────────────────────────────────────────────────┐
             │ CLEARANCE CHECKLIST (auto-generated):                  │
             │                                                        │
             │ IT Department:                                         │
             │   □ Laptop returned and wiped                         │
             │   □ Access card deactivated                           │
             │   □ Email account archived (30-day grace)             │
             │   □ All systems access revoked                        │
             │   □ SIM card returned                                 │
             │                                                        │
             │ Finance:                                               │
             │   □ Salary advance recovered                          │
             │   □ Loan balance settled or deducted from settlement  │
             │   □ Expense claims processed                          │
             │   □ Final settlement calculated and approved          │
             │                                                        │
             │ Admin:                                                 │
             │   □ Office keys returned                              │
             │   □ Parking sticker cancelled                         │
             │   □ Company phone returned                            │
             │                                                        │
             │ HR:                                                    │
             │   □ Knowledge transfer completed                      │
             │   □ Exit interview conducted                          │
             │   □ Experience letter prepared                        │
             │   □ Relieving letter prepared                         │
             └────────────────────────────────────────────────────────┘

  Step 4 ──► Each department head notified by email/in-app:
             "Action Required: Clearance tasks for Ahmed Khan by Jan 31"

─────────────────────────────────────────────────────────────────────────────
STAGE 2: EXIT INTERVIEW
─────────────────────────────────────────────────────────────────────────────

[HR Manager]
  Step 5 ──► Schedules exit interview (within first week of notice period)
             Sends digital exit interview form to employee

[Employee]
  Step 6 ──► Completes exit interview form:
             - Primary reason for leaving (dropdown: compensation/growth/culture/personal/...)
             - Would you recommend us as employer? (NPS 0-10)
             - Rating: management/culture/work-life balance/compensation
             - Open text: what could we improve?
             - Contact for alumni network? (optional)

[Celery AI Worker]
  Step 7 ──► AI sentiment analysis on open text responses:
             a) VADER sentiment score → overall sentiment
             b) Key theme extraction (SpaCy + custom HR lexicon)
             c) Flags concerning themes: harassment, burnout, management issues
             d) Stores: sentiment_score, key_themes, severity_flags
             e) If severity_flags present → alert HR Director immediately

─────────────────────────────────────────────────────────────────────────────
STAGE 3: KNOWLEDGE TRANSFER
─────────────────────────────────────────────────────────────────────────────

[Line Manager + Departing Employee]
  Step 8 ──► Manager creates knowledge transfer tasks:
             Assigns to: successor or peer
             Each task: description, handover_doc_url, deadline, status

  Step 9 ──► Employee completes tasks + uploads handover documents
             Marks each as "completed"
             Manager reviews and approves completion

─────────────────────────────────────────────────────────────────────────────
STAGE 4: CLEARANCE COMPLETION
─────────────────────────────────────────────────────────────────────────────

[Each Department Head]
 Step 10 ──► Completes own department clearance tasks in system
             Marks each task: pending → completed (with date + notes)
             For IT: system access revocation triggered automatically
             when IT marks their clearance as complete

[System — IT clearance complete trigger]
 Step 11 ──► Auto-revoke all system access:
             a) Disable user account (is_active = False)
             b) Revoke all active JWT sessions (Redis blacklist)
             c) Remove from all email distribution groups
             d) Transfer files/emails to manager (Google Workspace API)
             e) Trigger audit log entry: "system_access_revoked"

─────────────────────────────────────────────────────────────────────────────
STAGE 5: FINAL SETTLEMENT CALCULATION
─────────────────────────────────────────────────────────────────────────────

[HR Manager]
 Step 12 ──► Opens Final Settlement module
             System auto-calculates:
             ┌────────────────────────────────────────────────────────┐
             │ FINAL SETTLEMENT COMPONENTS:                           │
             │                                                        │
             │ PAYABLE TO EMPLOYEE:                                   │
             │ + Salary up to last working day (pro-rated)            │
             │ + Leave encashment (unused annual leave × daily rate)  │
             │ + Gratuity = (basic × years_of_service × 30/365)      │
             │   [Pakistan: only if >1 year service]                  │
             │ + Bonus pro-rata (if applicable)                       │
             │ + Notice pay (if waived by company)                    │
             │                                                        │
             │ DEDUCTIBLE FROM EMPLOYEE:                              │
             │ - Outstanding salary advances                          │
             │ - Loan balance remaining                               │
             │ - Notice period not served (if early exit)             │
             │ - Asset damage recovery (if any)                       │
             │                                                        │
             │ NET SETTLEMENT = Payable - Deductible                  │
             └────────────────────────────────────────────────────────┘

 Step 13 ──► HR Manager reviews calculation → submits for Finance approval
             POST /offboarding/{id}/settlement {action: "submit"}

[Finance Manager]
 Step 14 ──► Reviews settlement figures
             Approves → triggers inclusion in next payroll run
             OR creates special off-cycle payment

─────────────────────────────────────────────────────────────────────────────
STAGE 6: DOCUMENTATION & CLOSURE
─────────────────────────────────────────────────────────────────────────────

[HR Manager]
 Step 15 ──► All clearance tasks marked complete
             Generates documents:
             a) Experience Letter (PDF from template)
             b) Relieving Letter (PDF from template)
             Uploads signed copies to employee documents
             Shares with employee via email + portal

 Step 16 ──► Updates employee record:
             lifecycle_status → "terminated" or "resigned"
             end_date = last_working_day
             Org chart auto-updates (reporting line removed)

 Step 17 ──► Optional: Alumni portal invite sent if employee opted in

─────────────────────────────────────────────────────────────────────────────
TOTAL FLOW: 30-day notice period | Automated: Steps 3,7,11,12
─────────────────────────────────────────────────────────────────────────────
```

---

## WORKFLOW 5: PERFORMANCE APPRAISAL CYCLE (Goal-Setting → Increment Decision)

```
ACTORS: HR Manager, Department Manager, Employee, Peers, System (Celery)

─────────────────────────────────────────────────────────────────────────────
STAGE 1: CYCLE CREATION & CONFIGURATION
─────────────────────────────────────────────────────────────────────────────

[HR Manager]
  Step 1 ──► Creates Appraisal Cycle:
             POST /api/v1/performance/cycles
             {
               name: "Annual Review 2024",
               year: 2024,
               type: "annual",          // or quarterly
               rating_scale: "1_to_5",
               include_self_review: true,
               include_peer_review: true,
               include_360: true,
               forced_ranking: true,    // bell curve
               competencies: [
                 "technical_skills", "communication", "leadership",
                 "initiative", "teamwork", "delivery"
               ]
             }
             status → "goal_setting"

  Step 2 ──► System sends notification to all employees:
             "Performance Review Cycle 2024 has begun. Set your goals by Jan 31."

─────────────────────────────────────────────────────────────────────────────
STAGE 2: GOAL SETTING
─────────────────────────────────────────────────────────────────────────────

[Employee]
  Step 3 ──► Opens "My Goals" in portal
             Creates 3-5 goals (KPIs / OKRs):
             POST /api/v1/performance/goals
             {
               title: "Reduce API response time by 30%",
               goal_type: "kpi",           // or okr
               target_value: 30,
               target_unit: "percent",
               target_date: "2024-12-31",
               weight: 40                  // % of overall score
             }

[Line Manager]
  Step 4 ──► Reviews team goals
             May add/edit goals for direct reports
             Approves final goal set → status → "goals_approved"

  Step 5 ──► HR Manager advances cycle stage:
             PATCH /cycles/{id}/advance → stage: "in_progress" (mid-year)
             Employees begin updating actual progress during the year

─────────────────────────────────────────────────────────────────────────────
STAGE 3: CONTINUOUS PROGRESS TRACKING (throughout year)
─────────────────────────────────────────────────────────────────────────────

[Employee] (monthly)
  Step 6 ──► Updates goal progress:
             PATCH /performance/goals/{goal_id}
             {actual_value: 15, progress_note: "Achieved 15% improvement in Q2"}

  Step 7 ──► AI anomaly detection (Celery, runs monthly):
             If employee has not updated goals in 45 days → reminder sent
             If goal progress behind schedule → flag to manager

─────────────────────────────────────────────────────────────────────────────
STAGE 4: APPRAISAL REVIEWS
─────────────────────────────────────────────────────────────────────────────

[HR Manager]
  Step 8 ──► Advances cycle to "review" stage (year end / quarter end)
             System opens review forms for all participants

[Employee — Self Review]
  Step 9 ──► Opens "My Review" form
             Rates own competencies (1-5 slider for each)
             Reviews each goal: target vs actual
             Writes overall self-assessment text
             POST /performance/reviews {type: "self"}
             Deadline: 10 days → system sends daily reminder if not submitted

[Peer Reviewers]
 Step 10 ──► Each employee receives 2-3 peer review requests
             (HR or manager assigns peers; anonymized in output)
             POST /performance/reviews {type: "peer", reviewer_id: ...}
             Peer ratings are anonymized before employee sees them

[Line Manager — Manager Review]
 Step 11 ──► After self-review submitted, manager unlocks their form
             Rates each competency → adds manager comments
             Reviews goal achievement vs actuals
             Sets: performance_band (exceptional/exceeds/meets/below/unsatisfactory)
             Sets: increment_recommended (T/F), increment_percentage
             Sets: promotion_recommended (T/F), pip_recommended (T/F)
             POST /performance/reviews {type: "manager"}

[Celery AI Worker — runs nightly during review period]
 Step 12 ──► Generates performance prediction per employee:
             Uses: historical KPIs, attendance, training, peer ratings, tenure
             Stores: predicted_band, confidence_score
             HR sees AI prediction alongside manager's rating

─────────────────────────────────────────────────────────────────────────────
STAGE 5: CALIBRATION
─────────────────────────────────────────────────────────────────────────────

[HR Manager]
 Step 13 ──► Opens "Review Dashboard" → Bell Curve view
             Sees distribution of performance bands across org
             ┌─────────────────────────────────────────────────────┐
             │ BELL CURVE TARGET DISTRIBUTION:                     │
             │ Exceptional:  10%  ▓▓                               │
             │ Exceeds:      20%  ▓▓▓▓                             │
             │ Meets:        50%  ▓▓▓▓▓▓▓▓▓▓                      │
             │ Below:        15%  ▓▓▓                              │
             │ Unsatisfactory: 5% ▓                                │
             └─────────────────────────────────────────────────────┘
             Identifies outliers (entire department rated "exceptional")

 Step 14 ──► Calibration session with dept managers:
             Managers can adjust ratings with justification
             All changes tracked in audit log with override reason

─────────────────────────────────────────────────────────────────────────────
STAGE 6: COMMUNICATION & ACKNOWLEDGEMENT
─────────────────────────────────────────────────────────────────────────────

[HR Manager]
 Step 15 ──► Advances cycle → "finalised"
             System sends each employee their review:
             "Your 2024 Performance Review is ready to view"

[Employee]
 Step 16 ──► Reviews final ratings and manager comments
             PATCH /performance/reviews/{id}/acknowledge
             {acknowledged: true, acknowledgement_note: "Agreed/Disagreed..."}
             Disagreement logged — triggers HR follow-up if escalated

─────────────────────────────────────────────────────────────────────────────
STAGE 7: INCREMENT & PROMOTION DECISIONS
─────────────────────────────────────────────────────────────────────────────

[HR Manager + Finance]
 Step 17 ──► Exports increment recommendations report
             Groups by band, department, current salary
             Validates against salary budget constraints

 Step 18 ──► Creates compensation revisions for approved increments:
             POST /employees/{id}/compensation
             {effective_date: "2024-04-01", revision_reason: "Annual increment"}
             Approval workflow: HR → Finance → CEO

 Step 19 ──► PIP cases:
             For employees with "unsatisfactory" band:
             POST /performance/pips {employee_id, goals, timeline, milestones}
             Employee + Manager notified
             PIP tracked over 90 days with milestone check-ins

 Step 20 ──► Cycle closed → status → "closed"
             Historical data archived, feeds next cycle's AI training data

─────────────────────────────────────────────────────────────────────────────
TOTAL FLOW: 3-4 months (annual) | 6 weeks (quarterly)
Automated: Steps 2,7,12,15 | AI-assisted: Steps 12,13
─────────────────────────────────────────────────────────────────────────────
```

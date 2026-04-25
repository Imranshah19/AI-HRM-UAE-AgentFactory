# Section 4: UI Pages Inventory

## 4.1 HR Manager — Screen Inventory

### Dashboard & Navigation
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| HR Dashboard | Command center — real-time org stats | KPI cards (headcount, attrition, leave rate, open positions), pending approvals widget, attendance live feed, AI alerts panel | Navigate to modules, act on pending approvals |
| Notifications Center | All notifications and alerts | Notification list grouped by type, mark read, filter by channel | Read, dismiss, respond |

### Employee Management
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Employee List | Browse all employees | DataTable with column filters, search, export, bulk actions, status filter chips | Search, filter, export CSV/Excel, bulk status update |
| Employee Profile | View/edit full employee data | Profile header (photo, name, status badge), tabbed sections: Personal · Employment · Compensation · Documents · History | Edit fields, upload docs, trigger lifecycle actions |
| Add Employee | Onboard new employee | Multi-step form: Basic Info → Employment → Compensation → Documents → Access | Submit, save as draft |
| Bulk Import | Import employees from file | Drag-drop file upload, column mapping wizard, validation preview table, error report | Upload file, map columns, fix errors, confirm import |
| Org Chart | Visual hierarchy | Zoomable D3.js tree, click-to-expand, search highlight, export as PNG/SVG | Navigate, search, export |
| Document Manager | Employee document vault | Grouped list by type, expiry date color coding (red/amber/green), version history modal | Upload, view, verify, set expiry alert |

### Attendance
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Live Attendance Board | Real-time check-in status | Live grid of all employees (present/absent/late/on-leave), WebSocket-powered auto-update | Filter by department, manual override |
| Attendance Records | Historical attendance data | Calendar view + table view toggle, per-employee timeline, exception highlighting | Filter, override, export |
| Monthly Report | Attendance summary report | Department-wise summary table, late/absent/overtime stats, exception list | Filter, export PDF/Excel |
| Shift Manager | Manage work shifts | Shift cards with time ranges, assign employees to shifts, roster calendar | Create/edit shifts, bulk assign |

### Payroll
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Payroll Dashboard | All payroll runs + status | Run cards with status badges, timeline of approval stages, totals summary | View, filter by period |
| New Payroll Run | Initiate payroll | Period selector, scope config (all/dept), estimated count, confirm dialog | Start run, monitor progress |
| Payroll Run Detail | Review and approve run | Employee-wise breakdown table, totals, components view, comparison with last run | Approve/reject, download bank file |
| Payslip Viewer | Individual payslip | Formatted payslip layout matching print output | Download PDF, email to employee |
| Salary Structures | Configure pay components | Component cards with type/formula, preview calculator | Create/edit structures |
| Tax Configuration | Configure tax slabs | Slab table editor per jurisdiction, effective date | Add/edit slabs |

### Recruitment (ATS)
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Jobs Board | All open positions | Kanban or list view, stats per job (applied/screened/interviewed), external posting status | Create job, pause/close, view applications |
| Job Detail & Editor | Create/edit job posting | Rich text editor for JD, salary config, external board toggles, preview | Publish, save draft, post to LinkedIn/Indeed |
| Applications Pipeline | Candidate pipeline per job | Kanban with drag-and-drop stage movement, AI score visible, bulk actions | Move stages, schedule interview, reject, view CV |
| Candidate Profile | Individual candidate view | CV viewer, AI score breakdown card, interview notes timeline, offer history | Score with AI, schedule interview, send offer |
| Interview Scheduler | Manage interviews | Calendar integration view, interviewer assignment, confirmation email | Schedule, send calendar invite, record feedback |
| Offer Management | Track offers | Offer list with status, template generator, expiry dates | Generate PDF, send, track response |

### Leave Management
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Leave Dashboard | Overview + pending approvals | Pending approval cards, today's absences, upcoming leaves calendar | Approve/reject pending, view calendar |
| Leave Requests List | All leave requests | Filterable table with status badges, date ranges, employee names | Approve, reject, add comments, export |
| Leave Types Config | Configure leave types | Type cards with rules config, gender restrictions, carry-forward rules | Add/edit types, activate/deactivate |
| Public Holidays | Manage holidays per location | Yearly calendar with holiday markers, per-country config | Add/edit holidays, set location scope |
| Leave Balances | Employee balance report | Table with all types per employee, year filter | View, adjust balance, encash |

### Performance
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Review Cycles | Manage appraisal cycles | Cycle cards with progress bars (goals set/self-reviews/manager reviews), status | Create cycle, advance stage |
| Review Dashboard | Overview of current cycle | Completion heatmap by department, pending reviews, bell curve chart | Remind pending, view bell curve |
| Employee Review | View/submit review | Rating form with competency sliders, text areas, goal achievement table | Submit ratings, request clarification |
| PIP Manager | Performance improvement plans | Active PIPs list, timeline tracker, milestone status | Create PIP, update milestones, close |
| AI Predictions | Performance predictions | Table with predicted bands, confidence scores, filters | View, export, override |

### Training
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Training Catalog | All programs | Card grid with type badges, enrollment counts, completion rates | Create program, enroll employees |
| Training Enrollments | Enrollment management | Employee-program matrix, completion status, deadlines | Enroll, mark complete, generate certificate |
| Skill Matrix | Org-wide skill analysis | Heatmap: employees × skills, gap analysis by role | Filter by dept/role, export |
| Compliance Tracker | Mandatory training deadlines | Alert list of overdue/upcoming mandatory training | Send reminders, report compliance % |

### Analytics & Reports
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Executive Dashboard | Top-level HR KPIs | KPI tiles, trend charts, attrition heatmap, headcount trend, salary distribution | Date range filter, drill-down |
| Custom Report Builder | Ad-hoc reports | Drag-drop field selector, filter builder, preview table, chart type selector | Build, save, schedule, export |
| Scheduled Reports | Manage auto-reports | List of scheduled reports with next run time, recipients | Create, edit, disable |
| AI Analytics | NLQ + anomaly detection | Chat-like query input, generated chart output, anomaly alert list | Type query, view chart, investigate anomaly |

### System Config (HR Manager)
| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| User Management | Manage system users | User list with roles, invite form, MFA status | Invite, change role, disable user |
| Notification Templates | Configure notification messages | Template list with preview, variable reference guide | Edit templates, preview, test send |

---

## 4.2 Employee Self-Service — Screen Inventory

| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| My Dashboard | Personal overview | Leave balance cards, upcoming events, team calendar, recent payslip, notifications | Quick apply leave, view payslip |
| My Profile | View/edit personal info | Personal info tabs, emergency contacts, bank details (masked) | Edit contact info, request salary update |
| Apply for Leave | Leave application form | Leave type selector, date picker with balance preview, conflict calendar, reason | Submit, save draft |
| My Leave History | All leave requests | List with status timeline, cancel option | View, cancel pending |
| My Payslips | Salary statements | Monthly list, PDF download, tax year filter | Download, view online |
| Tax Certificate | Year-end document | Year selector, download button | Download PDF |
| My Goals | Performance goals | Goal cards with progress bars, target vs actual | Update actual value, add note |
| My Reviews | Performance review history | Review list, self-assessment form, acknowledgement | Submit self-review, acknowledge |
| Training Portal | Available + enrolled | Catalog with filter, enrolled list with progress, certificates | Enroll, start e-learning, download cert |
| Raise Request | Internal tickets | Request type selector, form, attachments | Submit, track status |
| HR Letters | Document request | Letter type selector, purpose input | Request letter, download when ready |
| Announcements | Company news | Feed with pinned items, attachment downloads | Read, download attachments |
| Team Directory | Org directory | Search, filter by dept, clickable cards | Search, view profile, message |
| My Assets | Assigned equipment | Asset list with condition, handover date | Report damage, request return |
| Change Password | Security settings | Current + new password form, MFA setup | Change password, enable/disable MFA |

---

## 4.3 Recruiter — Screen Inventory

| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Recruiter Dashboard | Recruitment pipeline overview | Jobs by status, applications by stage, time-to-hire chart, today's interviews | Navigate to active roles |
| My Jobs | Assigned job postings | List with applicant counts, urgency indicators | Post jobs, view pipeline |
| Application Pipeline | Kanban per job | Cards with AI scores, contact info, stage move | Screen, schedule, reject, score with AI |
| Candidate Database | All candidates | Search by skill/experience, source filter | View profile, match to jobs |
| Interview Schedule | Today/week interviews | Calendar view with interviewer, time, mode | Confirm, reschedule, add feedback |
| Offer Tracker | All pending offers | List with expiry countdowns | Follow up, extend, retract |
| Analytics | Recruitment metrics | Time-to-hire, cost-per-hire, funnel conversion chart | Date range filter, export |

---

## 4.4 Super Admin — Screen Inventory

| Page | Purpose | Key Components | User Actions |
|------|---------|----------------|-------------|
| Admin Dashboard | Platform health | Tenant list, system metrics, error rate, active users | Navigate to tenant management |
| Tenant Management | Manage all tenants/orgs | Tenant cards with subscription tier, employee count, status | Create tenant, edit settings, suspend |
| Role & Permission Manager | RBAC configuration | Role list, permission matrix editor, resource-level access | Create roles, assign permissions |
| Audit Log Viewer | Immutable audit trail | Searchable audit log with actor, action, resource, timestamp, diff viewer | Filter, search, export |
| System Health | Infrastructure status | Service status, DB connections, Redis memory, Celery queue depths | Investigate, restart service |
| AI Model Management | AI model versions | Model version list, accuracy metrics, retrain trigger, bias reports | View metrics, trigger retraining |
| Data Privacy | GDPR controls | Erasure requests queue, consent tracking, retention policy viewer | Process erasure, approve, log |
| Configuration | Global system config | Feature flag toggles, jurisdiction rules, integration settings | Enable/disable features, configure |

---

## 4.5 Mobile App — Screen Inventory (PWA Phase 1)

| Screen | Platform | Key Components | Actions |
|--------|----------|----------------|---------|
| Login | PWA + RN | Email/password + biometric button, SSO option | Login, biometric auth |
| Home/Dashboard | PWA + RN | Attendance status card, leave balance summary, pending actions, notifications | Quick check-in, apply leave |
| Check In/Out | PWA + RN | GPS map view, face capture preview, geofence status indicator | Confirm check-in/out |
| Apply Leave | PWA + RN | Leave type picker, date picker, balance preview | Submit leave |
| Leave Status | PWA + RN | Active requests with status steps | View status, cancel |
| Payslip | PWA + RN | Month picker, payslip summary, PDF download | View, download |
| Notifications | PWA + RN | Notification list, swipe-to-dismiss | Read, navigate to related item |
| Team Directory | PWA | Search, profile cards | Search, call |
| Settings | PWA + RN | Notification preferences, biometric toggle, language | Configure |

### React Native Additional Screens (Phase 2)

| Screen | Key Components | Actions |
|--------|----------------|---------|
| Offline Queue | Pending sync items, error list | View, force sync |
| Face Capture | Camera view, face alignment guide | Capture, retake |
| Push Notifications | Native notification permission flow | Enable/disable per type |
| Biometric Setup | Fingerprint/FaceID enrollment flow | Enroll, disable |
| Offline Payslip | Cached payslip list | View cached, refresh |

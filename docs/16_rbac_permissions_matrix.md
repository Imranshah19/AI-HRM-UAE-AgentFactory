# SECTION 6 — USER ROLES & PERMISSIONS MATRIX

## 6.1 Role Hierarchy

```
Super Admin (tenant-level god mode)
  └── HR Manager (full HR operations)
        ├── Finance (payroll read + approve + bank file)
        ├── Recruiter (ATS operations)
        └── Department Manager (own dept + team)
              └── Employee (self-service only)
```

## 6.2 Permission Notation

```
C = Create    R = Read    U = Update    D = Delete    A = Approve
● = Full      ◐ = Partial (scope-limited)   ○ = None   * = with conditions
```

---

## 6.3 Full RBAC Matrix — All 14 Modules

### MODULE 1: EMPLOYEE MANAGEMENT

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Employee list (all) | CRUDA | CRUDA | R | ○ | R◐ | ○ |
| Employee list (own dept) | ● | ● | ○ | ○ | R | ○ |
| Own employee profile | ● | ● | R | ○ | R | R* |
| Personal fields (name, address) | CRUDA | CRUD | ○ | ○ | R | U* |
| **CNIC / NID** | CRUD | CRUD | ○ | ○ | ○ | R* |
| **Basic salary** | CRUD | CRUD | R | ○ | ○ | ○ |
| **Bank account details** | CRUD | CRUD | RU | ○ | ○ | U* |
| **Grade / cost center** | CRUD | CRUD | R | ○ | R | ○ |
| Work email / employment | CRUD | CRUD | R | ○ | R | ○ |
| Emergency contacts | CRUD | CRUD | ○ | ○ | ○ | CRUD |
| Employee lifecycle status | CRUDA | CRUDA | ○ | ○ | ○ | ○ |
| Org chart (view) | ● | ● | ● | ● | ● | R |
| Org chart (edit hierarchy) | CRUD | CRUD | ○ | ○ | ○ | ○ |
| Document upload | CRUD | CRUD | ○ | ○ | ○ | C◐ |
| Document view | ● | ● | R◐ | ○ | R◐ | R* |
| Document expiry alerts | ● | ● | ○ | ○ | R | R* |
| Bulk import | ● | C | ○ | ○ | ○ | ○ |
| Bulk export | ● | C | C◐ | ○ | ○ | ○ |
| Employee directory | ● | ● | R | R | R | R |

> * Employee can update own non-sensitive fields; cannot change employment/salary data
> ◐ Dept Manager sees own department only; Finance sees salary fields only

---

### MODULE 2: ATTENDANCE & TIME TRACKING

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Check-in / check-out (own) | ● | ● | ● | ● | ● | C |
| View own attendance | ● | ● | ● | ● | ● | R |
| View team attendance | ● | ● | ○ | ○ | R | ○ |
| View all attendance | ● | ● | ○ | ○ | ○ | ○ |
| Regularize attendance (override) | ● | A | ○ | ○ | C◐ | ○ |
| Live attendance dashboard | ● | ● | ○ | ○ | R◐ | ○ |
| Shift create / edit | ● | CRUD | ○ | ○ | ○ | ○ |
| Shift assignment | ● | CRUD | ○ | ○ | R | ○ |
| Shift swap request | ● | ● | ● | ● | A | C |
| Overtime approval | ● | A | ○ | ○ | A◐ | ○ |
| Monthly attendance report | ● | ● | R | ○ | R◐ | R* |
| Export attendance | ● | ● | ○ | ○ | C◐ | ○ |
| Biometric device config | ● | C | ○ | ○ | ○ | ○ |
| Geofence config | ● | CRUD | ○ | ○ | ○ | ○ |

---

### MODULE 3: PAYROLL SYSTEM

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **View salary (all employees)** | ● | ● | R | ○ | ○ | ○ |
| **View salary (own dept)** | ● | ● | ○ | ○ | ○ | ○ |
| **View own salary** | ● | ● | ● | ● | ● | R |
| Salary structure create/edit | ● | CRUD | R | ○ | ○ | ○ |
| Compensation revision | ● | C | ○ | ○ | ○ | ○ |
| Compensation approval | ● | A | A | ○ | ○ | ○ |
| Payroll run initiate | ● | C | ○ | ○ | ○ | ○ |
| Payroll run view | ● | R | R | ○ | ○ | ○ |
| Payroll HR approve | ● | A | ○ | ○ | ○ | ○ |
| **Payroll Finance approve** | ● | ○ | A | ○ | ○ | ○ |
| **Payroll CEO/Admin approve** | A | ○ | ○ | ○ | ○ | ○ |
| **Bank file download** | ● | ○ | R/C | ○ | ○ | ○ |
| View own payslip | ● | ● | ● | ● | ● | R |
| View all payslips | ● | ● | R | ○ | ○ | ○ |
| Tax certificate (own) | ● | ● | ● | ● | ● | R |
| Tax slab configuration | ● | R | CRUD | ○ | ○ | ○ |
| Bonus create | ● | C | R | ○ | ○ | ○ |
| Bonus approve | ● | A | A | ○ | ○ | ○ |
| Loan / advance create | ● | C | C | ○ | ○ | C* |
| Payroll audit trail | ● | R | R | ○ | ○ | ○ |

---

### MODULE 4: RECRUITMENT (ATS)

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Job posting create/edit | ● | CRUD | ○ | CRUD◐ | R | ○ |
| Job posting publish | ● | A | ○ | C◐ | ○ | ○ |
| Job posting close | ● | A | ○ | A◐ | ○ | ○ |
| View all applications | ● | ● | ○ | R | R◐ | ○ |
| View own referral application | ● | ● | ○ | ● | ● | R |
| Move application stage | ● | ● | ○ | ● | A◐ | ○ |
| Reject application | ● | A | ○ | A | A◐ | ○ |
| AI CV score trigger | ● | C | ○ | C | ○ | ○ |
| AI score view | ● | R | ○ | R | R | ○ |
| AI score override | ● | A | ○ | A | ○ | ○ |
| Schedule interview | ● | CRUD | ○ | CRUD | CRUD◐ | ○ |
| Interview feedback | ● | CRUD | ○ | CRUD | CRUD◐ | ○ |
| Offer letter generate | ● | C | C◐ | C | ○ | ○ |
| Offer approve / send | ● | A | A | ○ | ○ | ○ |
| Candidate database | ● | R | ○ | R | ○ | ○ |
| Recruitment analytics | ● | R | ○ | R | ○ | ○ |
| Referral tracking | ● | R | R | R | ○ | R* |
| External job board post | ● | C | ○ | C◐ | ○ | ○ |

---

### MODULE 5: LEAVE MANAGEMENT

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Apply leave (own) | ● | ● | ● | ● | ● | C |
| View own leave requests | ● | ● | ● | ● | ● | R |
| View team leave requests | ● | ● | ○ | ○ | R | ○ |
| View all leave requests | ● | R | ○ | ○ | ○ | ○ |
| Manager-level approve/reject | ● | A | ○ | ○ | A◐ | ○ |
| HR-level approve/reject | ● | A | ○ | ○ | ○ | ○ |
| Override leave status | ● | A | ○ | ○ | ○ | ○ |
| Cancel own leave | ● | ● | ● | ● | ● | D* |
| Leave balance (own) | ● | ● | ● | ● | ● | R |
| **Leave balance (all)** | ● | R | ○ | ○ | R◐ | ○ |
| Adjust leave balance | ● | CRUD | ○ | ○ | ○ | ○ |
| Leave types configure | ● | CRUD | ○ | ○ | ○ | ○ |
| Leave calendar (team) | ● | ● | ● | ● | R | R◐ |
| Blackout dates configure | ● | CRUD | ○ | ○ | ○ | ○ |
| Public holidays configure | ● | CRUD | ○ | ○ | ○ | ○ |
| Leave encashment process | ● | A | A | ○ | ○ | ○ |
| Leave report | ● | R | R◐ | ○ | R◐ | ○ |

---

### MODULE 6: PERFORMANCE MANAGEMENT

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Appraisal cycle create | ● | CRUD | ○ | ○ | ○ | ○ |
| Appraisal cycle advance stage | ● | A | ○ | ○ | ○ | ○ |
| Goal set (own) | ● | ● | ● | ● | ● | C |
| Goal set (team) | ● | ● | ○ | ○ | CRUD◐ | ○ |
| Goal update (own) | ● | ● | ● | ● | ● | U |
| Self-review submit | ● | ● | ● | ● | ● | C* |
| Manager review submit | ● | C | ○ | ○ | C◐ | ○ |
| Peer review submit | ● | C | C | C | C | C◐ |
| View own review | ● | ● | ● | ● | ● | R |
| **View team reviews** | ● | R | ○ | ○ | R◐ | ○ |
| **View all reviews** | ● | R | ○ | ○ | ○ | ○ |
| Finalize review | ● | A | ○ | ○ | A◐ | ○ |
| PIP create | ● | CRUD | ○ | ○ | C◐ | ○ |
| PIP milestone update | ● | U | ○ | ○ | U◐ | ○ |
| PIP close | ● | A | ○ | ○ | ○ | ○ |
| Increment recommend | ● | C | R | ○ | C◐ | ○ |
| **Increment approve** | ● | A | A | ○ | ○ | ○ |
| AI performance prediction | ● | R | ○ | ○ | R◐ | ○ |
| AI prediction override | ● | A | ○ | ○ | ○ | ○ |
| Bell curve report | ● | R | ○ | ○ | R◐ | ○ |

---

### MODULE 7: TRAINING & DEVELOPMENT

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Training catalog view | ● | ● | ● | ● | ● | R |
| Training program create | ● | CRUD | ○ | ○ | ○ | ○ |
| Training enroll (self) | ● | ● | ● | ● | ● | C* |
| Training enroll (team) | ● | CRUD | ○ | ○ | CRUD◐ | ○ |
| Mark training complete | ● | U | ○ | ○ | U◐ | ○ |
| Certificate generate | ● | C | ○ | ○ | C◐ | ○ |
| Skill matrix view | ● | R | ○ | ○ | R◐ | R* |
| Skill matrix edit | ● | CRUD | ○ | ○ | U◐ | ○ |
| Training cost view | ● | R | R | ○ | ○ | ○ |
| Training cost approve | ● | A | A | ○ | ○ | ○ |
| Compliance training assign | ● | CRUD | ○ | ○ | ○ | ○ |
| Training needs analysis | ● | R | ○ | ○ | R◐ | ○ |
| LMS integration manage | ● | CRUD | ○ | ○ | ○ | ○ |
| Training report | ● | R | R◐ | ○ | R◐ | R* |

---

### MODULE 8: SELF-SERVICE PORTAL

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| View own dashboard | ● | ● | ● | ● | ● | R |
| Update personal contact info | ● | ● | ● | ● | ● | U |
| Update own bank details | ● | ● | ● | ● | ● | U* |
| View own payslips | ● | ● | ● | ● | ● | R |
| Download tax certificate | ● | ● | ● | ● | ● | R |
| Apply leave | ● | ● | ● | ● | ● | C |
| Raise IT/HR/Admin request | ● | ● | ● | ● | ● | C |
| View announcements | ● | ● | ● | ● | ● | R |
| View org chart | ● | ● | ● | ● | ● | R |
| View team directory | ● | ● | ● | ● | ● | R |
| Request HR letter | ● | ● | ● | ● | ● | C |
| View own assets | ● | ● | ● | ● | ● | R |
| Submit raise request | ● | ● | ● | ● | ● | C |
| Manage notification prefs | ● | ● | ● | ● | ● | U |
| Change own password | ● | ● | ● | ● | ● | U |
| MFA setup | ● | ● | ● | ● | ● | CRUD |

---

### MODULE 9: ASSET MANAGEMENT

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Asset register view | ● | R | R | ○ | R◐ | R* |
| Asset create | ● | C | C | ○ | ○ | ○ |
| Asset edit | ● | U | U | ○ | ○ | ○ |
| Asset delete / decommission | ● | D | ○ | ○ | ○ | ○ |
| Asset assign to employee | ● | C | ○ | ○ | ○ | ○ |
| Asset return process | ● | A | ○ | ○ | ○ | ○ |
| View own assigned assets | ● | ● | ● | ● | ● | R |
| Report asset lost/damaged | ● | ● | ● | ● | ● | C |
| Asset depreciation view | ● | R | R | ○ | ○ | ○ |
| Maintenance schedule | ● | CRUD | R | ○ | ○ | ○ |
| Warranty alert | ● | R | R | ○ | ○ | ○ |
| Asset report | ● | R | R | ○ | R◐ | ○ |

---

### MODULE 10: OFFBOARDING

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Initiate offboarding | ● | C | ○ | ○ | C◐ | ○ |
| View offboarding checklist | ● | R | R◐ | ○ | R◐ | R* |
| Complete own dept clearance | ● | A | A◐ | ○ | A◐ | ○ |
| Exit interview (fill) | ● | ● | ● | ● | ● | C* |
| **Exit interview (view all)** | ● | R | ○ | ○ | ○ | ○ |
| AI sentiment view | ● | R | ○ | ○ | ○ | ○ |
| Final settlement calculate | ● | C | C | ○ | ○ | ○ |
| **Final settlement approve** | ● | A | A | ○ | ○ | ○ |
| Experience letter generate | ● | C | ○ | ○ | ○ | ○ |
| Relieving letter generate | ● | C | ○ | ○ | ○ | ○ |
| Knowledge transfer tasks | ● | CRUD | ○ | ○ | CRUD◐ | C◐ |
| System access revocation | ● | A | ○ | ○ | ○ | ○ |

---

### MODULE 11: COMPLIANCE & LEGAL

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Audit log view (all)** | R | R◐ | R◐ | ○ | ○ | ○ |
| **Audit log export** | C | ○ | ○ | ○ | ○ | ○ |
| GDPR erasure request process | A | A | ○ | ○ | ○ | ○ |
| Data retention config | CRUD | R | ○ | ○ | ○ | ○ |
| Policy document publish | ● | CRUD | ○ | ○ | ○ | ○ |
| Policy acknowledgement view | ● | R | ○ | ○ | ○ | ○ |
| Employee e-sign policy | ● | ● | ● | ● | ● | A |
| EOBI/SESSI report export | ● | C | C | ○ | ○ | ○ |
| Income tax filing export | ● | C | C | ○ | ○ | ○ |
| Contract expiry alert config | ● | CRUD | ○ | ○ | ○ | ○ |
| Labour law jurisdiction config | ● | CRUD | R | ○ | ○ | ○ |
| Consent management view | ● | R | ○ | ○ | ○ | ○ |
| Right-to-access request | ● | A | ○ | ○ | ○ | C* |

---

### MODULE 12: NOTIFICATIONS

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| View own notifications | ● | ● | ● | ● | ● | R |
| Manage own notification prefs | ● | ● | ● | ● | ● | CRUD |
| **Notification template create/edit** | CRUD | CRUD | ○ | ○ | ○ | ○ |
| Send broadcast notification | ● | C | ○ | ○ | C◐ | ○ |
| Notification delivery log | ● | R | ○ | ○ | ○ | ○ |
| Notification trigger config | ● | CRUD | ○ | ○ | ○ | ○ |
| WhatsApp bot config | ● | R | ○ | ○ | ○ | ○ |
| Override employee notification prefs | ● | A | ○ | ○ | ○ | ○ |

---

### MODULE 13: BI REPORTING & ANALYTICS

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Executive dashboard | R | R | R | ○ | R◐ | ○ |
| Headcount report | R | R | R◐ | ○ | R◐ | ○ |
| **Attrition report** | R | R | ○ | ○ | R◐ | ○ |
| **Salary distribution chart** | R | R | R | ○ | ○ | ○ |
| Cost-per-hire report | R | R | R | R | ○ | ○ |
| Custom report builder | ● | CRUD | CRUD◐ | CRUD◐ | CRUD◐ | ○ |
| Scheduled report create | ● | CRUD | CRUD◐ | CRUD◐ | ○ | ○ |
| AI NLQ query | ● | C | C◐ | ○ | ○ | ○ |
| Anomaly alert view | ● | R | R◐ | ○ | ○ | ○ |
| Report export (PDF/Excel) | ● | C | C | C◐ | C◐ | ○ |
| Data drill-down | ● | R | R◐ | R◐ | R◐ | ○ |

---

### MODULE 14: MOBILE APPLICATION

| Resource / Action | Super Admin | HR Manager | Finance | Recruiter | Dept Manager | Employee |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| Mobile check-in (GPS) | ● | ● | ● | ● | ● | C |
| Mobile leave apply | ● | ● | ● | ● | ● | C |
| Mobile payslip view | ● | ● | ● | ● | ● | R |
| Mobile push notifications | ● | ● | ● | ● | ● | R |
| Mobile team directory | ● | ● | ● | ● | ● | R |
| Mobile announcements | ● | ● | ● | ● | ● | R |
| Mobile biometric setup | ● | ● | ● | ● | ● | CRUD |
| Mobile approval actions | ● | A | A◐ | ○ | A◐ | ○ |
| Offline data sync | ● | ● | ● | ● | ● | R |
| **Mobile admin dashboard** | R | R | ○ | ○ | R◐ | ○ |

---

## 6.4 Field-Level Permission Details

### Salary & Compensation Fields
```
Field: basic_salary, gross_salary, net_salary, all allowances
  Visible to  : Super Admin, HR Manager, Finance
  Hidden from : Recruiter, Dept Manager, Employee (see own only)
  Own salary  : Employee can see their own in payslip view only

Field: bank_account_number, bank_iban
  Visible to  : Super Admin, HR Manager, Finance (masked: ****3456)
  Update by   : HR Manager, Finance (update), Employee (update own — triggers review)
  Hidden from : Recruiter, Dept Manager

Field: cnic_nid
  Visible to  : Super Admin, HR Manager
  Masked to   : Finance (shows *** 7-1 format)
  Hidden from : Recruiter, Dept Manager, Employee (cannot see own in list)

Field: performance_band, increment_percentage
  Visible to  : Super Admin, HR Manager, Dept Manager (own team)
  Hidden from : Peers, Employee (until formally communicated)
```

### FastAPI Field-Level RBAC Enforcement
```python
# schemas/employee.py
from pydantic import BaseModel, model_validator
from typing import Optional
from enum import Enum

class EmployeeRole(str, Enum):
    super_admin = "super_admin"
    hr_manager = "hr_manager"
    finance = "finance"
    recruiter = "recruiter"
    dept_manager = "dept_manager"
    employee = "employee"

# Field visibility matrix
FIELD_VISIBILITY = {
    "basic_salary":           {EmployeeRole.super_admin, EmployeeRole.hr_manager, EmployeeRole.finance},
    "gross_salary":           {EmployeeRole.super_admin, EmployeeRole.hr_manager, EmployeeRole.finance},
    "bank_account_number":    {EmployeeRole.super_admin, EmployeeRole.hr_manager, EmployeeRole.finance},
    "cnic_nid":               {EmployeeRole.super_admin, EmployeeRole.hr_manager},
    "grade_level":            {EmployeeRole.super_admin, EmployeeRole.hr_manager, EmployeeRole.finance},
    "cost_center":            {EmployeeRole.super_admin, EmployeeRole.hr_manager, EmployeeRole.finance},
    "performance_band":       {EmployeeRole.super_admin, EmployeeRole.hr_manager, EmployeeRole.dept_manager},
    "increment_percentage":   {EmployeeRole.super_admin, EmployeeRole.hr_manager, EmployeeRole.finance},
    "attrition_risk_score":   {EmployeeRole.super_admin, EmployeeRole.hr_manager},
}

def apply_field_mask(data: dict, viewer_role: EmployeeRole, viewer_id: str, subject_id: str) -> dict:
    """
    Mask fields the viewer is not permitted to see.
    viewer_id == subject_id means employee viewing own record (some extra fields visible).
    """
    masked = dict(data)
    is_own_record = (viewer_id == subject_id)

    for field, allowed_roles in FIELD_VISIBILITY.items():
        if viewer_role not in allowed_roles:
            if is_own_record and field in ("basic_salary", "gross_salary", "bank_account_number"):
                # Employee can see own salary and bank details (masked)
                if field == "bank_account_number" and masked.get(field):
                    masked[field] = "****" + str(masked[field])[-4:]
            else:
                masked[field] = None  # nullify restricted field

    return masked
```

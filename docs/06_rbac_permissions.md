# Section 6: User Roles & Permissions Matrix

## 6.1 Role Definitions

| Role | Code | Description |
|------|------|-------------|
| Super Admin | `SUPER_ADMIN` | Platform-level admin — full access to all tenants and system config |
| HR Manager | `HR_MANAGER` | Full HR operations access within their tenant |
| Finance Manager | `FINANCE_MANAGER` | Payroll approval, financial reports, salary data |
| Recruiter | `RECRUITER` | Full ATS access, limited employee data |
| Department Manager | `DEPT_MANAGER` | Own department: attendance, leave, performance, limited employee data |
| Employee | `EMPLOYEE` | Self-service only — own data |
| IT Admin | `IT_ADMIN` | Asset management, system access revocation |
| Read-Only HR | `HR_READONLY` | Read access to HR data (no sensitive financial) |
| Payroll Admin | `PAYROLL_ADMIN` | Payroll execution without strategic HR access |

---

## 6.2 Full RBAC Matrix

Legend: `C` = Create, `R` = Read, `U` = Update, `D` = Delete, `A` = Approve, `X` = No Access, `O` = Own only

### MODULE 1: Employee Management

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Create employee | C | C | X | X | X | X | X |
| View employee list | R | R | R (salary visible) | R (no salary) | R (own dept, no salary) | X | R (asset fields) |
| View own profile | R | R | R | R | R | R | R |
| View other's full profile | R | R | R (finance fields) | R (basic only) | R (own dept, no salary) | X | R (basic) |
| View salary details | R | R | R | X | X | X | X |
| View CNIC/passport | R | R | X | X | X | O (own) | X |
| View bank details | R | X | R | X | X | O (own) | X |
| Update personal info | U | U | X | X | X | U (limited fields) | X |
| Update employment info | U | U | X | X | X | X | X |
| Update compensation | U | U | U | X | X | X | X |
| Bulk import employees | C | C | X | X | X | X | X |
| Export employee list | R | R | R | X | R (own dept) | X | X |
| Delete (soft) employee | D | X | X | X | X | X | X |
| View org chart | R | R | R | R | R | R | R |
| Manage documents | CRUD | CRUD | R | X | R | O (upload own) | R |

### MODULE 2: Attendance

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Check in/out | C | C | C | C | C | C | C |
| View own attendance | R | R | R | R | R | R | R |
| View team attendance | R | R | X | X | R (own dept) | X | X |
| View all attendance | R | R | X | X | X | X | X |
| Manual override | U | U | X | X | U (own dept) | X | X |
| Configure shifts | CRUD | CRUD | X | X | X | X | X |
| View live dashboard | R | R | X | X | R (own dept) | X | X |
| Export reports | R | R | X | X | R (own dept) | X | X |
| Configure geofences | CRUD | CRUD | X | X | X | X | X |

### MODULE 3: Payroll

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Initiate payroll run | C | C | X | X | X | X | X |
| View payroll runs | R | R | R | X | X | X | X |
| Approve payroll (HR stage) | A | A | X | X | X | X | X |
| Approve payroll (Finance) | A | X | A | X | X | X | X |
| Approve payroll (CEO) | A | X | X | X | X | X | X |
| View own payslip | R | R | R | R | R | R | R |
| View others' payslips | R | R | R | X | X | X | X |
| View salary amounts | R | R | R | X | X | O (own) | X |
| Generate bank file | C | X | C | X | X | X | X |
| Configure salary structures | CRUD | CRUD | CRUD | X | X | X | X |
| Configure tax slabs | CRUD | CRUD | CRUD | X | X | X | X |
| Payroll audit trail | R | R | R | X | X | X | X |
| Year-end tax certificates | C | C | C | X | X | O (own download) | X |

### MODULE 4: Recruitment

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Create job posting | C | C | X | C | C (request only) | X | X |
| Publish job externally | C | C | X | C | X | X | X |
| View all applications | R | R | X | R | R (own dept postings) | X | X |
| Move application stage | U | U | X | U | U (own dept) | X | X |
| AI CV scoring | C | C | X | C | X | X | X |
| Schedule interviews | C | C | X | C | C | X | X |
| Send offer letter | C | C | X | C (draft only) | X | X | X |
| Approve offer | A | A | X | X | X | X | X |
| View candidate data | R | R | X | R | R (own dept) | X | X |
| Internal referral | C | C | X | C | C | C | X |
| View referral bonus | R | R | R | X | X | O (own) | X |
| Recruitment analytics | R | R | X | R | R (own dept) | X | X |

### MODULE 5: Leave

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Apply for leave | C | C | C | C | C | C | C |
| View own leave requests | R | R | R | R | R | R | R |
| View team leave | R | R | X | X | R (own team) | X | X |
| View all leave | R | R | X | X | X | X | X |
| Approve leave (Manager stage) | A | A | X | X | A (own team) | X | X |
| Approve leave (HR stage) | A | A | X | X | X | X | X |
| Override approved leave | U | U | X | X | X | X | X |
| Configure leave types | CRUD | CRUD | X | X | X | X | X |
| Manage leave balances | CRUD | CRUD | X | X | X | X | X |
| Configure public holidays | CRUD | CRUD | X | X | X | X | X |
| Leave encashment | C | C | C | X | X | X | X |
| View leave reports | R | R | R | X | R (own dept) | X | X |

### MODULE 6: Performance

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Create review cycle | C | C | X | X | X | X | X |
| Set own goals | C | C | C | C | C | C | X |
| Set team goals | C | C | X | X | C | X | X |
| Submit self-review | C | C | C | C | C | C | X |
| Submit manager review | C | C | X | X | C (own team) | X | X |
| Submit peer review | C | C | X | X | C | C | X |
| View own reviews | R | R | R | R | R | R | X |
| View team reviews | R | R | X | X | R (own team) | X | X |
| View all reviews | R | R | X | X | X | X | X |
| Bell curve / calibration | R | R | X | X | X | X | X |
| Create PIP | C | C | X | X | C (own team, HR approval) | X | X |
| Increment/promotion decisions | C | C | C (salary impact) | X | C (recommend only) | X | X |
| AI performance predictions | R | R | X | X | R (own team) | X | X |
| View fairness reports | R | R | X | X | X | X | X |

### MODULE 7: Training

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Create training program | C | C | X | X | X | X | X |
| Enroll employees | C | C | X | X | C (own team) | O (self) | X |
| Mark completion | U | U | X | X | U (own team) | X | X |
| Generate certificates | C | C | X | X | X | X | X |
| View skill matrix | R | R | X | X | R (own dept) | O (own) | X |
| Training cost reports | R | R | R | X | R (own dept, no $) | X | X |
| Configure mandatory training | CRUD | CRUD | X | X | X | X | X |

### MODULE 8: Self-Service

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| View own dashboard | R | R | R | R | R | R | R |
| Raise request | C | C | C | C | C | C | C |
| View own requests | R | R | R | R | R | R | R |
| Handle requests (assign) | U | U | X | X | U (own dept) | X | U (IT requests) |
| Request HR letter | C | C | C | C | C | C | C |
| View announcements | R | R | R | R | R | R | R |
| Post announcements | C | C | X | X | C (own dept) | X | X |
| View company directory | R | R | R | R | R | R | R |

### MODULE 9: Asset Management

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Add asset to register | C | C | X | X | X | X | C |
| Assign asset | C | C | X | X | X | X | C |
| Return asset | C | C | X | X | X | O (request) | C |
| Report damage/loss | C | C | X | X | X | C (own assets) | C |
| View all assets | R | R | R | X | R (own dept) | O (own) | R |
| Depreciation reports | R | R | R | X | X | X | X |
| Maintenance schedule | CRUD | X | X | X | X | X | CRUD |

### MODULE 10: Offboarding

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Initiate offboarding | C | C | X | X | X | X | X |
| View offboarding status | R | R | R (settlement) | X | R (own emp) | O (own) | R (IT tasks) |
| Complete clearance tasks | U | U | U (finance tasks) | X | U (dept tasks) | X | U (IT tasks) |
| Calculate final settlement | C | C | C | X | X | X | X |
| Approve final settlement | A | A | A | X | X | X | X |
| Generate relieving letter | C | C | X | X | X | X | X |
| Exit interview analysis | R | R | X | X | X | X | X |
| Revoke system access | C | X | X | X | X | X | C |

### MODULE 11: Compliance

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| View audit logs | R | R (own module) | R (payroll audit) | X | X | X | X |
| Export audit logs | R | X | X | X | X | X | X |
| Manage data erasure | CRUD | X | X | X | X | X | X |
| View GDPR consents | R | R | X | X | X | O (own) | X |
| Configure data retention | CRUD | X | X | X | X | X | X |
| Regulatory reports | R | R | R | X | X | X | X |
| Policy acknowledgement track | R | R | X | X | X | O (own) | X |

### MODULE 12: Notifications

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Configure templates | CRUD | CRUD | X | X | X | X | X |
| View delivery logs | R | R (own module) | R (payroll) | X | X | X | X |
| Update own preferences | U | U | U | U | U | U | U |
| Send manual notifications | C | C | C (finance) | X | C (own dept) | X | X |

### MODULE 13: Analytics

| Action | SUPER_ADMIN | HR_MANAGER | FINANCE_MGR | RECRUITER | DEPT_MGR | EMPLOYEE | IT_ADMIN |
|--------|------------|------------|-------------|-----------|----------|----------|----------|
| Executive dashboard | R | R | R (financial KPIs) | X | R (own dept) | X | X |
| Custom report builder | CRUD | CRUD | CRUD (finance) | R (recruitment) | R (own dept) | X | X |
| NLQ analytics | C | C | C (finance queries) | X | C (own dept) | X | X |
| Schedule reports | CRUD | CRUD | CRUD (own) | X | X | X | X |
| AI anomaly alerts | R | R | X | X | X | X | X |
| Attrition dashboard | R | R | X | X | R (own dept) | X | X |
| Salary benchmarking | R | R | R | X | X | X | X |

---

## 6.3 Field-Level Access Control

Implemented as Pydantic response models with role-based field inclusion:

```python
class EmployeeResponseBase(BaseModel):
    id: UUID
    employee_code: str
    full_name: str
    work_email: str
    department: DepartmentSummary
    job_grade: JobGradeSummary
    status: str

class EmployeeResponseEmployee(EmployeeResponseBase):
    """Employee sees own data — no salary"""
    personal_email: Optional[str]
    phone_primary: Optional[str]
    address_line1: Optional[str]
    bank_account_number: str = Field(default="****", description="Masked")

class EmployeeResponseHR(EmployeeResponseBase):
    """HR sees most fields"""
    national_id: str          # Decrypted for HR
    base_salary: Decimal      # Visible to HR
    bank_account_number: str  # Visible to HR
    salary_structure: SalaryStructure

class EmployeeResponseFinance(EmployeeResponseHR):
    """Finance also sees bank routing details"""
    bank_iban: str
    bank_branch_code: str

def get_employee_response_model(role: str) -> type:
    role_models = {
        "EMPLOYEE": EmployeeResponseEmployee,
        "DEPT_MANAGER": EmployeeResponseBase,
        "HR_MANAGER": EmployeeResponseHR,
        "FINANCE_MANAGER": EmployeeResponseFinance,
        "SUPER_ADMIN": EmployeeResponseFinance,
    }
    return role_models.get(role, EmployeeResponseBase)
```

---

## 6.4 Resource-Level Access (Row Security)

```python
# Department Manager can only see own department employees
async def check_resource_access(
    user: AuthUser,
    resource_employee_id: UUID,
    db: AsyncSession
) -> bool:
    if user.role == "SUPER_ADMIN" or user.role == "HR_MANAGER":
        return True

    if user.role == "DEPT_MANAGER":
        # Check if target employee is in user's department
        result = await db.execute(
            select(Employee.department_id)
            .where(Employee.id == resource_employee_id)
        )
        target_dept = result.scalar()
        return target_dept == user.department_id

    if user.role == "EMPLOYEE":
        # Employees can only access own data
        return resource_employee_id == user.employee_id

    return False
```

---

## 6.5 Permission Codes Reference

Format: `module:action[:scope]`

```
employee:create
employee:read:all
employee:read:own_dept
employee:read:own
employee:update:all
employee:update:own
employee:update:compensation
employee:delete
employee:export

attendance:checkin:own
attendance:read:all
attendance:read:own_dept
attendance:override

payroll:run
payroll:approve:hr
payroll:approve:finance
payroll:approve:ceo
payroll:read:all
payroll:read:own_payslip
payroll:bankfile:generate

leave:apply
leave:approve:manager
leave:approve:hr
leave:read:all
leave:configure

recruitment:create
recruitment:publish
recruitment:score:ai
recruitment:offer:send

performance:review:submit
performance:review:read:own
performance:review:read:team
performance:calibrate
performance:pip:create

compliance:audit:read
compliance:erasure:process

analytics:executive
analytics:nlq
analytics:export
```

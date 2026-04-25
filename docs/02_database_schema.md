# Section 2: Database Schema

## 2.1 ERD Overview — Entity Relationships

```
CORE ENTITIES AND RELATIONSHIPS:

departments ──< employees >── job_titles
     │               │
     │               ├──< attendance_records
     │               ├──< leave_requests >── leave_types
     │               ├──< payroll_records >── salary_structures
     │               ├──< performance_reviews
     │               ├──< training_enrollments >── training_programs
     │               ├──< assets (assigned)
     │               ├──< job_applications (employee referrals)
     │               └──< audit_logs
     │
job_postings ──< job_applications >── candidates
                       │
                       └──< interview_schedules

leave_requests >── approval_workflows >── workflow_steps

payroll_records >── payroll_components
payroll_run >── payroll_records

performance_reviews >── review_responses
performance_reviews >── kpi_goals

notification_logs >── notification_templates
```

---

## 2.2 Full SQL Schema

```sql
-- ============================================================
-- ENUMERATIONS
-- ============================================================

CREATE TYPE employee_status AS ENUM (
    'onboarding', 'probation', 'confirmed', 'active',
    'on_leave', 'suspended', 'offboarding', 'terminated', 'resigned'
);

CREATE TYPE contract_type AS ENUM (
    'permanent', 'contract', 'internship', 'part_time', 'freelance', 'consultant'
);

CREATE TYPE gender AS ENUM ('male', 'female', 'other', 'prefer_not_to_say');

CREATE TYPE leave_status AS ENUM (
    'draft', 'pending', 'approved_by_manager', 'approved', 'rejected',
    'cancelled', 'auto_approved'
);

CREATE TYPE payroll_status AS ENUM (
    'draft', 'processing', 'pending_hr', 'pending_finance', 'pending_ceo',
    'approved', 'bank_file_generated', 'paid', 'cancelled'
);

CREATE TYPE job_stage AS ENUM (
    'applied', 'screened', 'phone_screen', 'interview_scheduled',
    'interviewed', 'offered', 'offer_accepted', 'hired',
    'rejected', 'withdrawn', 'on_hold'
);

CREATE TYPE asset_status AS ENUM (
    'available', 'assigned', 'under_maintenance', 'disposed', 'lost'
);

CREATE TYPE notification_channel AS ENUM ('email', 'sms', 'in_app', 'whatsapp', 'push');

CREATE TYPE review_type AS ENUM ('self', 'manager', 'peer', 'subordinate', '360');

CREATE TYPE risk_tier AS ENUM ('low', 'medium', 'high', 'critical');

-- ============================================================
-- TABLE 1: TENANTS (Multi-tenancy)
-- ============================================================

CREATE TABLE tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug                VARCHAR(100) UNIQUE NOT NULL,  -- acme-corp
    legal_name          VARCHAR(255) NOT NULL,
    display_name        VARCHAR(255) NOT NULL,
    country_code        CHAR(2) NOT NULL DEFAULT 'PK',
    timezone            VARCHAR(100) NOT NULL DEFAULT 'Asia/Karachi',
    currency_code       CHAR(3) NOT NULL DEFAULT 'PKR',
    locale              VARCHAR(10) NOT NULL DEFAULT 'en',
    subscription_tier   VARCHAR(50) NOT NULL DEFAULT 'professional',
    max_employees       INTEGER NOT NULL DEFAULT 500,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    settings            JSONB NOT NULL DEFAULT '{}',
    -- settings includes: fiscal_year_start, working_days, overtime_rules,
    --                     probation_days, gratuity_formula, tax_slabs
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);

-- ============================================================
-- TABLE 2: DEPARTMENTS
-- ============================================================

CREATE TABLE departments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name                VARCHAR(255) NOT NULL,
    code                VARCHAR(50),                  -- ENG, HR, FIN
    parent_id           UUID REFERENCES departments(id),  -- self-referencing for sub-depts
    head_employee_id    UUID,                         -- FK set after employees table created
    cost_center_code    VARCHAR(50),
    location            VARCHAR(255),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, code)
);

CREATE INDEX idx_departments_tenant ON departments(tenant_id);
CREATE INDEX idx_departments_parent ON departments(parent_id);

-- ============================================================
-- TABLE 3: JOB TITLES / GRADES
-- ============================================================

CREATE TABLE job_grades (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    title               VARCHAR(255) NOT NULL,
    grade_code          VARCHAR(20),                  -- L1, L2, M1, M2, SM
    min_salary          NUMERIC(15,2),
    max_salary          NUMERIC(15,2),
    currency_code       CHAR(3) DEFAULT 'PKR',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(tenant_id, grade_code)
);

-- ============================================================
-- TABLE 4: EMPLOYEES (Core Entity)
-- ============================================================

CREATE TABLE employees (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    employee_code               VARCHAR(50) NOT NULL,   -- EMP-0001

    -- Personal Information
    first_name                  VARCHAR(100) NOT NULL,
    last_name                   VARCHAR(100) NOT NULL,
    preferred_name              VARCHAR(100),
    date_of_birth               DATE,
    gender                      gender,
    nationality                 CHAR(2),                -- ISO country code
    national_id                 BYTEA,                  -- AES-256 encrypted CNIC/NID
    passport_number             BYTEA,                  -- Encrypted
    passport_expiry             DATE,

    -- Contact Information
    personal_email              VARCHAR(255),
    work_email                  VARCHAR(255) NOT NULL,
    phone_primary               VARCHAR(30),
    phone_secondary             VARCHAR(30),
    address_line1               VARCHAR(255),
    address_line2               VARCHAR(255),
    city                        VARCHAR(100),
    state_province              VARCHAR(100),
    postal_code                 VARCHAR(20),
    country_code                CHAR(2),

    -- Emergency Contact
    emergency_contact_name      VARCHAR(200),
    emergency_contact_relation  VARCHAR(100),
    emergency_contact_phone     VARCHAR(30),

    -- Employment Details
    department_id               UUID REFERENCES departments(id),
    job_grade_id                UUID REFERENCES job_grades(id),
    reporting_manager_id        UUID REFERENCES employees(id),
    location                    VARCHAR(255),
    contract_type               contract_type NOT NULL DEFAULT 'permanent',
    status                      employee_status NOT NULL DEFAULT 'onboarding',

    -- Dates
    hire_date                   DATE NOT NULL,
    probation_end_date          DATE,
    confirmation_date           DATE,
    resignation_date            DATE,
    last_working_date           DATE,

    -- Compensation (sensitive — field-level access control enforced in API)
    base_salary                 BYTEA,                  -- Encrypted
    salary_currency             CHAR(3) DEFAULT 'PKR',
    salary_structure_id         UUID,                   -- FK to salary_structures
    bank_account_number         BYTEA,                  -- Encrypted
    bank_name                   VARCHAR(100),
    bank_branch_code            VARCHAR(50),
    bank_iban                   BYTEA,                  -- Encrypted

    -- System
    user_account_id             UUID UNIQUE,            -- FK to auth.users
    profile_photo_url           VARCHAR(500),
    biometric_device_id         VARCHAR(100),           -- ZKTeco enrollment ID
    timezone                    VARCHAR(100),
    locale                      VARCHAR(10),
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metadata
    created_by                  UUID,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, employee_code),
    UNIQUE(tenant_id, work_email)
);

CREATE INDEX idx_employees_tenant ON employees(tenant_id);
CREATE INDEX idx_employees_dept ON employees(department_id);
CREATE INDEX idx_employees_manager ON employees(reporting_manager_id);
CREATE INDEX idx_employees_status ON employees(status);
CREATE INDEX idx_employees_hire_date ON employees(hire_date);
CREATE INDEX idx_employees_fullname ON employees(tenant_id, last_name, first_name);

-- After employees table, add FK for department head
ALTER TABLE departments
    ADD CONSTRAINT fk_dept_head
    FOREIGN KEY (head_employee_id) REFERENCES employees(id);

-- ============================================================
-- TABLE 5: ATTENDANCE RECORDS
-- ============================================================

CREATE TABLE attendance_records (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    employee_id         UUID NOT NULL REFERENCES employees(id),
    attendance_date     DATE NOT NULL,

    -- Clock times
    check_in_time       TIMESTAMPTZ,
    check_out_time      TIMESTAMPTZ,
    check_in_source     VARCHAR(50),    -- biometric, mobile_gps, manual, web
    check_out_source    VARCHAR(50),

    -- GPS data (for geo-fence punch)
    check_in_latitude   DECIMAL(10,8),
    check_in_longitude  DECIMAL(11,8),
    check_out_latitude  DECIMAL(10,8),
    check_out_longitude DECIMAL(11,8),
    geofence_valid      BOOLEAN,        -- Was punch within allowed radius?

    -- Computed fields (updated by Celery EOD job)
    shift_id            UUID,           -- FK to shifts
    scheduled_in        TIME,
    scheduled_out       TIME,
    working_hours       NUMERIC(5,2),   -- Actual hours worked
    overtime_hours      NUMERIC(5,2) DEFAULT 0,
    late_minutes        INTEGER DEFAULT 0,
    early_leave_minutes INTEGER DEFAULT 0,
    is_present          BOOLEAN,
    is_holiday          BOOLEAN DEFAULT FALSE,
    is_weekend          BOOLEAN DEFAULT FALSE,

    -- Status
    status              VARCHAR(50) DEFAULT 'present',
    -- present, absent, half_day, on_leave, holiday, weekend, work_from_home

    notes               TEXT,
    approved_by         UUID REFERENCES employees(id),
    manual_override     BOOLEAN DEFAULT FALSE,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, employee_id, attendance_date)
);

CREATE INDEX idx_attendance_employee_date ON attendance_records(employee_id, attendance_date);
CREATE INDEX idx_attendance_tenant_date ON attendance_records(tenant_id, attendance_date);
CREATE INDEX idx_attendance_date ON attendance_records(attendance_date);

-- ============================================================
-- TABLE 6: PAYROLL RUNS
-- ============================================================

CREATE TABLE payroll_runs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    run_code            VARCHAR(50) NOT NULL,           -- PR-2024-01
    pay_period_start    DATE NOT NULL,
    pay_period_end      DATE NOT NULL,
    payment_date        DATE NOT NULL,
    currency_code       CHAR(3) NOT NULL DEFAULT 'PKR',

    status              payroll_status NOT NULL DEFAULT 'draft',

    -- Totals (computed)
    total_employees     INTEGER DEFAULT 0,
    total_gross         NUMERIC(18,2) DEFAULT 0,
    total_deductions    NUMERIC(18,2) DEFAULT 0,
    total_net           NUMERIC(18,2) DEFAULT 0,
    total_tax           NUMERIC(18,2) DEFAULT 0,

    -- Approval workflow
    submitted_by        UUID REFERENCES employees(id),
    submitted_at        TIMESTAMPTZ,
    hr_approved_by      UUID REFERENCES employees(id),
    hr_approved_at      TIMESTAMPTZ,
    finance_approved_by UUID REFERENCES employees(id),
    finance_approved_at TIMESTAMPTZ,
    ceo_approved_by     UUID REFERENCES employees(id),
    ceo_approved_at     TIMESTAMPTZ,

    -- Bank file
    bank_file_url       VARCHAR(500),
    bank_file_generated_at TIMESTAMPTZ,

    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, run_code)
);

CREATE INDEX idx_payroll_runs_tenant ON payroll_runs(tenant_id);
CREATE INDEX idx_payroll_runs_period ON payroll_runs(pay_period_start, pay_period_end);
CREATE INDEX idx_payroll_runs_status ON payroll_runs(status);

-- ============================================================
-- TABLE 7: PAYROLL RECORDS (Per-Employee Per-Run)
-- ============================================================

CREATE TABLE payroll_records (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    payroll_run_id          UUID NOT NULL REFERENCES payroll_runs(id),
    employee_id             UUID NOT NULL REFERENCES employees(id),

    -- Working data
    working_days            INTEGER NOT NULL,
    present_days            NUMERIC(5,1) NOT NULL,
    leave_days              NUMERIC(5,1) DEFAULT 0,
    absent_days             NUMERIC(5,1) DEFAULT 0,
    overtime_hours          NUMERIC(6,2) DEFAULT 0,

    -- Earnings (all encrypted in production)
    basic_salary            NUMERIC(15,2) NOT NULL,
    hra                     NUMERIC(15,2) DEFAULT 0,     -- House rent allowance
    transport_allowance     NUMERIC(15,2) DEFAULT 0,
    medical_allowance       NUMERIC(15,2) DEFAULT 0,
    meal_allowance          NUMERIC(15,2) DEFAULT 0,
    other_allowances        JSONB DEFAULT '{}',          -- {"field_allowance": 5000}
    performance_bonus       NUMERIC(15,2) DEFAULT 0,
    overtime_pay            NUMERIC(15,2) DEFAULT 0,
    arrears                 NUMERIC(15,2) DEFAULT 0,
    gross_salary            NUMERIC(15,2) NOT NULL,

    -- Deductions
    income_tax              NUMERIC(15,2) DEFAULT 0,
    eobi_employee           NUMERIC(15,2) DEFAULT 0,     -- Employee contribution
    eobi_employer           NUMERIC(15,2) DEFAULT 0,     -- Employer contribution
    sessi_employee          NUMERIC(15,2) DEFAULT 0,
    sessi_employer          NUMERIC(15,2) DEFAULT 0,
    loan_deduction          NUMERIC(15,2) DEFAULT 0,
    advance_deduction       NUMERIC(15,2) DEFAULT 0,
    absent_deduction        NUMERIC(15,2) DEFAULT 0,
    late_deduction          NUMERIC(15,2) DEFAULT 0,
    other_deductions        JSONB DEFAULT '{}',
    total_deductions        NUMERIC(15,2) NOT NULL,

    net_salary              NUMERIC(15,2) NOT NULL,
    currency_code           CHAR(3) NOT NULL DEFAULT 'PKR',

    -- Bank transfer
    bank_account_number     BYTEA,                       -- Encrypted snapshot
    bank_name               VARCHAR(100),
    transfer_status         VARCHAR(50) DEFAULT 'pending',
    transfer_reference      VARCHAR(100),

    -- Payslip
    payslip_url             VARCHAR(500),
    payslip_generated_at    TIMESTAMPTZ,

    -- Calculation metadata
    calculation_log         JSONB,                       -- Step-by-step breakdown
    tax_slab_applied        VARCHAR(100),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(payroll_run_id, employee_id)
);

CREATE INDEX idx_payroll_records_run ON payroll_records(payroll_run_id);
CREATE INDEX idx_payroll_records_employee ON payroll_records(employee_id);
CREATE INDEX idx_payroll_records_tenant ON payroll_records(tenant_id);

-- ============================================================
-- TABLE 8: LEAVE REQUESTS
-- ============================================================

CREATE TABLE leave_types (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    name                VARCHAR(100) NOT NULL,           -- Annual Leave
    code                VARCHAR(20) NOT NULL,            -- AL, SL, CL, ML, PL
    days_per_year       NUMERIC(5,1) NOT NULL,
    carry_forward_max   NUMERIC(5,1) DEFAULT 0,
    is_paid             BOOLEAN DEFAULT TRUE,
    gender_restriction  gender,                          -- null=all, female=maternity
    min_tenure_months   INTEGER DEFAULT 0,
    requires_docs       BOOLEAN DEFAULT FALSE,           -- Sick leave > 2 days needs cert
    notice_days_required INTEGER DEFAULT 0,
    encashable          BOOLEAN DEFAULT FALSE,
    is_active           BOOLEAN DEFAULT TRUE,
    UNIQUE(tenant_id, code)
);

CREATE TABLE leave_balances (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    employee_id         UUID NOT NULL REFERENCES employees(id),
    leave_type_id       UUID NOT NULL REFERENCES leave_types(id),
    year                INTEGER NOT NULL,
    entitled_days       NUMERIC(5,1) NOT NULL,
    taken_days          NUMERIC(5,1) DEFAULT 0,
    pending_days        NUMERIC(5,1) DEFAULT 0,         -- Applied but not yet approved
    carried_forward     NUMERIC(5,1) DEFAULT 0,
    encashed_days       NUMERIC(5,1) DEFAULT 0,
    balance_days        NUMERIC(5,1) GENERATED ALWAYS AS
                            (entitled_days + carried_forward - taken_days - pending_days - encashed_days)
                        STORED,
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, employee_id, leave_type_id, year)
);

CREATE TABLE leave_requests (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    request_number      VARCHAR(50) NOT NULL,            -- LR-2024-001234
    employee_id         UUID NOT NULL REFERENCES employees(id),
    leave_type_id       UUID NOT NULL REFERENCES leave_types(id),

    start_date          DATE NOT NULL,
    end_date            DATE NOT NULL,
    total_days          NUMERIC(5,1) NOT NULL,
    is_half_day         BOOLEAN DEFAULT FALSE,
    half_day_period     VARCHAR(10),                     -- morning, afternoon

    reason              TEXT,
    attachment_url      VARCHAR(500),

    status              leave_status NOT NULL DEFAULT 'pending',

    -- Approval chain
    manager_id          UUID REFERENCES employees(id),
    manager_action      VARCHAR(20),                     -- approved, rejected
    manager_action_at   TIMESTAMPTZ,
    manager_comments    TEXT,

    hr_id               UUID REFERENCES employees(id),
    hr_action           VARCHAR(20),
    hr_action_at        TIMESTAMPTZ,
    hr_comments         TEXT,

    -- Cancellation
    cancelled_by        UUID REFERENCES employees(id),
    cancelled_at        TIMESTAMPTZ,
    cancellation_reason TEXT,

    -- AI metadata
    conflict_detected   BOOLEAN DEFAULT FALSE,
    conflict_details    JSONB,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, request_number)
);

CREATE INDEX idx_leave_requests_employee ON leave_requests(employee_id);
CREATE INDEX idx_leave_requests_dates ON leave_requests(start_date, end_date);
CREATE INDEX idx_leave_requests_status ON leave_requests(status);
CREATE INDEX idx_leave_requests_manager ON leave_requests(manager_id, status);

-- ============================================================
-- TABLE 9: JOB POSTINGS
-- ============================================================

CREATE TABLE job_postings (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    posting_code        VARCHAR(50) NOT NULL,            -- JP-2024-001

    title               VARCHAR(255) NOT NULL,
    department_id       UUID REFERENCES departments(id),
    job_grade_id        UUID REFERENCES job_grades(id),
    location            VARCHAR(255),
    employment_type     contract_type NOT NULL DEFAULT 'permanent',

    description         TEXT NOT NULL,
    requirements        TEXT,
    responsibilities    TEXT,
    nice_to_have        TEXT,

    salary_min          NUMERIC(15,2),
    salary_max          NUMERIC(15,2),
    currency_code       CHAR(3) DEFAULT 'PKR',
    show_salary         BOOLEAN DEFAULT FALSE,

    vacancies           INTEGER DEFAULT 1,
    applications_count  INTEGER DEFAULT 0,

    status              VARCHAR(50) DEFAULT 'draft',
    -- draft, open, paused, closed, cancelled

    published_at        TIMESTAMPTZ,
    closes_at           TIMESTAMPTZ,

    -- External posting flags
    post_to_linkedin    BOOLEAN DEFAULT FALSE,
    post_to_indeed      BOOLEAN DEFAULT FALSE,
    linkedin_job_id     VARCHAR(100),
    indeed_job_key      VARCHAR(100),

    -- Internal referral
    referral_bonus      NUMERIC(10,2) DEFAULT 0,

    -- AI: JD embedding for CV matching
    description_embedding VECTOR(1536),                  -- pgvector

    hiring_manager_id   UUID REFERENCES employees(id),
    created_by          UUID REFERENCES employees(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, posting_code)
);

CREATE INDEX idx_job_postings_tenant ON job_postings(tenant_id);
CREATE INDEX idx_job_postings_status ON job_postings(status);
CREATE INDEX idx_job_postings_embedding ON job_postings USING ivfflat (description_embedding vector_cosine_ops);

-- ============================================================
-- TABLE 10: JOB APPLICATIONS (Candidates)
-- ============================================================

CREATE TABLE candidates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),

    -- Personal
    first_name          VARCHAR(100) NOT NULL,
    last_name           VARCHAR(100) NOT NULL,
    email               VARCHAR(255) NOT NULL,
    phone               VARCHAR(30),

    -- Parsed CV data
    cv_url              VARCHAR(500),
    cv_text             TEXT,                            -- Extracted text
    cv_embedding        VECTOR(1536),                    -- For similarity search
    parsed_skills       TEXT[],
    parsed_experience_years NUMERIC(4,1),
    parsed_education    JSONB,                           -- [{degree, institution, year}]
    parsed_certifications TEXT[],
    current_employer    VARCHAR(255),
    current_title       VARCHAR(255),
    current_salary      NUMERIC(15,2),
    expected_salary     NUMERIC(15,2),

    source              VARCHAR(100),                    -- linkedin, indeed, referral, direct
    referred_by         UUID REFERENCES employees(id),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, email)
);

CREATE TABLE job_applications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    application_code    VARCHAR(50) NOT NULL,
    job_posting_id      UUID NOT NULL REFERENCES job_postings(id),
    candidate_id        UUID NOT NULL REFERENCES candidates(id),

    stage               job_stage NOT NULL DEFAULT 'applied',
    applied_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- AI scoring
    ai_score            NUMERIC(5,2),                    -- 0-100
    ai_score_breakdown  JSONB,
    -- {"skills_match": 90, "experience_match": 80, "education_match": 70,
    --  "overall": 84, "explanation": "...", "bias_flags": []}
    ai_scored_at        TIMESTAMPTZ,

    -- HR notes
    hr_rating           INTEGER CHECK (hr_rating BETWEEN 1 AND 5),
    hr_notes            TEXT,

    -- Stage-specific data
    rejection_reason    VARCHAR(255),
    offer_amount        NUMERIC(15,2),
    offer_sent_at       TIMESTAMPTZ,
    offer_accepted_at   TIMESTAMPTZ,
    offer_document_url  VARCHAR(500),

    -- Referral
    referral_bonus_paid BOOLEAN DEFAULT FALSE,
    referral_bonus_amount NUMERIC(10,2),

    -- Converted to employee
    converted_employee_id UUID REFERENCES employees(id),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, application_code),
    UNIQUE(job_posting_id, candidate_id)
);

CREATE INDEX idx_job_applications_posting ON job_applications(job_posting_id);
CREATE INDEX idx_job_applications_candidate ON job_applications(candidate_id);
CREATE INDEX idx_job_applications_stage ON job_applications(stage);

-- ============================================================
-- TABLE 11: PERFORMANCE REVIEWS
-- ============================================================

CREATE TABLE review_cycles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    name                VARCHAR(255) NOT NULL,           -- Q1 2024 Review
    cycle_type          VARCHAR(50) NOT NULL,            -- quarterly, annual, mid_year
    review_period_start DATE NOT NULL,
    review_period_end   DATE NOT NULL,
    goal_setting_deadline DATE,
    self_review_deadline  DATE,
    manager_review_deadline DATE,
    calibration_date    DATE,
    status              VARCHAR(50) DEFAULT 'planning',
    -- planning, goal_setting, self_review, peer_review, manager_review,
    -- calibration, completed
    rating_scale        JSONB NOT NULL DEFAULT '[1,2,3,4,5]',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE kpi_goals (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    employee_id         UUID NOT NULL REFERENCES employees(id),
    review_cycle_id     UUID NOT NULL REFERENCES review_cycles(id),

    title               VARCHAR(255) NOT NULL,
    description         TEXT,
    goal_type           VARCHAR(50) DEFAULT 'kpi',      -- kpi, okr, development
    category            VARCHAR(100),                    -- Sales, Quality, Leadership

    target_value        NUMERIC(15,4),
    actual_value        NUMERIC(15,4),
    unit                VARCHAR(50),                     -- %, $, count, hours
    weight              NUMERIC(5,2) DEFAULT 1.0,        -- Relative importance

    target_date         DATE,
    status              VARCHAR(50) DEFAULT 'active',   -- active, achieved, missed, cancelled

    self_rating         NUMERIC(3,1),
    manager_rating      NUMERIC(3,1),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE performance_reviews (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    review_cycle_id     UUID NOT NULL REFERENCES review_cycles(id),
    employee_id         UUID NOT NULL REFERENCES employees(id),
    reviewer_id         UUID NOT NULL REFERENCES employees(id),
    review_type         review_type NOT NULL,

    -- Ratings
    overall_rating      NUMERIC(3,1),
    competency_ratings  JSONB,
    -- {"leadership": 4.0, "communication": 3.5, "technical": 5.0, ...}

    -- Qualitative
    strengths           TEXT,
    areas_for_improvement TEXT,
    development_plan    TEXT,
    comments            TEXT,

    -- Goals achievement score
    goals_achievement_pct NUMERIC(5,2),

    status              VARCHAR(50) DEFAULT 'draft',
    -- draft, submitted, acknowledged, calibrated, final

    submitted_at        TIMESTAMPTZ,
    acknowledged_by_employee_at TIMESTAMPTZ,

    -- AI prediction
    predicted_next_cycle_band VARCHAR(20),              -- High, Medium, Low
    prediction_confidence NUMERIC(4,3),

    -- PIP
    pip_initiated       BOOLEAN DEFAULT FALSE,
    pip_id              UUID,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(review_cycle_id, employee_id, reviewer_id, review_type)
);

CREATE INDEX idx_perf_reviews_employee ON performance_reviews(employee_id);
CREATE INDEX idx_perf_reviews_cycle ON performance_reviews(review_cycle_id);

-- ============================================================
-- TABLE 12: ASSETS
-- ============================================================

CREATE TABLE assets (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    asset_code          VARCHAR(100) NOT NULL,           -- LAP-001, PHN-023

    asset_type          VARCHAR(100) NOT NULL,           -- laptop, phone, access_card
    brand               VARCHAR(100),
    model               VARCHAR(100),
    serial_number       VARCHAR(200),
    purchase_date       DATE,
    purchase_price      NUMERIC(12,2),
    warranty_expiry     DATE,

    -- Current state
    status              asset_status NOT NULL DEFAULT 'available',
    assigned_to         UUID REFERENCES employees(id),
    assigned_at         TIMESTAMPTZ,
    condition           VARCHAR(50),                     -- new, good, fair, poor
    condition_photos    TEXT[],                          -- S3 URLs

    -- Depreciation
    depreciation_method VARCHAR(50) DEFAULT 'straight_line',
    useful_life_years   INTEGER,
    current_value       NUMERIC(12,2),
    last_depreciation_date DATE,

    notes               TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, asset_code)
);

-- ============================================================
-- TABLE 13: AUDIT LOGS (Immutable — append only)
-- ============================================================

CREATE TABLE audit_logs (
    id                  BIGSERIAL PRIMARY KEY,           -- Integer for performance
    tenant_id           UUID NOT NULL,

    -- Actor
    user_id             UUID,
    employee_id         UUID,
    user_email          VARCHAR(255),
    user_role           VARCHAR(100),
    ip_address          INET,
    user_agent          TEXT,
    session_id          VARCHAR(255),

    -- Action
    action              VARCHAR(100) NOT NULL,
    -- CREATE, READ, UPDATE, DELETE, LOGIN, LOGOUT, EXPORT, APPROVE, REJECT, etc.

    -- Target
    resource_type       VARCHAR(100) NOT NULL,           -- employee, payroll, leave, etc.
    resource_id         UUID,
    resource_code       VARCHAR(100),

    -- Change details
    old_values          JSONB,                           -- Previous state (sensitive fields masked)
    new_values          JSONB,                           -- New state
    changed_fields      TEXT[],                          -- Which fields changed

    -- Context
    module              VARCHAR(100),
    endpoint            VARCHAR(255),
    http_method         VARCHAR(10),

    -- AI decisions
    ai_decision         JSONB,                           -- If action was AI-triggered
    human_override      BOOLEAN DEFAULT FALSE,
    override_reason     TEXT,

    -- Timing
    duration_ms         INTEGER,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()

    -- NOTE: No UPDATE or DELETE on this table. Enforced via:
    -- 1. RLS: REVOKE UPDATE, DELETE ON audit_logs FROM app_user;
    -- 2. Trigger: DENY any UPDATE/DELETE
    -- 3. Partitioned by month for performance: audit_logs_2024_01, etc.
);

CREATE INDEX idx_audit_logs_tenant_time ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action, created_at DESC);

-- Partition by month
CREATE TABLE audit_logs_2024_01 PARTITION OF audit_logs
    FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');
-- (auto-created by pg_partman extension)

-- Prevent modifications
CREATE RULE no_update_audit AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE no_delete_audit AS ON DELETE TO audit_logs DO INSTEAD NOTHING;

-- ============================================================
-- TABLE 14: NOTIFICATIONS
-- ============================================================

CREATE TABLE notification_templates (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID,                            -- null = system template
    code                VARCHAR(100) UNIQUE NOT NULL,    -- LEAVE_APPROVED, PAYSLIP_READY
    name                VARCHAR(255) NOT NULL,
    channels            notification_channel[] NOT NULL,
    subject_template    TEXT,                            -- Email subject with {{variables}}
    body_template_html  TEXT,                            -- HTML email body
    body_template_text  TEXT,                            -- Plain text / SMS
    whatsapp_template   TEXT,                            -- WhatsApp Business API template
    variables           TEXT[],                          -- Required variable names
    is_active           BOOLEAN DEFAULT TRUE
);

CREATE TABLE notification_logs (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    template_code       VARCHAR(100) NOT NULL,
    channel             notification_channel NOT NULL,

    recipient_employee_id UUID REFERENCES employees(id),
    recipient_email     VARCHAR(255),
    recipient_phone     VARCHAR(30),

    subject             TEXT,
    body                TEXT,

    status              VARCHAR(50) DEFAULT 'pending',   -- pending, sent, delivered, failed, read
    sent_at             TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    read_at             TIMESTAMPTZ,
    failed_reason       TEXT,

    retry_count         INTEGER DEFAULT 0,
    next_retry_at       TIMESTAMPTZ,

    -- External message IDs
    sendgrid_message_id VARCHAR(255),
    twilio_sid          VARCHAR(255),
    fcm_message_id      VARCHAR(255),

    metadata            JSONB,                           -- Template variables used
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notif_logs_employee ON notification_logs(recipient_employee_id);
CREATE INDEX idx_notif_logs_status ON notification_logs(status, next_retry_at);
CREATE INDEX idx_notif_logs_created ON notification_logs(created_at DESC);

-- ============================================================
-- TABLE 15: ATTRITION RISK SCORES (AI Output)
-- ============================================================

CREATE TABLE attrition_risk_scores (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    employee_id         UUID NOT NULL REFERENCES employees(id),

    risk_score          NUMERIC(5,2) NOT NULL,           -- 0-100
    risk_tier           risk_tier NOT NULL,

    -- Top contributing factors (SHAP values)
    top_factors         JSONB NOT NULL,
    -- [{"factor": "low_salary_vs_market", "contribution": 0.35, "value": -18000},
    --  {"factor": "no_promotion_36months", "contribution": 0.28, "value": 36},
    --  {"factor": "high_absenteeism", "contribution": 0.15, "value": 4.2}]

    -- Recommended interventions
    recommendations     JSONB,
    -- [{"action": "salary_review", "priority": "high", "expected_impact": "reduce_risk_by_20pct"}]

    model_version       VARCHAR(50) NOT NULL,
    computed_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    alert_sent          BOOLEAN DEFAULT FALSE,
    alert_sent_at       TIMESTAMPTZ,

    -- HR response
    hr_reviewed         BOOLEAN DEFAULT FALSE,
    hr_reviewed_by      UUID REFERENCES employees(id),
    hr_action_taken     TEXT,

    -- Was the prediction correct?
    employee_left       BOOLEAN,
    left_within_90_days BOOLEAN,

    UNIQUE(employee_id, computed_at::DATE)
);

CREATE INDEX idx_attrition_scores_tenant ON attrition_risk_scores(tenant_id, risk_tier);
CREATE INDEX idx_attrition_scores_employee ON attrition_risk_scores(employee_id, computed_at DESC);
```

---

## 2.3 Additional Supporting Tables

```sql
-- Salary Structures
CREATE TABLE salary_structures (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    name            VARCHAR(255) NOT NULL,
    components      JSONB NOT NULL,
    -- [{"code": "BASIC", "name": "Basic Salary", "type": "fixed", "value": 50000},
    --  {"code": "HRA", "name": "House Rent", "type": "percentage", "basis": "BASIC", "value": 45},
    --  {"code": "TRANSPORT", "name": "Transport", "type": "fixed", "value": 5000}]
    tax_config      JSONB,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Shifts
CREATE TABLE shifts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    name            VARCHAR(100) NOT NULL,               -- Morning, Evening, Night
    start_time      TIME NOT NULL,
    end_time        TIME NOT NULL,
    is_overnight    BOOLEAN DEFAULT FALSE,
    break_minutes   INTEGER DEFAULT 60,
    grace_minutes   INTEGER DEFAULT 10,                  -- Late arrival grace period
    night_allowance NUMERIC(10,2) DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE
);

-- Training Programs
CREATE TABLE training_programs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    type            VARCHAR(50),                         -- internal, external, elearning
    category        VARCHAR(100),                        -- technical, soft_skills, compliance
    provider        VARCHAR(255),
    cost_per_seat   NUMERIC(10,2),
    duration_hours  NUMERIC(6,2),
    is_mandatory    BOOLEAN DEFAULT FALSE,
    mandatory_roles TEXT[],                              -- ["all"] or specific roles
    completion_certificate BOOLEAN DEFAULT FALSE,
    passing_score   INTEGER,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE training_enrollments (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    program_id          UUID NOT NULL REFERENCES training_programs(id),
    employee_id         UUID NOT NULL REFERENCES employees(id),
    enrolled_at         TIMESTAMPTZ DEFAULT NOW(),
    deadline            TIMESTAMPTZ,
    status              VARCHAR(50) DEFAULT 'enrolled',
    -- enrolled, in_progress, completed, failed, expired
    score               NUMERIC(5,2),
    completed_at        TIMESTAMPTZ,
    certificate_url     VARCHAR(500),
    UNIQUE(program_id, employee_id)
);

-- Documents
CREATE TABLE employee_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    employee_id     UUID NOT NULL REFERENCES employees(id),
    doc_type        VARCHAR(100) NOT NULL,               -- passport, visa, certificate, contract
    title           VARCHAR(255) NOT NULL,
    file_url        VARCHAR(500) NOT NULL,
    file_size_bytes INTEGER,
    version         INTEGER DEFAULT 1,
    issue_date      DATE,
    expiry_date     DATE,
    issuing_authority VARCHAR(255),
    verified        BOOLEAN DEFAULT FALSE,
    verified_by     UUID REFERENCES employees(id),
    notes           TEXT,
    uploaded_by     UUID REFERENCES employees(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_emp_docs_expiry ON employee_documents(expiry_date)
    WHERE expiry_date IS NOT NULL;
```

---

## 2.4 PostgreSQL Extensions Required

```sql
-- Run once on database creation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";    -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";     -- AES-256 encryption functions
CREATE EXTENSION IF NOT EXISTS "vector";       -- pgvector for AI embeddings
CREATE EXTENSION IF NOT EXISTS "pg_partman";   -- Auto partition management
CREATE EXTENSION IF NOT EXISTS "pg_trgm";      -- Trigram indexes for LIKE search
CREATE EXTENSION IF NOT EXISTS "btree_gin";    -- GIN indexes for JSONB
CREATE EXTENSION IF NOT EXISTS "citext";       -- Case-insensitive text type

-- Example: Encrypting sensitive data
INSERT INTO employees (national_id)
VALUES (pgp_sym_encrypt('3520212345678', current_setting('app.encryption_key')));

-- Decrypting (only in authorized queries)
SELECT pgp_sym_decrypt(national_id::bytea, current_setting('app.encryption_key'))
FROM employees WHERE id = $1;
```

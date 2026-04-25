# SECTION 2 — DATABASE SCHEMA

## 2.1 Design Principles
- Every table has `tenant_id UUID NOT NULL` for multi-tenant isolation
- Every table has `created_at`, `updated_at` timestamps
- Soft deletes via `deleted_at TIMESTAMPTZ` (no hard deletes on sensitive HR data)
- Sensitive columns (salary, CNIC, bank account) encrypted at application layer (AES-256)
  before storage — stored as BYTEA or TEXT with `_encrypted` suffix convention
- UUID primary keys (no sequential int PKs — avoids enumeration attacks)
- Row-level security (PostgreSQL RLS) as defense-in-depth for tenant isolation

## 2.2 SQL CREATE TABLE Statements

```sql
-- ─────────────────────────────────────────────────────────────────────────────
-- EXTENSIONS
-- ─────────────────────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";  -- pgvector for AI embeddings

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: tenants
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE tenants (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) NOT NULL,
    slug                VARCHAR(100) UNIQUE NOT NULL,  -- used in URL/subdomain
    legal_entity_name   VARCHAR(255),
    country             VARCHAR(100) NOT NULL DEFAULT 'Pakistan',
    currency            VARCHAR(10) NOT NULL DEFAULT 'PKR',
    timezone            VARCHAR(100) NOT NULL DEFAULT 'Asia/Karachi',
    subscription_tier   VARCHAR(50) NOT NULL DEFAULT 'standard'
                            CHECK (subscription_tier IN ('starter','standard','enterprise')),
    max_employees       INTEGER NOT NULL DEFAULT 500,
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    settings            JSONB NOT NULL DEFAULT '{}',    -- tenant-level config
    logo_url            TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at          TIMESTAMPTZ
);

CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_active ON tenants(is_active) WHERE is_active = TRUE;

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: departments
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE departments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    name            VARCHAR(255) NOT NULL,
    code            VARCHAR(50) NOT NULL,
    parent_id       UUID REFERENCES departments(id),   -- self-referencing for hierarchy
    head_id         UUID,                               -- FK to employees (circular — set after)
    cost_center     VARCHAR(100),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at      TIMESTAMPTZ,
    UNIQUE (tenant_id, code)
);

CREATE INDEX idx_departments_tenant ON departments(tenant_id);
CREATE INDEX idx_departments_parent ON departments(parent_id);
CREATE INDEX idx_departments_head ON departments(head_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: branches
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE branches (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,
    name            VARCHAR(255) NOT NULL,
    code            VARCHAR(50) NOT NULL,
    address_line1   VARCHAR(255),
    address_line2   VARCHAR(255),
    city            VARCHAR(100),
    state_province  VARCHAR(100),
    postal_code     VARCHAR(20),
    country         VARCHAR(100) NOT NULL DEFAULT 'Pakistan',
    timezone        VARCHAR(100) NOT NULL DEFAULT 'Asia/Karachi',
    phone           VARCHAR(50),
    is_headquarters BOOLEAN NOT NULL DEFAULT FALSE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, code)
);

CREATE INDEX idx_branches_tenant ON branches(tenant_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: employees (core — most sensitive table)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE employees (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id) ON DELETE RESTRICT,

    -- Identity
    employee_number             VARCHAR(50) NOT NULL,
    first_name                  VARCHAR(100) NOT NULL,
    middle_name                 VARCHAR(100),
    last_name                   VARCHAR(100) NOT NULL,
    full_name                   VARCHAR(300) GENERATED ALWAYS AS
                                    (first_name || ' ' || COALESCE(middle_name || ' ', '') || last_name)
                                    STORED,
    date_of_birth               DATE,
    gender                      VARCHAR(30) CHECK (gender IN ('male','female','other','prefer_not_to_say')),
    marital_status              VARCHAR(30) CHECK (marital_status IN ('single','married','divorced','widowed')),
    nationality                 VARCHAR(100),
    cnic_nid_encrypted          TEXT,                   -- AES-256 encrypted
    cnic_expiry                 DATE,
    profile_photo_url           TEXT,

    -- Contact
    personal_email              VARCHAR(255),
    work_email                  VARCHAR(255),
    phone_primary               VARCHAR(50),
    phone_secondary             VARCHAR(50),

    -- Address
    address_line1               VARCHAR(255),
    address_line2               VARCHAR(255),
    city                        VARCHAR(100),
    state_province              VARCHAR(100),
    postal_code                 VARCHAR(20),
    country                     VARCHAR(100) DEFAULT 'Pakistan',

    -- Emergency Contact
    emergency_contact_name      VARCHAR(255),
    emergency_contact_relation  VARCHAR(100),
    emergency_contact_phone     VARCHAR(50),
    emergency_contact_email     VARCHAR(255),

    -- Employment
    department_id               UUID REFERENCES departments(id),
    branch_id                   UUID REFERENCES branches(id),
    reporting_manager_id        UUID REFERENCES employees(id),  -- self-referencing
    designation                 VARCHAR(255),
    grade_level                 VARCHAR(50),
    cost_center                 VARCHAR(100),
    contract_type               VARCHAR(50) NOT NULL DEFAULT 'permanent'
                                    CHECK (contract_type IN ('permanent','fixed_term','probation','intern','consultant')),
    work_schedule               VARCHAR(50) DEFAULT 'full_time'
                                    CHECK (work_schedule IN ('full_time','part_time','remote','hybrid')),
    work_location               VARCHAR(50) DEFAULT 'office'
                                    CHECK (work_location IN ('office','remote','hybrid','field')),
    timezone                    VARCHAR(100) DEFAULT 'Asia/Karachi',
    shift_id                    UUID,                    -- FK to shifts

    -- Lifecycle
    joining_date                DATE,
    probation_end_date          DATE,
    confirmation_date           DATE,
    lifecycle_status            VARCHAR(50) NOT NULL DEFAULT 'onboarding'
                                    CHECK (lifecycle_status IN
                                        ('onboarding','probation','confirmed','active','on_leave',
                                         'suspended','offboarding','terminated','resigned')),

    -- Notice Period
    notice_period_days          INTEGER DEFAULT 30,

    -- System
    user_id                     UUID UNIQUE,             -- FK to users (auth)
    is_active                   BOOLEAN NOT NULL DEFAULT TRUE,
    created_by                  UUID,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at                  TIMESTAMPTZ,
    UNIQUE (tenant_id, employee_number),
    UNIQUE (tenant_id, work_email)
);

CREATE INDEX idx_employees_tenant ON employees(tenant_id);
CREATE INDEX idx_employees_dept ON employees(department_id);
CREATE INDEX idx_employees_branch ON employees(branch_id);
CREATE INDEX idx_employees_manager ON employees(reporting_manager_id);
CREATE INDEX idx_employees_status ON employees(lifecycle_status);
CREATE INDEX idx_employees_active ON employees(tenant_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_employees_fullname ON employees USING gin(to_tsvector('english', full_name));
CREATE INDEX idx_employees_joining ON employees(joining_date);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: employee_compensation
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE employee_compensation (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    employee_id             UUID NOT NULL REFERENCES employees(id),

    -- Salary (all encrypted at application layer, stored as text)
    currency                VARCHAR(10) NOT NULL DEFAULT 'PKR',
    basic_salary_encrypted  TEXT NOT NULL,
    hra_encrypted           TEXT DEFAULT '0',
    medical_allowance_encrypted TEXT DEFAULT '0',
    transport_allowance_encrypted TEXT DEFAULT '0',
    fuel_allowance_encrypted TEXT DEFAULT '0',
    utility_allowance_encrypted TEXT DEFAULT '0',
    other_allowances_encrypted TEXT DEFAULT '0',

    -- Deductions
    eobi_applicable         BOOLEAN DEFAULT TRUE,
    sessi_applicable        BOOLEAN DEFAULT FALSE,
    income_tax_applicable   BOOLEAN DEFAULT TRUE,
    salary_structure_id     UUID,

    -- Bank Details (all encrypted)
    bank_name               VARCHAR(255),
    bank_account_title      VARCHAR(255),
    bank_account_number_encrypted TEXT,
    bank_iban_encrypted     TEXT,
    bank_branch_code        VARCHAR(50),
    payment_method          VARCHAR(50) DEFAULT 'bank_transfer'
                                CHECK (payment_method IN ('bank_transfer','cash','cheque')),

    -- Versioning
    effective_date          DATE NOT NULL,
    end_date                DATE,
    is_current              BOOLEAN NOT NULL DEFAULT TRUE,
    revision_reason         TEXT,
    approved_by             UUID REFERENCES employees(id),
    approved_at             TIMESTAMPTZ,

    created_by              UUID,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_compensation_employee ON employee_compensation(employee_id);
CREATE INDEX idx_compensation_current ON employee_compensation(employee_id, is_current)
    WHERE is_current = TRUE;
CREATE INDEX idx_compensation_tenant ON employee_compensation(tenant_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: attendance_records
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE attendance_records (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    employee_id         UUID NOT NULL REFERENCES employees(id),
    attendance_date     DATE NOT NULL,

    -- Check-in/out
    check_in_time       TIMESTAMPTZ,
    check_out_time      TIMESTAMPTZ,
    check_in_method     VARCHAR(50) CHECK (check_in_method IN
                            ('manual','biometric','geo_fence','mobile','kiosk','admin_override')),
    check_out_method    VARCHAR(50) CHECK (check_out_method IN
                            ('manual','biometric','geo_fence','mobile','kiosk','admin_override')),

    -- Location
    check_in_latitude   DECIMAL(10, 8),
    check_in_longitude  DECIMAL(11, 8),
    check_out_latitude  DECIMAL(10, 8),
    check_out_longitude DECIMAL(11, 8),
    geofence_status     VARCHAR(30) CHECK (geofence_status IN ('within','outside','not_checked')),

    -- Biometric
    device_id           VARCHAR(100),
    biometric_verified  BOOLEAN DEFAULT FALSE,
    face_match_score    DECIMAL(5, 4),

    -- Computed fields
    total_hours         DECIMAL(5, 2) GENERATED ALWAYS AS (
                            CASE
                                WHEN check_in_time IS NOT NULL AND check_out_time IS NOT NULL
                                THEN EXTRACT(EPOCH FROM (check_out_time - check_in_time)) / 3600
                                ELSE NULL
                            END
                        ) STORED,
    late_minutes        INTEGER DEFAULT 0,
    early_leave_minutes INTEGER DEFAULT 0,
    overtime_minutes    INTEGER DEFAULT 0,

    -- Status
    status              VARCHAR(50) NOT NULL DEFAULT 'present'
                            CHECK (status IN ('present','absent','late','half_day','on_leave',
                                             'holiday','weekend','work_from_home','field_work')),
    is_regularized      BOOLEAN DEFAULT FALSE,
    regularization_reason TEXT,
    regularized_by      UUID REFERENCES employees(id),
    regularized_at      TIMESTAMPTZ,

    -- Shift
    shift_id            UUID,
    expected_start_time TIME,
    expected_end_time   TIME,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, employee_id, attendance_date)
);

CREATE INDEX idx_attendance_tenant_date ON attendance_records(tenant_id, attendance_date);
CREATE INDEX idx_attendance_employee_date ON attendance_records(employee_id, attendance_date);
CREATE INDEX idx_attendance_status ON attendance_records(status);
CREATE INDEX idx_attendance_month ON attendance_records(
    tenant_id, date_trunc('month', attendance_date)
);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: payroll_runs
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE payroll_runs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    run_code            VARCHAR(50) NOT NULL,           -- e.g. PR-2024-01
    period_month        INTEGER NOT NULL CHECK (period_month BETWEEN 1 AND 12),
    period_year         INTEGER NOT NULL,
    currency            VARCHAR(10) NOT NULL DEFAULT 'PKR',

    -- Scope
    scope_type          VARCHAR(50) DEFAULT 'all'
                            CHECK (scope_type IN ('all','department','branch','custom')),
    scope_department_id UUID REFERENCES departments(id),
    scope_branch_id     UUID REFERENCES branches(id),
    employee_count      INTEGER DEFAULT 0,

    -- Status
    status              VARCHAR(50) NOT NULL DEFAULT 'draft'
                            CHECK (status IN ('draft','processing','calculated',
                                             'pending_hr','pending_finance','pending_ceo',
                                             'approved','bank_file_generated','paid','cancelled')),

    -- Totals (computed, stored for audit)
    total_gross_salary  DECIMAL(15, 2) DEFAULT 0,
    total_deductions    DECIMAL(15, 2) DEFAULT 0,
    total_net_salary    DECIMAL(15, 2) DEFAULT 0,
    total_tax           DECIMAL(15, 2) DEFAULT 0,
    total_eobi          DECIMAL(15, 2) DEFAULT 0,

    -- Approval workflow
    submitted_by        UUID REFERENCES employees(id),
    submitted_at        TIMESTAMPTZ,
    hr_approved_by      UUID REFERENCES employees(id),
    hr_approved_at      TIMESTAMPTZ,
    finance_approved_by UUID REFERENCES employees(id),
    finance_approved_at TIMESTAMPTZ,
    ceo_approved_by     UUID REFERENCES employees(id),
    ceo_approved_at     TIMESTAMPTZ,
    rejected_by         UUID REFERENCES employees(id),
    rejected_at         TIMESTAMPTZ,
    rejection_reason    TEXT,

    -- Bank file
    bank_file_url       TEXT,
    bank_file_generated_at TIMESTAMPTZ,
    payment_date        DATE,

    notes               TEXT,
    created_by          UUID,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, run_code)
);

CREATE INDEX idx_payroll_runs_tenant ON payroll_runs(tenant_id);
CREATE INDEX idx_payroll_runs_period ON payroll_runs(tenant_id, period_year, period_month);
CREATE INDEX idx_payroll_runs_status ON payroll_runs(status);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: payroll_records (one row per employee per payroll run)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE payroll_records (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id                   UUID NOT NULL REFERENCES tenants(id),
    payroll_run_id              UUID NOT NULL REFERENCES payroll_runs(id),
    employee_id                 UUID NOT NULL REFERENCES employees(id),

    -- Working days
    working_days                INTEGER NOT NULL DEFAULT 0,
    present_days                DECIMAL(5, 2) DEFAULT 0,
    absent_days                 DECIMAL(5, 2) DEFAULT 0,
    leave_days                  DECIMAL(5, 2) DEFAULT 0,
    holiday_days                INTEGER DEFAULT 0,

    -- Earnings (stored as JSONB for full auditability + flexibility)
    earnings                    JSONB NOT NULL DEFAULT '{}',
    -- {
    --   "basic": 100000, "hra": 40000, "medical": 10000,
    --   "transport": 5000, "fuel": 0, "overtime": 2000,
    --   "festival_bonus": 0, "performance_bonus": 0
    -- }

    -- Deductions (JSONB)
    deductions                  JSONB NOT NULL DEFAULT '{}',
    -- {
    --   "income_tax": 8500, "eobi": 370, "sessi": 0,
    --   "loan_deduction": 5000, "advance_recovery": 0,
    --   "other": 0
    -- }

    -- Totals
    gross_salary                DECIMAL(15, 2) NOT NULL DEFAULT 0,
    total_deductions            DECIMAL(15, 2) NOT NULL DEFAULT 0,
    net_salary                  DECIMAL(15, 2) NOT NULL DEFAULT 0,

    -- Tax
    taxable_income              DECIMAL(15, 2) DEFAULT 0,
    tax_slab_applied            VARCHAR(100),
    ytd_tax_paid                DECIMAL(15, 2) DEFAULT 0,

    -- Payslip
    payslip_pdf_url             TEXT,
    payslip_sent_at             TIMESTAMPTZ,

    -- Status
    status                      VARCHAR(50) DEFAULT 'calculated'
                                    CHECK (status IN ('calculated','approved','paid','cancelled','on_hold')),
    on_hold_reason              TEXT,

    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, payroll_run_id, employee_id)
);

CREATE INDEX idx_payroll_records_run ON payroll_records(payroll_run_id);
CREATE INDEX idx_payroll_records_employee ON payroll_records(employee_id);
CREATE INDEX idx_payroll_records_tenant ON payroll_records(tenant_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: leave_types
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE leave_types (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    name                    VARCHAR(100) NOT NULL,
    code                    VARCHAR(50) NOT NULL,
    color                   VARCHAR(7) DEFAULT '#3B82F6',  -- hex color for calendar
    annual_allocation       DECIMAL(5, 2) DEFAULT 0,
    max_consecutive_days    INTEGER,
    carry_forward_allowed   BOOLEAN DEFAULT FALSE,
    carry_forward_max_days  DECIMAL(5, 2) DEFAULT 0,
    encashment_allowed      BOOLEAN DEFAULT FALSE,
    requires_document       BOOLEAN DEFAULT FALSE,        -- e.g. medical cert for sick leave
    gender_restriction      VARCHAR(20) CHECK (gender_restriction IN ('all','male','female')),
    min_service_days        INTEGER DEFAULT 0,            -- must have worked X days to use
    notice_required_days    INTEGER DEFAULT 0,            -- apply X days in advance
    applicable_employee_types VARCHAR(200) DEFAULT 'all', -- JSON array of contract types
    is_paid                 BOOLEAN DEFAULT TRUE,
    is_active               BOOLEAN DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, code)
);

CREATE INDEX idx_leave_types_tenant ON leave_types(tenant_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: leave_requests
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE leave_requests (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    employee_id             UUID NOT NULL REFERENCES employees(id),
    leave_type_id           UUID NOT NULL REFERENCES leave_types(id),

    -- Dates
    start_date              DATE NOT NULL,
    end_date                DATE NOT NULL,
    total_days              DECIMAL(5, 2) NOT NULL,
    is_half_day             BOOLEAN DEFAULT FALSE,
    half_day_period         VARCHAR(20) CHECK (half_day_period IN ('morning','afternoon')),

    -- Request
    reason                  TEXT,
    document_url            TEXT,                         -- medical cert etc.

    -- Approval workflow
    status                  VARCHAR(50) NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','manager_approved','hr_approved',
                                                  'approved','rejected','cancelled','auto_approved')),
    submitted_at            TIMESTAMPTZ DEFAULT NOW(),

    -- Level 1: Line Manager
    manager_id              UUID REFERENCES employees(id),
    manager_action          VARCHAR(20) CHECK (manager_action IN ('approved','rejected','delegated')),
    manager_actioned_at     TIMESTAMPTZ,
    manager_comments        TEXT,

    -- Level 2: HR
    hr_approver_id          UUID REFERENCES employees(id),
    hr_action               VARCHAR(20) CHECK (hr_action IN ('approved','rejected')),
    hr_actioned_at          TIMESTAMPTZ,
    hr_comments             TEXT,

    -- Rejection
    rejection_reason        TEXT,

    -- Contact during leave
    contact_during_leave    VARCHAR(255),
    handover_notes          TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_leave_requests_tenant ON leave_requests(tenant_id);
CREATE INDEX idx_leave_requests_employee ON leave_requests(employee_id);
CREATE INDEX idx_leave_requests_status ON leave_requests(status);
CREATE INDEX idx_leave_requests_dates ON leave_requests(start_date, end_date);
CREATE INDEX idx_leave_requests_pending ON leave_requests(tenant_id, status)
    WHERE status IN ('pending', 'manager_approved');

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: job_postings
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE job_postings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    job_code                VARCHAR(50) NOT NULL,
    title                   VARCHAR(255) NOT NULL,
    department_id           UUID REFERENCES departments(id),
    branch_id               UUID REFERENCES branches(id),
    reporting_manager_id    UUID REFERENCES employees(id),

    -- Job Details
    description             TEXT,
    requirements            TEXT,
    responsibilities        TEXT,
    employment_type         VARCHAR(50) CHECK (employment_type IN
                                ('full_time','part_time','contract','intern','remote')),
    experience_min_years    DECIMAL(4, 1) DEFAULT 0,
    experience_max_years    DECIMAL(4, 1),
    education_required      VARCHAR(100),
    skills_required         TEXT[],                       -- array of skills
    skills_preferred        TEXT[],

    -- Compensation
    salary_currency         VARCHAR(10) DEFAULT 'PKR',
    salary_min              DECIMAL(15, 2),
    salary_max              DECIMAL(15, 2),
    show_salary             BOOLEAN DEFAULT FALSE,

    -- Status
    status                  VARCHAR(50) NOT NULL DEFAULT 'draft'
                                CHECK (status IN ('draft','open','paused','closed','filled','cancelled')),
    openings_count          INTEGER DEFAULT 1,
    filled_count            INTEGER DEFAULT 0,
    deadline                DATE,

    -- External posting
    post_to_linkedin        BOOLEAN DEFAULT FALSE,
    linkedin_post_id        VARCHAR(255),
    post_to_indeed          BOOLEAN DEFAULT FALSE,
    indeed_post_id          VARCHAR(255),
    is_internal_only        BOOLEAN DEFAULT FALSE,

    -- Analytics
    view_count              INTEGER DEFAULT 0,
    application_count       INTEGER DEFAULT 0,

    published_at            TIMESTAMPTZ,
    closed_at               TIMESTAMPTZ,
    created_by              UUID REFERENCES employees(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, job_code)
);

CREATE INDEX idx_job_postings_tenant ON job_postings(tenant_id);
CREATE INDEX idx_job_postings_status ON job_postings(status);
CREATE INDEX idx_job_postings_dept ON job_postings(department_id);
CREATE INDEX idx_job_postings_fts ON job_postings
    USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')));

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: job_applications
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE job_applications (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    job_posting_id          UUID NOT NULL REFERENCES job_postings(id),

    -- Candidate
    candidate_id            UUID,                         -- FK to candidates table
    first_name              VARCHAR(100) NOT NULL,
    last_name               VARCHAR(100) NOT NULL,
    email                   VARCHAR(255) NOT NULL,
    phone                   VARCHAR(50),
    current_designation     VARCHAR(255),
    current_employer        VARCHAR(255),
    total_experience_years  DECIMAL(4, 1) DEFAULT 0,
    expected_salary         DECIMAL(15, 2),
    notice_period_days      INTEGER,
    location                VARCHAR(255),

    -- CV
    cv_url                  TEXT,
    cv_parsed_data          JSONB DEFAULT '{}',           -- NLP-extracted structured data
    cover_letter            TEXT,

    -- AI Scoring
    ai_score                DECIMAL(5, 2),                -- 0-100
    ai_score_breakdown      JSONB DEFAULT '{}',           -- {"skills": 90, "exp": 80, ...}
    ai_explanation          TEXT,
    ai_bias_flags           JSONB DEFAULT '{}',
    ai_scored_at            TIMESTAMPTZ,

    -- Pipeline Stage
    stage                   VARCHAR(50) NOT NULL DEFAULT 'applied'
                                CHECK (stage IN ('applied','screening','phone_screen',
                                               'technical_test','interview_1','interview_2',
                                               'interview_final','offered','hired',
                                               'rejected','withdrawn')),
    rejection_reason        VARCHAR(255),
    rejection_stage         VARCHAR(50),

    -- Source
    source                  VARCHAR(100),                 -- linkedin, indeed, referral, direct
    referral_employee_id    UUID REFERENCES employees(id),

    -- Notes
    hr_notes                TEXT,
    is_starred              BOOLEAN DEFAULT FALSE,

    applied_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_applications_tenant ON job_applications(tenant_id);
CREATE INDEX idx_applications_job ON job_applications(job_posting_id);
CREATE INDEX idx_applications_stage ON job_applications(stage);
CREATE INDEX idx_applications_email ON job_applications(tenant_id, email);
CREATE INDEX idx_applications_score ON job_applications(ai_score DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: performance_reviews
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE performance_reviews (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    cycle_id                UUID NOT NULL,               -- FK to appraisal_cycles
    employee_id             UUID NOT NULL REFERENCES employees(id),
    reviewer_id             UUID NOT NULL REFERENCES employees(id),
    review_type             VARCHAR(50) NOT NULL
                                CHECK (review_type IN ('self','manager','peer','subordinate','360')),

    -- Ratings (JSONB for flexible competency structure)
    competency_ratings      JSONB DEFAULT '{}',
    -- {
    --   "technical_skills": {"score": 4, "comment": "..."},
    --   "communication": {"score": 3, "comment": "..."},
    --   "leadership": {"score": 5, "comment": "..."}
    -- }

    goal_achievement_ratings JSONB DEFAULT '{}',
    -- [{"goal_id": "...", "target": 100, "actual": 90, "score": 4}]

    overall_rating          DECIMAL(3, 2),               -- 1.00 to 5.00
    overall_comment         TEXT,

    -- Performance Band
    performance_band        VARCHAR(50)
                                CHECK (performance_band IN ('exceptional','exceeds','meets',
                                                           'below','unsatisfactory')),

    -- AI Prediction
    predicted_band          VARCHAR(50),
    prediction_confidence   DECIMAL(5, 4),

    -- Status
    status                  VARCHAR(50) NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending','in_progress','submitted',
                                                  'acknowledged','finalised')),
    submitted_at            TIMESTAMPTZ,
    acknowledged_at         TIMESTAMPTZ,
    acknowledged_by         UUID REFERENCES employees(id),

    -- Increment / Promotion
    increment_recommended   BOOLEAN DEFAULT FALSE,
    increment_percentage    DECIMAL(5, 2),
    promotion_recommended   BOOLEAN DEFAULT FALSE,
    promotion_to_grade      VARCHAR(50),

    -- PIP
    pip_recommended         BOOLEAN DEFAULT FALSE,
    pip_reason              TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, cycle_id, employee_id, reviewer_id, review_type)
);

CREATE INDEX idx_reviews_tenant ON performance_reviews(tenant_id);
CREATE INDEX idx_reviews_employee ON performance_reviews(employee_id);
CREATE INDEX idx_reviews_cycle ON performance_reviews(cycle_id);
CREATE INDEX idx_reviews_status ON performance_reviews(status);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: assets
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE assets (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id               UUID NOT NULL REFERENCES tenants(id),
    asset_tag               VARCHAR(100) NOT NULL,
    name                    VARCHAR(255) NOT NULL,
    category                VARCHAR(100)
                                CHECK (category IN ('laptop','desktop','phone','tablet',
                                                   'vehicle','access_card','sim_card',
                                                   'monitor','printer','other')),
    make                    VARCHAR(100),
    model                   VARCHAR(100),
    serial_number           VARCHAR(255),
    purchase_date           DATE,
    purchase_price          DECIMAL(15, 2),
    currency                VARCHAR(10) DEFAULT 'PKR',
    warranty_expiry         DATE,
    condition               VARCHAR(50) DEFAULT 'good'
                                CHECK (condition IN ('new','good','fair','poor','damaged','decommissioned')),

    -- Assignment
    assigned_to_id          UUID REFERENCES employees(id),
    assigned_at             DATE,
    assignment_notes        TEXT,

    -- Depreciation
    depreciation_method     VARCHAR(50) DEFAULT 'straight_line'
                                CHECK (depreciation_method IN ('straight_line','reducing_balance')),
    useful_life_years       INTEGER DEFAULT 3,
    salvage_value           DECIMAL(15, 2) DEFAULT 0,
    current_book_value      DECIMAL(15, 2),

    -- Status
    status                  VARCHAR(50) NOT NULL DEFAULT 'available'
                                CHECK (status IN ('available','assigned','maintenance',
                                                 'lost','damaged','disposed','reserved')),

    location                VARCHAR(255),
    qr_code_url             TEXT,
    notes                   TEXT,
    photo_url               TEXT,

    last_audit_date         DATE,
    next_maintenance_date   DATE,

    created_by              UUID,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, asset_tag)
);

CREATE INDEX idx_assets_tenant ON assets(tenant_id);
CREATE INDEX idx_assets_assigned ON assets(assigned_to_id);
CREATE INDEX idx_assets_status ON assets(status);
CREATE INDEX idx_assets_warranty ON assets(warranty_expiry);

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: audit_logs (IMMUTABLE — no UPDATE or DELETE permitted)
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,               -- sequential for ordering
    tenant_id       UUID NOT NULL,                       -- no FK — survives tenant deletion
    actor_id        UUID,                                -- NULL for system events
    actor_email     VARCHAR(255),                        -- denormalized for permanence
    actor_ip        INET,
    actor_user_agent TEXT,

    -- Action
    action          VARCHAR(100) NOT NULL,               -- e.g. employee.update, payroll.approve
    resource_type   VARCHAR(100) NOT NULL,               -- e.g. employees, payroll_records
    resource_id     UUID,
    resource_label  VARCHAR(255),                        -- e.g. employee full name

    -- Change detail
    old_values      JSONB,
    new_values      JSONB,
    diff            JSONB,                               -- computed diff only changed fields

    -- Context
    http_method     VARCHAR(10),
    endpoint        VARCHAR(500),
    request_id      VARCHAR(100),

    -- AI decisions
    ai_decision_id  UUID,
    is_ai_action    BOOLEAN DEFAULT FALSE,

    severity        VARCHAR(20) DEFAULT 'info'
                        CHECK (severity IN ('info','warning','critical','security')),

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
    -- NO updated_at, NO deleted_at — immutable
);

-- Partition by month for performance
CREATE INDEX idx_audit_tenant_date ON audit_logs(tenant_id, created_at DESC);
CREATE INDEX idx_audit_actor ON audit_logs(actor_id, created_at DESC);
CREATE INDEX idx_audit_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_action ON audit_logs(action);

-- Prevent UPDATE and DELETE on audit_logs
CREATE RULE no_update_audit AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE no_delete_audit AS ON DELETE TO audit_logs DO INSTEAD NOTHING;

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: notification_logs
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE notification_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    recipient_id        UUID REFERENCES employees(id),
    recipient_email     VARCHAR(255),
    recipient_phone     VARCHAR(50),

    -- Content
    event_type          VARCHAR(100) NOT NULL,           -- e.g. probation_ending, leave_approved
    channel             VARCHAR(50) NOT NULL
                            CHECK (channel IN ('email','sms','in_app','push','whatsapp')),
    subject             VARCHAR(500),
    body                TEXT,
    template_id         UUID,
    variables_used      JSONB DEFAULT '{}',

    -- Status
    status              VARCHAR(50) NOT NULL DEFAULT 'queued'
                            CHECK (status IN ('queued','sent','delivered','failed','bounced','read')),
    sent_at             TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    read_at             TIMESTAMPTZ,
    failed_reason       TEXT,

    -- Retry
    attempt_count       INTEGER DEFAULT 0,
    next_retry_at       TIMESTAMPTZ,
    max_attempts        INTEGER DEFAULT 3,

    -- External refs
    provider_message_id VARCHAR(255),                    -- SendGrid message ID, Twilio SID

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notif_tenant ON notification_logs(tenant_id);
CREATE INDEX idx_notif_recipient ON notification_logs(recipient_id);
CREATE INDEX idx_notif_status ON notification_logs(status);
CREATE INDEX idx_notif_retry ON notification_logs(next_retry_at)
    WHERE status = 'failed' AND attempt_count < max_attempts;

-- ─────────────────────────────────────────────────────────────────────────────
-- TABLE: feature_flags
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE feature_flags (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key             VARCHAR(200) UNIQUE NOT NULL,         -- e.g. "new_payroll_engine"
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    flag_type       VARCHAR(30) NOT NULL DEFAULT 'boolean'
                        CHECK (flag_type IN ('boolean','percentage','multivariate')),

    -- Value
    is_enabled      BOOLEAN DEFAULT FALSE,               -- for boolean flags
    rollout_percentage DECIMAL(5, 2) DEFAULT 0,          -- 0.00 to 100.00
    variants        JSONB DEFAULT '[]',                  -- for multivariate flags
    -- [{"key": "A", "weight": 50, "value": {...}}, ...]

    -- Targeting rules
    tenant_overrides  JSONB DEFAULT '{}',                -- {"tenant_id": true/false}
    role_overrides    JSONB DEFAULT '{}',                -- {"hr_manager": true}
    department_overrides JSONB DEFAULT '{}',

    -- Lifecycle
    environment     VARCHAR(50) DEFAULT 'production'
                        CHECK (environment IN ('development','staging','production','all')),
    expires_at      TIMESTAMPTZ,                         -- auto-disable after date
    tags            TEXT[],

    -- Audit
    created_by      UUID,
    updated_by      UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_feature_flags_key ON feature_flags(key);
CREATE INDEX idx_feature_flags_enabled ON feature_flags(is_enabled) WHERE is_enabled = TRUE;

-- ─────────────────────────────────────────────────────────────────────────────
-- ADDITIONAL TABLES (abbreviated — full schema in implementation)
-- ─────────────────────────────────────────────────────────────────────────────
-- shifts, shift_assignments, shift_swap_requests
-- leave_balances, leave_balance_transactions, public_holidays
-- appraisal_cycles, goals, goal_updates, pips, pip_milestones
-- training_programs, training_enrollments, skill_matrix, skills
-- employee_documents, document_types
-- exit_interviews, clearance_checklists, clearance_items
-- asset_assignments (history), asset_maintenance_records
-- users, user_sessions, roles, permissions, role_permissions
-- salary_structures, salary_components, tax_slabs, bonus_records
-- interviews, interview_feedback, offers
-- announcements, raise_requests, hr_letters
-- ai_decisions, ai_overrides, ai_bias_reports
-- document_embeddings (vector type for chatbot RAG)
-- etl_jobs, etl_records, migration_batches
```

## 2.3 ERD Key Relationships

```
tenants ──< departments ──< employees
tenants ──< branches ──< employees
employees >── employees (self-ref: reporting_manager_id)
employees ──< attendance_records
employees ──< employee_compensation
employees ──< leave_requests >── leave_types
employees ──< payroll_records >── payroll_runs
employees ──< performance_reviews >── appraisal_cycles
employees ──< job_applications >── job_postings >── departments
employees ──< assets (assigned_to)
employees ──< audit_logs (actor)
employees ──< notification_logs
tenants ──< feature_flags (via tenant_overrides JSONB)
```

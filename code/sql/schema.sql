-- ══════════════════════════════════════════════════════════════════════════════
-- AI-HRMS — Complete PostgreSQL Schema
-- Version : 1.0.0
-- Engine  : PostgreSQL 15+
-- Encoding: UTF-8
-- ══════════════════════════════════════════════════════════════════════════════
-- Usage:
--   psql -U hrms_user -d hrms_db -f schema.sql
-- Or via Alembic (preferred):
--   alembic upgrade head
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Extensions ───────────────────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "unaccent";

SET timezone = 'UTC';
SET client_encoding = 'UTF8';

-- ─── Drop existing ENUMs (for clean re-runs in dev) ───────────────────────────
DROP TYPE IF EXISTS tenant_plan_enum         CASCADE;
DROP TYPE IF EXISTS permission_action_enum   CASCADE;
DROP TYPE IF EXISTS module_name_enum         CASCADE;
DROP TYPE IF EXISTS gender_enum              CASCADE;
DROP TYPE IF EXISTS marital_status_enum      CASCADE;
DROP TYPE IF EXISTS contract_type_enum       CASCADE;
DROP TYPE IF EXISTS employment_status_enum   CASCADE;
DROP TYPE IF EXISTS work_schedule_enum       CASCADE;
DROP TYPE IF EXISTS document_type_enum       CASCADE;
DROP TYPE IF EXISTS payment_method_enum      CASCADE;
DROP TYPE IF EXISTS currency_enum            CASCADE;
DROP TYPE IF EXISTS check_in_source_enum     CASCADE;
DROP TYPE IF EXISTS attendance_status_enum   CASCADE;
DROP TYPE IF EXISTS adjustment_status_enum   CASCADE;
DROP TYPE IF EXISTS leave_status_enum        CASCADE;
DROP TYPE IF EXISTS leave_gender_enum        CASCADE;
DROP TYPE IF EXISTS payroll_run_status_enum  CASCADE;
DROP TYPE IF EXISTS payroll_record_status_enum CASCADE;
DROP TYPE IF EXISTS job_status_enum          CASCADE;
DROP TYPE IF EXISTS employment_type_enum     CASCADE;
DROP TYPE IF EXISTS application_status_enum  CASCADE;
DROP TYPE IF EXISTS application_source_enum  CASCADE;
DROP TYPE IF EXISTS interview_mode_enum      CASCADE;
DROP TYPE IF EXISTS interview_status_enum    CASCADE;
DROP TYPE IF EXISTS cycle_status_enum        CASCADE;
DROP TYPE IF EXISTS appraisal_status_enum    CASCADE;
DROP TYPE IF EXISTS goal_status_enum         CASCADE;
DROP TYPE IF EXISTS goal_category_enum       CASCADE;
DROP TYPE IF EXISTS training_mode_enum       CASCADE;
DROP TYPE IF EXISTS training_status_enum     CASCADE;
DROP TYPE IF EXISTS enrollment_status_enum   CASCADE;
DROP TYPE IF EXISTS asset_condition_enum     CASCADE;
DROP TYPE IF EXISTS asset_status_enum        CASCADE;
DROP TYPE IF EXISTS asset_category_enum      CASCADE;
DROP TYPE IF EXISTS notification_type_enum   CASCADE;
DROP TYPE IF EXISTS notification_channel_enum CASCADE;
DROP TYPE IF EXISTS notification_category_enum CASCADE;

-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 1 — ENUM TYPES
-- ══════════════════════════════════════════════════════════════════════════════

CREATE TYPE tenant_plan_enum AS ENUM ('starter', 'professional', 'enterprise');

CREATE TYPE permission_action_enum AS ENUM ('create', 'read', 'update', 'delete', 'approve', 'export');

CREATE TYPE module_name_enum AS ENUM (
    'employee_management', 'attendance', 'payroll', 'leave',
    'performance', 'recruitment', 'training', 'self_service',
    'assets', 'offboarding', 'compliance', 'notifications',
    'analytics', 'mobile', 'system'
);

CREATE TYPE gender_enum AS ENUM ('male', 'female', 'other', 'prefer_not_to_say');

CREATE TYPE marital_status_enum AS ENUM ('single', 'married', 'divorced', 'widowed');

CREATE TYPE contract_type_enum AS ENUM ('permanent', 'contract', 'probation', 'intern', 'consultant');

CREATE TYPE employment_status_enum AS ENUM (
    'active', 'inactive', 'terminated', 'resigned', 'on_leave', 'suspended'
);

CREATE TYPE work_schedule_enum AS ENUM ('full_time', 'part_time', 'remote', 'hybrid');

CREATE TYPE document_type_enum AS ENUM (
    'cnic_front', 'cnic_back', 'passport', 'degree_certificate',
    'experience_letter', 'cv_resume', 'offer_letter', 'contract',
    'medical_certificate', 'visa', 'work_permit', 'noc', 'other'
);

CREATE TYPE payment_method_enum AS ENUM ('bank_transfer', 'cash', 'cheque');

CREATE TYPE currency_enum AS ENUM ('PKR', 'USD', 'AED', 'SAR', 'GBP', 'EUR', 'INR', 'BDT');

CREATE TYPE check_in_source_enum AS ENUM ('manual', 'biometric', 'mobile', 'geo', 'web');

CREATE TYPE attendance_status_enum AS ENUM (
    'present', 'absent', 'late', 'half_day', 'holiday', 'on_leave', 'work_from_home', 'weekly_off'
);

CREATE TYPE adjustment_status_enum AS ENUM ('pending', 'approved', 'rejected');

CREATE TYPE leave_status_enum AS ENUM ('pending', 'approved', 'rejected', 'cancelled', 'recalled');

CREATE TYPE leave_gender_enum AS ENUM ('all', 'male', 'female');

CREATE TYPE payroll_run_status_enum AS ENUM ('draft', 'processing', 'approved', 'paid', 'cancelled');

CREATE TYPE payroll_record_status_enum AS ENUM ('pending', 'processed', 'paid', 'on_hold');

CREATE TYPE job_status_enum AS ENUM ('draft', 'open', 'closed', 'on_hold', 'filled');

CREATE TYPE employment_type_enum AS ENUM ('full_time', 'part_time', 'contract', 'internship', 'remote');

CREATE TYPE application_status_enum AS ENUM (
    'applied', 'screening', 'shortlisted', 'interview', 'offered', 'hired', 'rejected', 'withdrawn'
);

CREATE TYPE application_source_enum AS ENUM (
    'portal', 'linkedin', 'indeed', 'referral', 'direct', 'agency', 'campus', 'other'
);

CREATE TYPE interview_mode_enum AS ENUM ('online', 'in_person', 'phone');

CREATE TYPE interview_status_enum AS ENUM (
    'scheduled', 'completed', 'cancelled', 'no_show', 'rescheduled'
);

CREATE TYPE cycle_status_enum AS ENUM (
    'upcoming', 'active', 'self_review', 'manager_review', 'calibration', 'completed', 'archived'
);

CREATE TYPE appraisal_status_enum AS ENUM (
    'not_started', 'self_review_pending', 'self_review_submitted',
    'manager_review_pending', 'manager_review_submitted', 'hr_review', 'completed'
);

CREATE TYPE goal_status_enum AS ENUM ('active', 'completed', 'missed', 'cancelled', 'on_hold');

CREATE TYPE goal_category_enum AS ENUM ('performance', 'learning', 'behavioral', 'project', 'other');

CREATE TYPE training_mode_enum AS ENUM ('online', 'in_person', 'hybrid', 'self_paced');

CREATE TYPE training_status_enum AS ENUM (
    'planned', 'registration_open', 'ongoing', 'completed', 'cancelled'
);

CREATE TYPE enrollment_status_enum AS ENUM (
    'enrolled', 'in_progress', 'completed', 'failed', 'absent', 'dropped'
);

CREATE TYPE asset_condition_enum AS ENUM ('excellent', 'good', 'fair', 'poor', 'damaged');

CREATE TYPE asset_status_enum AS ENUM ('available', 'assigned', 'maintenance', 'retired', 'lost', 'disposed');

CREATE TYPE asset_category_enum AS ENUM (
    'laptop', 'desktop', 'mobile', 'tablet', 'monitor', 'keyboard',
    'mouse', 'headset', 'sim_card', 'access_card', 'vehicle', 'furniture', 'other'
);

CREATE TYPE notification_type_enum AS ENUM ('info', 'success', 'warning', 'error');

CREATE TYPE notification_channel_enum AS ENUM ('in_app', 'email', 'sms', 'push', 'whatsapp');

CREATE TYPE notification_category_enum AS ENUM (
    'leave', 'attendance', 'payroll', 'performance', 'recruitment',
    'training', 'asset', 'onboarding', 'offboarding', 'compliance', 'system', 'general'
);


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 2 — CORE / AUTH TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 1: tenants ─────────────────────────────────────────────────────────
-- RLS: Not applicable — this is the root table used to scope all others.
CREATE TABLE tenants (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    slug            VARCHAR(100) NOT NULL UNIQUE,
    plan            tenant_plan_enum NOT NULL DEFAULT 'starter',
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    settings        JSONB,
    logo_url        VARCHAR(500),
    primary_color   VARCHAR(7),
    timezone        VARCHAR(50)  NOT NULL DEFAULT 'Asia/Karachi',
    country         VARCHAR(100) NOT NULL DEFAULT 'Pakistan',
    currency        VARCHAR(3)   NOT NULL DEFAULT 'PKR',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE tenants IS
    'Root multi-tenancy table. Every other table is scoped via tenant_id FK.';

CREATE INDEX idx_tenants_slug ON tenants (slug);
CREATE INDEX idx_tenants_is_active ON tenants (is_active) WHERE is_active = TRUE;


-- ─── Table 2: users ───────────────────────────────────────────────────────────
-- RLS: Enable per-tenant isolation via tenant_id.
CREATE TABLE users (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    email                   VARCHAR(255) NOT NULL,
    hashed_password         VARCHAR(255) NOT NULL,
    first_name              VARCHAR(100) NOT NULL,
    last_name               VARCHAR(100) NOT NULL,
    is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
    is_verified             BOOLEAN     NOT NULL DEFAULT FALSE,
    is_superadmin           BOOLEAN     NOT NULL DEFAULT FALSE,
    avatar_url              VARCHAR(500),
    phone                   VARCHAR(20),
    timezone                VARCHAR(50)  NOT NULL DEFAULT 'Asia/Karachi',
    last_login              TIMESTAMPTZ,
    failed_login_attempts   INTEGER     NOT NULL DEFAULT 0,
    locked_until            TIMESTAMPTZ,
    password_changed_at     TIMESTAMPTZ,
    reset_token             VARCHAR(255),
    reset_token_expires     TIMESTAMPTZ,
    refresh_token_hash      VARCHAR(255),
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email)
);

COMMENT ON TABLE users IS
    'Authentication accounts. One user belongs to exactly one tenant.';

CREATE INDEX idx_users_tenant_id     ON users (tenant_id);
CREATE INDEX idx_users_email         ON users (email);
CREATE INDEX idx_users_is_active     ON users (is_active, tenant_id);
CREATE INDEX idx_users_reset_token   ON users (reset_token) WHERE reset_token IS NOT NULL;


-- ─── Table 3: roles ───────────────────────────────────────────────────────────
CREATE TABLE roles (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    name            VARCHAR(100) NOT NULL,
    description     TEXT,
    is_system_role  BOOLEAN     NOT NULL DEFAULT FALSE,
    ui_config       JSONB,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_roles_tenant_name UNIQUE (tenant_id, name)
);

CREATE INDEX idx_roles_tenant_id ON roles (tenant_id);


-- ─── Table 4: permissions ─────────────────────────────────────────────────────
CREATE TABLE permissions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    module_name     module_name_enum    NOT NULL,
    action          permission_action_enum NOT NULL,
    description     TEXT,
    CONSTRAINT uq_permissions_module_action UNIQUE (module_name, action)
);

CREATE INDEX idx_permissions_module ON permissions (module_name);


-- ─── Table 5: role_permissions ────────────────────────────────────────────────
CREATE TABLE role_permissions (
    role_id         UUID        NOT NULL REFERENCES roles (id) ON DELETE CASCADE,
    permission_id   UUID        NOT NULL REFERENCES permissions (id) ON DELETE CASCADE,
    granted_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (role_id, permission_id)
);

CREATE INDEX idx_role_permissions_role_id ON role_permissions (role_id);
CREATE INDEX idx_role_permissions_perm_id ON role_permissions (permission_id);


-- ─── Table 6: user_roles ──────────────────────────────────────────────────────
CREATE TABLE user_roles (
    user_id         UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    role_id         UUID        NOT NULL REFERENCES roles (id) ON DELETE CASCADE,
    assigned_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    assigned_by     UUID        REFERENCES users (id) ON DELETE SET NULL,
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX idx_user_roles_user_id ON user_roles (user_id);
CREATE INDEX idx_user_roles_role_id ON user_roles (role_id);


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 3 — EMPLOYEE TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 7: departments ─────────────────────────────────────────────────────
CREATE TABLE departments (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    code            VARCHAR(20),
    description     TEXT,
    parent_id       UUID        REFERENCES departments (id) ON DELETE SET NULL,
    manager_id      UUID,       -- FK to employees.id added after employees table is created
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_departments_tenant_name UNIQUE (tenant_id, name)
);

COMMENT ON TABLE departments IS
    'Hierarchical department tree. Self-referential via parent_id.';

CREATE INDEX idx_departments_tenant_id ON departments (tenant_id);
CREATE INDEX idx_departments_parent_id ON departments (parent_id);


-- ─── Table 8: designations ────────────────────────────────────────────────────
CREATE TABLE designations (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,
    department_id   UUID        REFERENCES departments (id) ON DELETE SET NULL,
    level           VARCHAR(50),
    grade           VARCHAR(20),
    min_salary      INTEGER,
    max_salary      INTEGER,
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_designations_tenant_id     ON designations (tenant_id);
CREATE INDEX idx_designations_department_id ON designations (department_id);


-- ─── Table 9: shifts ──────────────────────────────────────────────────────────
-- Created before employees because employees.shift_id FKs to this table.
CREATE TABLE shifts (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    name                        VARCHAR(100) NOT NULL,
    start_time                  TIME        NOT NULL,
    end_time                    TIME        NOT NULL,
    break_minutes               INTEGER     NOT NULL DEFAULT 60,
    working_days                INTEGER[]   NOT NULL DEFAULT '{0,1,2,3,4}',
    is_night_shift              BOOLEAN     NOT NULL DEFAULT FALSE,
    late_threshold_minutes      INTEGER     NOT NULL DEFAULT 15,
    half_day_hours              NUMERIC(4,2) NOT NULL DEFAULT 4.0,
    overtime_threshold_hours    NUMERIC(4,2) NOT NULL DEFAULT 8.0,
    is_active                   BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN shifts.working_days IS
    'Array of day numbers: 0=Monday, 1=Tuesday, ..., 6=Sunday';

CREATE INDEX idx_shifts_tenant_id ON shifts (tenant_id);


-- ─── Table 10: employees ──────────────────────────────────────────────────────
-- RLS: All queries must filter on tenant_id.
CREATE TABLE employees (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    user_id                 UUID        UNIQUE REFERENCES users (id) ON DELETE SET NULL,
    employee_code           VARCHAR(30) NOT NULL,
    first_name              VARCHAR(100) NOT NULL,
    middle_name             VARCHAR(100),
    last_name               VARCHAR(100) NOT NULL,
    father_name             VARCHAR(200),

    -- Identity
    cnic                    VARCHAR(20),
    cnic_expiry             DATE,

    -- Contact
    personal_email          VARCHAR(255),
    work_email              VARCHAR(255),
    phone                   VARCHAR(20),
    phone_secondary         VARCHAR(20),

    -- Demographics
    gender                  gender_enum,
    dob                     DATE,
    marital_status          marital_status_enum,
    nationality             VARCHAR(100),
    religion                VARCHAR(100),
    blood_group             VARCHAR(5),

    -- Structured fields stored as JSONB for flexibility
    address                 JSONB,
    emergency_contact       JSONB,

    -- Employment
    department_id           UUID        REFERENCES departments (id) ON DELETE SET NULL,
    designation_id          UUID        REFERENCES designations (id) ON DELETE SET NULL,
    manager_id              UUID        REFERENCES employees (id) ON DELETE SET NULL,  -- Self-ref
    branch_location         VARCHAR(200),
    cost_center             VARCHAR(50),
    grade_level             VARCHAR(50),
    contract_type           contract_type_enum      NOT NULL DEFAULT 'permanent',
    employment_status       employment_status_enum  NOT NULL DEFAULT 'active',
    work_schedule           work_schedule_enum      NOT NULL DEFAULT 'full_time',

    -- Dates
    join_date               DATE,
    probation_end_date      DATE,
    confirmation_date       DATE,
    termination_date        DATE,
    termination_reason      TEXT,
    notice_period_days      INTEGER     NOT NULL DEFAULT 30,

    -- Shift
    shift_id                UUID        REFERENCES shifts (id) ON DELETE SET NULL,
    timezone                VARCHAR(50) NOT NULL DEFAULT 'Asia/Karachi',

    -- Media
    profile_photo_url       VARCHAR(500),

    -- Internal
    hr_notes                TEXT,
    is_deleted              BOOLEAN     NOT NULL DEFAULT FALSE,
    deleted_at              TIMESTAMPTZ,

    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_employees_tenant_code        UNIQUE (tenant_id, employee_code),
    CONSTRAINT uq_employees_tenant_cnic        UNIQUE (tenant_id, cnic),
    CONSTRAINT uq_employees_tenant_work_email  UNIQUE (tenant_id, work_email)
);

COMMENT ON TABLE employees IS
    'Core employee record. Soft-deleted via is_deleted flag (never hard-deleted for compliance).';
COMMENT ON COLUMN employees.address IS
    'JSONB: {line1, line2, city, state, postal_code, country}';
COMMENT ON COLUMN employees.emergency_contact IS
    'JSONB: {name, relation, phone, email}';

-- Foreign key cycle resolution: add departments.manager_id FK after employees exists
ALTER TABLE departments
    ADD CONSTRAINT fk_departments_manager_id
    FOREIGN KEY (manager_id) REFERENCES employees (id) ON DELETE SET NULL;

-- Performance-critical indexes
CREATE INDEX idx_employees_tenant_id        ON employees (tenant_id);
CREATE INDEX idx_employees_user_id          ON employees (user_id);
CREATE INDEX idx_employees_department_id    ON employees (department_id);
CREATE INDEX idx_employees_designation_id   ON employees (designation_id);
CREATE INDEX idx_employees_manager_id       ON employees (manager_id);
CREATE INDEX idx_employees_shift_id         ON employees (shift_id);
CREATE INDEX idx_employees_status           ON employees (employment_status, tenant_id);
CREATE INDEX idx_employees_join_date        ON employees (join_date);
CREATE INDEX idx_employees_is_deleted       ON employees (is_deleted) WHERE is_deleted = FALSE;
-- Full-text search index on name
CREATE INDEX idx_employees_name_trgm ON employees
    USING gin ((first_name || ' ' || last_name) gin_trgm_ops);


-- ─── Table 11: employee_documents ────────────────────────────────────────────
CREATE TABLE employee_documents (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id         UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    doc_type            document_type_enum NOT NULL,
    doc_name            VARCHAR(200) NOT NULL,
    file_url            VARCHAR(500) NOT NULL,
    file_name           VARCHAR(255) NOT NULL,
    file_size_bytes     INTEGER,
    mime_type           VARCHAR(100),
    expiry_date         DATE,
    is_verified         BOOLEAN     NOT NULL DEFAULT FALSE,
    verified_by         UUID        REFERENCES users (id) ON DELETE SET NULL,
    verified_at         TIMESTAMPTZ,
    notes               TEXT,
    is_deleted          BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE employee_documents IS
    'Document uploads for employees. Soft-delete only — never hard-delete for compliance.';

CREATE INDEX idx_employee_documents_employee_id ON employee_documents (employee_id);
CREATE INDEX idx_employee_documents_doc_type    ON employee_documents (doc_type);
CREATE INDEX idx_employee_documents_expiry      ON employee_documents (expiry_date) WHERE expiry_date IS NOT NULL;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 4 — COMPENSATION TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 12: salary_structures ─────────────────────────────────────────────
CREATE TABLE salary_structures (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    employee_id             UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    currency                currency_enum NOT NULL DEFAULT 'PKR',
    basic_salary            INTEGER     NOT NULL,
    house_rent_allowance    INTEGER     NOT NULL DEFAULT 0,
    medical_allowance       INTEGER     NOT NULL DEFAULT 0,
    transport_allowance     INTEGER     NOT NULL DEFAULT 0,
    fuel_allowance          INTEGER     NOT NULL DEFAULT 0,
    utility_allowance       INTEGER     NOT NULL DEFAULT 0,
    other_allowances        JSONB,
    eobi_applicable         BOOLEAN     NOT NULL DEFAULT TRUE,
    sessi_applicable        BOOLEAN     NOT NULL DEFAULT FALSE,
    income_tax_applicable   BOOLEAN     NOT NULL DEFAULT TRUE,
    loan_deduction          INTEGER     NOT NULL DEFAULT 0,
    advance_deduction       INTEGER     NOT NULL DEFAULT 0,
    effective_from          DATE        NOT NULL,
    effective_to            DATE,       -- NULL = currently active
    created_by              UUID        REFERENCES users (id) ON DELETE SET NULL,
    revision_note           VARCHAR(500),
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON COLUMN salary_structures.effective_to IS
    'NULL means this is the currently active salary structure for this employee.';

CREATE INDEX idx_salary_structures_tenant_id    ON salary_structures (tenant_id);
CREATE INDEX idx_salary_structures_employee_id  ON salary_structures (employee_id);
CREATE INDEX idx_salary_structures_effective_from ON salary_structures (effective_from);
-- Partial index for the active structure per employee
CREATE INDEX idx_salary_structures_active ON salary_structures (employee_id, effective_from)
    WHERE effective_to IS NULL;


-- ─── Table 13: bank_details ───────────────────────────────────────────────────
CREATE TABLE bank_details (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id         UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    bank_name           VARCHAR(200) NOT NULL,
    account_title       VARCHAR(200) NOT NULL,
    account_number      VARCHAR(30)  NOT NULL,
    iban                VARCHAR(34),
    branch_code         VARCHAR(10),
    branch_name         VARCHAR(200),
    swift_code          VARCHAR(11),
    payment_method      payment_method_enum NOT NULL DEFAULT 'bank_transfer',
    is_primary          BOOLEAN     NOT NULL DEFAULT TRUE,
    is_active           BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_bank_details_employee_id ON bank_details (employee_id);
CREATE INDEX idx_bank_details_primary ON bank_details (employee_id, is_primary)
    WHERE is_primary = TRUE;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 5 — ATTENDANCE TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 14: attendance_records ────────────────────────────────────────────
CREATE TABLE attendance_records (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    employee_id             UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    date                    DATE        NOT NULL,
    shift_id                UUID        REFERENCES shifts (id) ON DELETE SET NULL,
    check_in                TIMESTAMPTZ,
    check_in_source         check_in_source_enum,
    check_in_location       JSONB,
    check_out               TIMESTAMPTZ,
    check_out_source        check_in_source_enum,
    check_out_location      JSONB,
    status                  attendance_status_enum NOT NULL DEFAULT 'absent',
    working_hours           NUMERIC(5,2),
    overtime_hours          NUMERIC(5,2),
    late_minutes            INTEGER,
    early_out_minutes       INTEGER,
    notes                   TEXT,
    is_manual_entry         BOOLEAN     NOT NULL DEFAULT FALSE,
    entered_by              UUID        REFERENCES users (id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_attendance_employee_date UNIQUE (employee_id, date)
);

COMMENT ON TABLE attendance_records IS
    'One record per employee per day. UNIQUE (employee_id, date) enforced.';
COMMENT ON COLUMN attendance_records.check_in_location IS
    'JSONB: {latitude, longitude, address, accuracy_meters}';

CREATE INDEX idx_attendance_tenant_id   ON attendance_records (tenant_id);
CREATE INDEX idx_attendance_employee_id ON attendance_records (employee_id);
CREATE INDEX idx_attendance_date        ON attendance_records (date);
CREATE INDEX idx_attendance_status      ON attendance_records (status, tenant_id);
CREATE INDEX idx_attendance_emp_date    ON attendance_records (employee_id, date DESC);
-- Partial index for today's records (most common query)
CREATE INDEX idx_attendance_today       ON attendance_records (tenant_id, date)
    WHERE date = CURRENT_DATE;


-- ─── Table 15: attendance_adjustments ────────────────────────────────────────
CREATE TABLE attendance_adjustments (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    attendance_id           UUID        NOT NULL REFERENCES attendance_records (id) ON DELETE CASCADE,
    requested_by            UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    approved_by             UUID        REFERENCES users (id) ON DELETE SET NULL,
    requested_check_in      TIMESTAMPTZ,
    requested_check_out     TIMESTAMPTZ,
    reason                  TEXT        NOT NULL,
    supporting_document_url VARCHAR(500),
    status                  adjustment_status_enum NOT NULL DEFAULT 'pending',
    rejection_reason        TEXT,
    resolved_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_attendance_adj_attendance_id ON attendance_adjustments (attendance_id);
CREATE INDEX idx_attendance_adj_status        ON attendance_adjustments (status);


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 6 — LEAVE TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 16: leave_types ────────────────────────────────────────────────────
CREATE TABLE leave_types (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    name                    VARCHAR(100) NOT NULL,
    code                    VARCHAR(10),
    description             TEXT,
    color                   VARCHAR(7),
    days_allowed            INTEGER     NOT NULL,
    carry_forward           BOOLEAN     NOT NULL DEFAULT FALSE,
    max_carry_forward_days  INTEGER     NOT NULL DEFAULT 0,
    is_paid                 BOOLEAN     NOT NULL DEFAULT TRUE,
    applicable_gender       leave_gender_enum NOT NULL DEFAULT 'all',
    requires_document       BOOLEAN     NOT NULL DEFAULT FALSE,
    min_service_months      INTEGER     NOT NULL DEFAULT 0,
    max_consecutive_days    INTEGER,
    advance_notice_days     INTEGER     NOT NULL DEFAULT 0,
    allow_half_day          BOOLEAN     NOT NULL DEFAULT FALSE,
    is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_leave_types_tenant_id ON leave_types (tenant_id);


-- ─── Table 17: leave_balances ─────────────────────────────────────────────────
CREATE TABLE leave_balances (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id     UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    leave_type_id   UUID        NOT NULL REFERENCES leave_types (id) ON DELETE CASCADE,
    year            INTEGER     NOT NULL,
    total_days      NUMERIC(5,1) NOT NULL,
    used_days       NUMERIC(5,1) NOT NULL DEFAULT 0,
    pending_days    NUMERIC(5,1) NOT NULL DEFAULT 0,
    carried_days    NUMERIC(5,1) NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_leave_balance_emp_type_year UNIQUE (employee_id, leave_type_id, year)
);

CREATE INDEX idx_leave_balances_employee_id   ON leave_balances (employee_id);
CREATE INDEX idx_leave_balances_leave_type_id ON leave_balances (leave_type_id);
CREATE INDEX idx_leave_balances_year          ON leave_balances (year);


-- ─── Table 18: leave_requests ─────────────────────────────────────────────────
CREATE TABLE leave_requests (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    employee_id                 UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    leave_type_id               UUID        NOT NULL REFERENCES leave_types (id) ON DELETE RESTRICT,
    start_date                  DATE        NOT NULL,
    end_date                    DATE        NOT NULL,
    total_days                  NUMERIC(5,1) NOT NULL,
    is_half_day                 BOOLEAN     NOT NULL DEFAULT FALSE,
    half_day_period             VARCHAR(10),    -- 'morning' or 'afternoon'
    reason                      TEXT,
    document_url                VARCHAR(500),
    status                      leave_status_enum NOT NULL DEFAULT 'pending',
    approved_by                 UUID        REFERENCES users (id) ON DELETE SET NULL,
    approved_at                 TIMESTAMPTZ,
    rejection_reason            TEXT,
    reviewed_by                 UUID        REFERENCES users (id) ON DELETE SET NULL,
    reviewed_at                 TIMESTAMPTZ,
    contact_during_leave        VARCHAR(20),
    substitute_employee_id      UUID        REFERENCES employees (id) ON DELETE SET NULL,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE leave_requests IS
    'Leave applications. status transitions: pending→approved/rejected→(recalled).';

CREATE INDEX idx_leave_requests_tenant_id      ON leave_requests (tenant_id);
CREATE INDEX idx_leave_requests_employee_id    ON leave_requests (employee_id);
CREATE INDEX idx_leave_requests_leave_type_id  ON leave_requests (leave_type_id);
CREATE INDEX idx_leave_requests_status         ON leave_requests (status, tenant_id);
CREATE INDEX idx_leave_requests_start_date     ON leave_requests (start_date);
CREATE INDEX idx_leave_requests_pending        ON leave_requests (tenant_id, status)
    WHERE status = 'pending';


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 7 — PAYROLL TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 19: payroll_runs ───────────────────────────────────────────────────
CREATE TABLE payroll_runs (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    month                   INTEGER     NOT NULL CHECK (month BETWEEN 1 AND 12),
    year                    INTEGER     NOT NULL,
    label                   VARCHAR(100),
    status                  payroll_run_status_enum NOT NULL DEFAULT 'draft',
    total_employees         INTEGER     NOT NULL DEFAULT 0,
    total_gross             INTEGER     NOT NULL DEFAULT 0,
    total_net               INTEGER     NOT NULL DEFAULT 0,
    total_deductions        INTEGER     NOT NULL DEFAULT 0,
    total_eobi_employee     INTEGER     NOT NULL DEFAULT 0,
    total_eobi_employer     INTEGER     NOT NULL DEFAULT 0,
    total_income_tax        INTEGER     NOT NULL DEFAULT 0,
    processed_by            UUID        REFERENCES users (id) ON DELETE SET NULL,
    approved_by             UUID        REFERENCES users (id) ON DELETE SET NULL,
    run_at                  TIMESTAMPTZ,
    approved_at             TIMESTAMPTZ,
    paid_at                 TIMESTAMPTZ,
    notes                   TEXT,
    celery_task_id          VARCHAR(255),
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_payroll_runs_tenant_month_year UNIQUE (tenant_id, month, year)
);

COMMENT ON TABLE payroll_runs IS
    'Monthly payroll batch. One run per tenant per month/year.';

CREATE INDEX idx_payroll_runs_tenant_id ON payroll_runs (tenant_id);
CREATE INDEX idx_payroll_runs_status    ON payroll_runs (status, tenant_id);
CREATE INDEX idx_payroll_runs_year_month ON payroll_runs (tenant_id, year DESC, month DESC);


-- ─── Table 20: payroll_records ────────────────────────────────────────────────
CREATE TABLE payroll_records (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    payroll_run_id          UUID        NOT NULL REFERENCES payroll_runs (id) ON DELETE CASCADE,
    employee_id             UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    basic_salary            INTEGER     NOT NULL,
    house_rent_allowance    INTEGER     NOT NULL DEFAULT 0,
    medical_allowance       INTEGER     NOT NULL DEFAULT 0,
    transport_allowance     INTEGER     NOT NULL DEFAULT 0,
    fuel_allowance          INTEGER     NOT NULL DEFAULT 0,
    other_allowances        JSONB,
    total_allowances        INTEGER     NOT NULL DEFAULT 0,
    gross_salary            INTEGER     NOT NULL,
    eobi_employee           INTEGER     NOT NULL DEFAULT 0,
    eobi_employer           INTEGER     NOT NULL DEFAULT 0,
    sessi                   INTEGER     NOT NULL DEFAULT 0,
    income_tax              INTEGER     NOT NULL DEFAULT 0,
    loan_deduction          INTEGER     NOT NULL DEFAULT 0,
    advance_deduction       INTEGER     NOT NULL DEFAULT 0,
    other_deductions        JSONB,
    total_deductions        INTEGER     NOT NULL DEFAULT 0,
    net_salary              INTEGER     NOT NULL,
    working_days            INTEGER     NOT NULL,
    present_days            INTEGER     NOT NULL DEFAULT 0,
    absent_days             INTEGER     NOT NULL DEFAULT 0,
    late_days               INTEGER     NOT NULL DEFAULT 0,
    overtime_hours          NUMERIC(6,2),
    paid_leave_days         NUMERIC(4,1) NOT NULL DEFAULT 0,
    unpaid_leave_days       NUMERIC(4,1) NOT NULL DEFAULT 0,
    is_prorated             BOOLEAN     NOT NULL DEFAULT FALSE,
    payslip_url             VARCHAR(500),
    status                  payroll_record_status_enum NOT NULL DEFAULT 'pending',
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_payroll_record_run_employee UNIQUE (payroll_run_id, employee_id)
);

CREATE INDEX idx_payroll_records_run_id      ON payroll_records (payroll_run_id);
CREATE INDEX idx_payroll_records_employee_id ON payroll_records (employee_id);
CREATE INDEX idx_payroll_records_status      ON payroll_records (status);


-- ─── Table 21: tax_slabs ──────────────────────────────────────────────────────
CREATE TABLE tax_slabs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    year            INTEGER     NOT NULL,
    min_income      INTEGER     NOT NULL,
    max_income      INTEGER,    -- NULL = no upper limit
    tax_rate        NUMERIC(5,4) NOT NULL,
    fixed_tax       INTEGER     NOT NULL DEFAULT 0,
    description     VARCHAR(200),
    is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tax_slabs_tenant_year ON tax_slabs (tenant_id, year);


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 8 — RECRUITMENT TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 22: job_postings ───────────────────────────────────────────────────
CREATE TABLE job_postings (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    title                   VARCHAR(200) NOT NULL,
    department_id           UUID        REFERENCES departments (id) ON DELETE SET NULL,
    designation_id          UUID        REFERENCES designations (id) ON DELETE SET NULL,
    location                VARCHAR(200),
    description             TEXT,
    requirements            TEXT,
    responsibilities        TEXT,
    benefits                TEXT,
    vacancies               INTEGER     NOT NULL DEFAULT 1,
    employment_type         employment_type_enum NOT NULL DEFAULT 'full_time',
    experience_years_min    INTEGER     NOT NULL DEFAULT 0,
    experience_years_max    INTEGER,
    salary_min              INTEGER,
    salary_max              INTEGER,
    is_salary_visible       BOOLEAN     NOT NULL DEFAULT FALSE,
    embedding_vector        JSONB,
    required_skills         JSONB,
    status                  job_status_enum NOT NULL DEFAULT 'draft',
    posted_by               UUID        REFERENCES users (id) ON DELETE SET NULL,
    posted_at               TIMESTAMPTZ,
    closing_date            DATE,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_postings_tenant_id     ON job_postings (tenant_id);
CREATE INDEX idx_job_postings_status        ON job_postings (status, tenant_id);
CREATE INDEX idx_job_postings_department_id ON job_postings (department_id);
CREATE INDEX idx_job_postings_closing_date  ON job_postings (closing_date);
CREATE INDEX idx_job_postings_title_trgm    ON job_postings USING gin (title gin_trgm_ops);


-- ─── Table 23: job_applications ───────────────────────────────────────────────
CREATE TABLE job_applications (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    job_posting_id          UUID        NOT NULL REFERENCES job_postings (id) ON DELETE CASCADE,
    candidate_name          VARCHAR(200) NOT NULL,
    candidate_email         VARCHAR(255) NOT NULL,
    candidate_phone         VARCHAR(20),
    candidate_location      VARCHAR(200),
    cv_url                  VARCHAR(500),
    cover_letter            TEXT,
    portfolio_url           VARCHAR(500),
    linkedin_url            VARCHAR(500),
    source                  application_source_enum NOT NULL DEFAULT 'portal',
    referred_by             UUID        REFERENCES employees (id) ON DELETE SET NULL,
    applied_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    status                  application_status_enum NOT NULL DEFAULT 'applied',
    rejection_reason        TEXT,
    is_archived             BOOLEAN     NOT NULL DEFAULT FALSE,
    ai_score                NUMERIC(5,2),
    ai_explanation          JSONB,
    ai_scored_at            TIMESTAMPTZ,
    hr_notes                TEXT,
    offer_letter_url        VARCHAR(500),
    offer_sent_at           TIMESTAMPTZ,
    offer_deadline          DATE,
    hired_employee_id       UUID        REFERENCES employees (id) ON DELETE SET NULL,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_job_applications_posting_id    ON job_applications (job_posting_id);
CREATE INDEX idx_job_applications_email         ON job_applications (candidate_email);
CREATE INDEX idx_job_applications_status        ON job_applications (status, job_posting_id);
CREATE INDEX idx_job_applications_ai_score      ON job_applications (ai_score DESC) WHERE ai_score IS NOT NULL;
CREATE INDEX idx_job_applications_applied_at    ON job_applications (applied_at DESC);


-- ─── Table 24: interviews ─────────────────────────────────────────────────────
CREATE TABLE interviews (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    application_id      UUID        NOT NULL REFERENCES job_applications (id) ON DELETE CASCADE,
    round_number        INTEGER     NOT NULL DEFAULT 1,
    title               VARCHAR(200),
    interviewer_id      UUID        REFERENCES employees (id) ON DELETE SET NULL,
    scheduled_by        UUID        REFERENCES users (id) ON DELETE SET NULL,
    scheduled_at        TIMESTAMPTZ,
    duration_minutes    INTEGER     NOT NULL DEFAULT 60,
    mode                interview_mode_enum NOT NULL DEFAULT 'online',
    meeting_link        VARCHAR(500),
    location            VARCHAR(300),
    status              interview_status_enum NOT NULL DEFAULT 'scheduled',
    feedback            TEXT,
    rating              NUMERIC(3,1) CHECK (rating BETWEEN 1 AND 5),
    recommendation      VARCHAR(20),
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interviews_application_id ON interviews (application_id);
CREATE INDEX idx_interviews_interviewer_id ON interviews (interviewer_id);
CREATE INDEX idx_interviews_scheduled_at   ON interviews (scheduled_at);
CREATE INDEX idx_interviews_status         ON interviews (status);


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 9 — PERFORMANCE TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 25: appraisal_cycles ───────────────────────────────────────────────
CREATE TABLE appraisal_cycles (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    name                        VARCHAR(200) NOT NULL,
    year                        INTEGER     NOT NULL,
    quarter                     INTEGER     CHECK (quarter BETWEEN 1 AND 4),
    period_label                VARCHAR(50),
    start_date                  DATE        NOT NULL,
    end_date                    DATE        NOT NULL,
    self_review_deadline        DATE,
    manager_review_deadline     DATE,
    status                      cycle_status_enum NOT NULL DEFAULT 'upcoming',
    rating_scale_min            NUMERIC(3,1) NOT NULL DEFAULT 1.0,
    rating_scale_max            NUMERIC(3,1) NOT NULL DEFAULT 5.0,
    self_review_instructions    TEXT,
    manager_review_instructions TEXT,
    created_by                  UUID,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_appraisal_cycles_tenant_id ON appraisal_cycles (tenant_id);
CREATE INDEX idx_appraisal_cycles_year      ON appraisal_cycles (year, tenant_id);
CREATE INDEX idx_appraisal_cycles_status    ON appraisal_cycles (status, tenant_id);


-- ─── Table 26: appraisals ─────────────────────────────────────────────────────
CREATE TABLE appraisals (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cycle_id                    UUID        NOT NULL REFERENCES appraisal_cycles (id) ON DELETE CASCADE,
    employee_id                 UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    reviewer_id                 UUID        REFERENCES employees (id) ON DELETE SET NULL,
    self_rating                 NUMERIC(3,1),
    manager_rating              NUMERIC(3,1),
    final_rating                NUMERIC(3,1),
    kpi_scores                  JSONB,
    self_strengths              TEXT,
    self_improvements           TEXT,
    self_achievements           TEXT,
    manager_feedback            TEXT,
    hr_comments                 TEXT,
    predicted_rating            NUMERIC(3,1),
    attrition_risk_score        NUMERIC(5,4),
    ai_insights                 JSONB,
    increment_recommended       BOOLEAN     NOT NULL DEFAULT FALSE,
    increment_percentage        NUMERIC(5,2),
    promotion_recommended       BOOLEAN     NOT NULL DEFAULT FALSE,
    promotion_to_designation    VARCHAR(200),
    status                      appraisal_status_enum NOT NULL DEFAULT 'not_started',
    self_submitted_at           TIMESTAMPTZ,
    manager_submitted_at        TIMESTAMPTZ,
    finalized_at                TIMESTAMPTZ,
    employee_acknowledged       BOOLEAN     NOT NULL DEFAULT FALSE,
    acknowledged_at             TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_appraisals_cycle_employee UNIQUE (cycle_id, employee_id)
);

CREATE INDEX idx_appraisals_cycle_id     ON appraisals (cycle_id);
CREATE INDEX idx_appraisals_employee_id  ON appraisals (employee_id);
CREATE INDEX idx_appraisals_reviewer_id  ON appraisals (reviewer_id);
CREATE INDEX idx_appraisals_status       ON appraisals (status, cycle_id);


-- ─── Table 27: goals ──────────────────────────────────────────────────────────
CREATE TABLE goals (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    employee_id         UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    cycle_id            UUID        REFERENCES appraisal_cycles (id) ON DELETE SET NULL,
    title               VARCHAR(300) NOT NULL,
    description         TEXT,
    category            goal_category_enum NOT NULL DEFAULT 'performance',
    target              VARCHAR(500),
    target_value        NUMERIC(10,2),
    achievement         VARCHAR(500),
    achievement_value   NUMERIC(10,2),
    weight              NUMERIC(5,2) NOT NULL DEFAULT 100,
    due_date            DATE,
    status              goal_status_enum NOT NULL DEFAULT 'active',
    set_by              VARCHAR(10),    -- 'manager' or 'self'
    is_shared           BOOLEAN     NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_goals_employee_id ON goals (employee_id);
CREATE INDEX idx_goals_cycle_id    ON goals (cycle_id);
CREATE INDEX idx_goals_status      ON goals (status, employee_id);
CREATE INDEX idx_goals_due_date    ON goals (due_date) WHERE due_date IS NOT NULL;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 10 — TRAINING TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 28: training_programs ─────────────────────────────────────────────
CREATE TABLE training_programs (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id                   UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    title                       VARCHAR(300) NOT NULL,
    description                 TEXT,
    category                    VARCHAR(100),
    skills_covered              JSONB,
    trainer                     VARCHAR(200),
    trainer_id                  UUID        REFERENCES employees (id) ON DELETE SET NULL,
    mode                        training_mode_enum NOT NULL DEFAULT 'in_person',
    venue                       VARCHAR(300),
    meeting_link                VARCHAR(500),
    start_date                  DATE,
    end_date                    DATE,
    duration_hours              NUMERIC(6,1),
    max_participants            INTEGER,
    min_participants            INTEGER,
    cost_per_participant        INTEGER,
    currency                    VARCHAR(3)  NOT NULL DEFAULT 'PKR',
    is_mandatory                BOOLEAN     NOT NULL DEFAULT FALSE,
    issues_certificate          BOOLEAN     NOT NULL DEFAULT FALSE,
    certificate_validity_months INTEGER,
    material_url                VARCHAR(500),
    external_url                VARCHAR(500),
    status                      training_status_enum NOT NULL DEFAULT 'planned',
    created_by                  UUID,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_training_programs_tenant_id  ON training_programs (tenant_id);
CREATE INDEX idx_training_programs_status     ON training_programs (status, tenant_id);
CREATE INDEX idx_training_programs_start_date ON training_programs (start_date);


-- ─── Table 29: training_enrollments ──────────────────────────────────────────
CREATE TABLE training_enrollments (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    program_id              UUID        NOT NULL REFERENCES training_programs (id) ON DELETE CASCADE,
    employee_id             UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    status                  enrollment_status_enum NOT NULL DEFAULT 'enrolled',
    score                   NUMERIC(5,2),
    pass_score              NUMERIC(5,2),
    attendance_percentage   NUMERIC(5,2),
    feedback                TEXT,
    certificate_url         VARCHAR(500),
    certificate_issued_at   DATE,
    certificate_expires_at  DATE,
    enrolled_at             TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    completed_at            TIMESTAMPTZ,
    nominated_by            UUID,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_training_enrollment_program_employee UNIQUE (program_id, employee_id)
);

CREATE INDEX idx_training_enrollments_program_id  ON training_enrollments (program_id);
CREATE INDEX idx_training_enrollments_employee_id ON training_enrollments (employee_id);
CREATE INDEX idx_training_enrollments_status      ON training_enrollments (status);


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 11 — ASSET TABLES
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 30: assets ─────────────────────────────────────────────────────────
CREATE TABLE assets (
    id                      UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    asset_tag               VARCHAR(50) NOT NULL,
    name                    VARCHAR(200) NOT NULL,
    category                asset_category_enum NOT NULL,
    brand                   VARCHAR(100),
    model                   VARCHAR(200),
    serial_number           VARCHAR(100),
    specifications          JSONB,
    purchase_date           DATE,
    purchase_cost           INTEGER,
    current_value           INTEGER,
    currency                VARCHAR(3)  NOT NULL DEFAULT 'PKR',
    vendor                  VARCHAR(200),
    invoice_number          VARCHAR(100),
    warranty_expiry         DATE,
    condition               asset_condition_enum NOT NULL DEFAULT 'good',
    status                  asset_status_enum    NOT NULL DEFAULT 'available',
    location                VARCHAR(200),
    notes                   TEXT,
    photo_url               VARCHAR(500),
    current_employee_id     UUID        REFERENCES employees (id) ON DELETE SET NULL,
    assigned_since          DATE,
    is_active               BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_assets_tenant_tag UNIQUE (tenant_id, asset_tag)
);

CREATE INDEX idx_assets_tenant_id          ON assets (tenant_id);
CREATE INDEX idx_assets_category           ON assets (category, tenant_id);
CREATE INDEX idx_assets_status             ON assets (status, tenant_id);
CREATE INDEX idx_assets_current_employee   ON assets (current_employee_id);
CREATE INDEX idx_assets_warranty_expiry    ON assets (warranty_expiry) WHERE warranty_expiry IS NOT NULL;


-- ─── Table 31: asset_assignments ──────────────────────────────────────────────
CREATE TABLE asset_assignments (
    id                          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id                    UUID        NOT NULL REFERENCES assets (id) ON DELETE CASCADE,
    employee_id                 UUID        NOT NULL REFERENCES employees (id) ON DELETE CASCADE,
    assigned_at                 DATE        NOT NULL,
    assigned_by                 UUID        REFERENCES users (id) ON DELETE SET NULL,
    condition_at_assignment     asset_condition_enum NOT NULL DEFAULT 'good',
    assignment_notes            TEXT,
    handover_document_url       VARCHAR(500),
    employee_acknowledged       BOOLEAN     NOT NULL DEFAULT FALSE,
    acknowledged_at             TIMESTAMPTZ,
    returned_at                 DATE,
    condition_at_return         asset_condition_enum,
    return_notes                TEXT,
    return_document_url         VARCHAR(500),
    received_by                 UUID        REFERENCES users (id) ON DELETE SET NULL,
    is_damaged                  BOOLEAN     NOT NULL DEFAULT FALSE,
    damage_description          TEXT,
    damage_cost                 INTEGER,
    created_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_asset_assignments_asset_id    ON asset_assignments (asset_id);
CREATE INDEX idx_asset_assignments_employee_id ON asset_assignments (employee_id);
CREATE INDEX idx_asset_assignments_assigned_at ON asset_assignments (assigned_at DESC);
-- Active assignments (not yet returned)
CREATE INDEX idx_asset_assignments_active      ON asset_assignments (employee_id, asset_id)
    WHERE returned_at IS NULL;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 12 — NOTIFICATIONS TABLE
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 32: notifications ──────────────────────────────────────────────────
CREATE TABLE notifications (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    user_id             UUID        NOT NULL REFERENCES users (id) ON DELETE CASCADE,
    sender_id           UUID        REFERENCES users (id) ON DELETE SET NULL,
    title               VARCHAR(200) NOT NULL,
    message             TEXT        NOT NULL,
    type                notification_type_enum     NOT NULL DEFAULT 'info',
    category            notification_category_enum NOT NULL DEFAULT 'general',
    channel             notification_channel_enum  NOT NULL DEFAULT 'in_app',
    action_url          VARCHAR(500),
    action_label        VARCHAR(100),
    resource_type       VARCHAR(50),
    resource_id         UUID,
    extra_data          JSONB,
    is_read             BOOLEAN     NOT NULL DEFAULT FALSE,
    read_at             TIMESTAMPTZ,
    is_sent             BOOLEAN     NOT NULL DEFAULT FALSE,
    sent_at             TIMESTAMPTZ,
    delivery_error      TEXT,
    retry_count         INTEGER     NOT NULL DEFAULT 0,
    expires_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE notifications IS
    'In-app and push notification records. Bulk sent via Celery tasks.';

CREATE INDEX idx_notifications_tenant_id ON notifications (tenant_id);
CREATE INDEX idx_notifications_user_id   ON notifications (user_id);
CREATE INDEX idx_notifications_unread    ON notifications (user_id, is_read)
    WHERE is_read = FALSE;
CREATE INDEX idx_notifications_category  ON notifications (category, tenant_id);
CREATE INDEX idx_notifications_created   ON notifications (created_at DESC);
-- Pending delivery (unsent non-in-app notifications)
CREATE INDEX idx_notifications_unsent    ON notifications (channel, is_sent, retry_count)
    WHERE is_sent = FALSE AND channel != 'in_app';


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 13 — AUDIT TABLE
-- ══════════════════════════════════════════════════════════════════════════════

-- ─── Table 33: audit_logs ─────────────────────────────────────────────────────
CREATE TABLE audit_logs (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID        NOT NULL REFERENCES tenants (id) ON DELETE CASCADE,
    user_id         UUID        REFERENCES users (id) ON DELETE SET NULL,
    user_email      VARCHAR(255),
    action          VARCHAR(50) NOT NULL,
    resource        VARCHAR(100) NOT NULL,
    resource_id     UUID,
    resource_label  VARCHAR(300),
    old_values      JSONB,
    new_values      JSONB,
    changed_fields  JSONB,
    ip_address      VARCHAR(45),
    user_agent      TEXT,
    request_id      VARCHAR(36),
    session_id      VARCHAR(255),
    extra_data      JSONB,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
    -- NO updated_at — audit logs are insert-only
);

COMMENT ON TABLE audit_logs IS
    'Immutable audit trail. Records are NEVER updated or deleted. '
    'Consider pg_partman partitioning by created_at for large datasets.';

CREATE INDEX idx_audit_logs_tenant_id    ON audit_logs (tenant_id);
CREATE INDEX idx_audit_logs_user_id      ON audit_logs (user_id);
CREATE INDEX idx_audit_logs_action       ON audit_logs (action, tenant_id);
CREATE INDEX idx_audit_logs_resource     ON audit_logs (resource, resource_id);
CREATE INDEX idx_audit_logs_created_at   ON audit_logs (created_at DESC);
CREATE INDEX idx_audit_logs_ip_address   ON audit_logs (ip_address) WHERE ip_address IS NOT NULL;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 14 — ROW LEVEL SECURITY (RLS)
-- ══════════════════════════════════════════════════════════════════════════════
-- Enable RLS on all tenant-scoped tables.
-- Application sets: SET app.current_tenant_id = '<uuid>' at session start.
-- This provides defence-in-depth: even a misconfigured query can't leak
-- cross-tenant data.

ALTER TABLE users               ENABLE ROW LEVEL SECURITY;
ALTER TABLE roles               ENABLE ROW LEVEL SECURITY;
ALTER TABLE departments         ENABLE ROW LEVEL SECURITY;
ALTER TABLE designations        ENABLE ROW LEVEL SECURITY;
ALTER TABLE shifts              ENABLE ROW LEVEL SECURITY;
ALTER TABLE employees           ENABLE ROW LEVEL SECURITY;
ALTER TABLE employee_documents  ENABLE ROW LEVEL SECURITY;
ALTER TABLE salary_structures   ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records  ENABLE ROW LEVEL SECURITY;
ALTER TABLE leave_types         ENABLE ROW LEVEL SECURITY;
ALTER TABLE leave_balances      ENABLE ROW LEVEL SECURITY;
ALTER TABLE leave_requests      ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_runs        ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_records     ENABLE ROW LEVEL SECURITY;
ALTER TABLE tax_slabs           ENABLE ROW LEVEL SECURITY;
ALTER TABLE job_postings        ENABLE ROW LEVEL SECURITY;
ALTER TABLE appraisal_cycles    ENABLE ROW LEVEL SECURITY;
ALTER TABLE appraisals          ENABLE ROW LEVEL SECURITY;
ALTER TABLE goals               ENABLE ROW LEVEL SECURITY;
ALTER TABLE training_programs   ENABLE ROW LEVEL SECURITY;
ALTER TABLE assets              ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications       ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs          ENABLE ROW LEVEL SECURITY;

-- Example RLS policy (apply similar to all tenant-scoped tables):
-- CREATE POLICY tenant_isolation ON employees
--     USING (tenant_id = current_setting('app.current_tenant_id')::UUID);


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 15 — TRIGGERS (updated_at auto-refresh)
-- ══════════════════════════════════════════════════════════════════════════════

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to all tables with updated_at
DO $$
DECLARE
    t TEXT;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'tenants', 'users', 'roles', 'departments', 'designations', 'shifts',
        'employees', 'employee_documents', 'salary_structures', 'bank_details',
        'attendance_records', 'attendance_adjustments',
        'leave_types', 'leave_balances', 'leave_requests',
        'payroll_runs', 'payroll_records', 'tax_slabs',
        'job_postings', 'job_applications', 'interviews',
        'appraisal_cycles', 'appraisals', 'goals',
        'training_programs', 'training_enrollments',
        'assets', 'asset_assignments',
        'notifications'
    ]
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON %s
             FOR EACH ROW EXECUTE FUNCTION update_updated_at_column()',
            t, t
        );
    END LOOP;
END $$;


-- ══════════════════════════════════════════════════════════════════════════════
-- SECTION 16 — SEED DATA (system permissions)
-- ══════════════════════════════════════════════════════════════════════════════

INSERT INTO permissions (id, module_name, action, description) VALUES
    -- Employee Management
    (gen_random_uuid(), 'employee_management', 'create',  'Add new employees'),
    (gen_random_uuid(), 'employee_management', 'read',    'View employee records'),
    (gen_random_uuid(), 'employee_management', 'update',  'Edit employee details'),
    (gen_random_uuid(), 'employee_management', 'delete',  'Archive/delete employees'),
    (gen_random_uuid(), 'employee_management', 'export',  'Export employee data'),
    -- Attendance
    (gen_random_uuid(), 'attendance', 'create',  'Record attendance'),
    (gen_random_uuid(), 'attendance', 'read',    'View attendance records'),
    (gen_random_uuid(), 'attendance', 'update',  'Adjust attendance'),
    (gen_random_uuid(), 'attendance', 'approve', 'Approve attendance adjustments'),
    (gen_random_uuid(), 'attendance', 'export',  'Export attendance reports'),
    -- Payroll
    (gen_random_uuid(), 'payroll', 'create',  'Create payroll runs'),
    (gen_random_uuid(), 'payroll', 'read',    'View payroll records'),
    (gen_random_uuid(), 'payroll', 'update',  'Edit payroll records'),
    (gen_random_uuid(), 'payroll', 'approve', 'Approve payroll runs'),
    (gen_random_uuid(), 'payroll', 'export',  'Export payroll reports'),
    -- Leave
    (gen_random_uuid(), 'leave', 'create',  'Apply for leave'),
    (gen_random_uuid(), 'leave', 'read',    'View leave requests'),
    (gen_random_uuid(), 'leave', 'update',  'Edit leave requests'),
    (gen_random_uuid(), 'leave', 'approve', 'Approve/reject leave requests'),
    (gen_random_uuid(), 'leave', 'export',  'Export leave reports'),
    -- Performance
    (gen_random_uuid(), 'performance', 'create',  'Create appraisal cycles and goals'),
    (gen_random_uuid(), 'performance', 'read',    'View appraisals'),
    (gen_random_uuid(), 'performance', 'update',  'Edit appraisals'),
    (gen_random_uuid(), 'performance', 'approve', 'Finalize appraisals'),
    (gen_random_uuid(), 'performance', 'export',  'Export performance reports'),
    -- Recruitment
    (gen_random_uuid(), 'recruitment', 'create',  'Post jobs and create applications'),
    (gen_random_uuid(), 'recruitment', 'read',    'View job postings and applications'),
    (gen_random_uuid(), 'recruitment', 'update',  'Update application status'),
    (gen_random_uuid(), 'recruitment', 'approve', 'Approve offers'),
    (gen_random_uuid(), 'recruitment', 'export',  'Export recruitment reports'),
    -- Training
    (gen_random_uuid(), 'training', 'create',  'Create training programs'),
    (gen_random_uuid(), 'training', 'read',    'View training programs'),
    (gen_random_uuid(), 'training', 'update',  'Edit training programs'),
    (gen_random_uuid(), 'training', 'approve', 'Approve enrollments'),
    -- Assets
    (gen_random_uuid(), 'assets', 'create',  'Add assets'),
    (gen_random_uuid(), 'assets', 'read',    'View assets'),
    (gen_random_uuid(), 'assets', 'update',  'Edit/assign assets'),
    (gen_random_uuid(), 'assets', 'export',  'Export asset register'),
    -- Analytics
    (gen_random_uuid(), 'analytics', 'read',   'View reports and dashboards'),
    (gen_random_uuid(), 'analytics', 'export', 'Export analytics data'),
    -- System
    (gen_random_uuid(), 'system', 'create',  'Create system configuration'),
    (gen_random_uuid(), 'system', 'read',    'View system settings'),
    (gen_random_uuid(), 'system', 'update',  'Edit system settings'),
    (gen_random_uuid(), 'system', 'delete',  'Delete system data')
ON CONFLICT (module_name, action) DO NOTHING;


-- ══════════════════════════════════════════════════════════════════════════════
-- END OF SCHEMA
-- Tables created: 33
-- ENUMs created:  35
-- Indexes created: 70+
-- ══════════════════════════════════════════════════════════════════════════════

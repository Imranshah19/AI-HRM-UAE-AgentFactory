"""UAE AI-HRM complete schema — 9 tables for UAE multi-company HR.

Revision ID: uae_001_complete_schema
Revises: a3f7e9b2c1d4
Create Date: 2026-04-25 00:01:00.000000+00:00

New tables (ALL existing tables are untouched):
  1. companies              — Multi-company group structure
  2. employees_uae_profile  — UAE-specific employee data (extends existing employees)
  3. salary_structure_uae   — AED salary breakdown per employee
  4. payroll_uae            — Monthly payroll records in AED
  5. wps_submissions        — WPS SIF file submission tracking
  6. gratuity_ledger        — Gratuity accrual and final settlements
  7. leave_balances_uae     — 9 UAE leave types per employee
  8. documents_tracker      — Document expiry tracking (visa, passport, etc.)
  9. emiratisation_records  — Monthly Emiratisation compliance records
  10. agent_logs_uae        — UAE-specific agent execution logs

Zero modifications to existing Pakistan HRM tables.
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from alembic import op

revision: str = "uae_001_complete_schema"
down_revision: Union[str, None] = "a3f7e9b2c1d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    # ── 1. companies ──────────────────────────────────────────────────────────
    op.create_table(
        "companies",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("group_name", sa.String(256), nullable=False, index=True),
        sa.Column("name_en", sa.String(256), nullable=False),
        sa.Column("name_ar", sa.String(256), nullable=True),
        sa.Column("trade_license_number", sa.String(64), nullable=True, unique=True),
        sa.Column("mohre_establishment_id", sa.String(64), nullable=True, unique=True),
        sa.Column("wps_agent_bank", sa.String(128), nullable=True),
        sa.Column("industry_type", sa.String(128), nullable=True),
        sa.Column("emirate", sa.String(64), nullable=True),   # Dubai/AbuDhabi/Sharjah/etc.
        sa.Column("is_freezone", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("freezone_name", sa.String(128), nullable=True),  # DMCC/JAFZA/ADGM/DIFC
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_companies_group_name",   "companies", ["group_name"])
    op.create_index("ix_companies_emirate",      "companies", ["emirate"])
    op.create_index("ix_companies_is_active",    "companies", ["is_active"])

    # ── 2. employees_uae_profile ──────────────────────────────────────────────
    op.create_table(
        "employees_uae_profile",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),   # FK to employees.id
        sa.Column("company_id", sa.String(36), nullable=False),    # FK to companies.id
        sa.Column("name_ar", sa.String(256), nullable=True),
        sa.Column("nationality", sa.String(64), nullable=True),
        sa.Column("country_of_origin", sa.String(64), nullable=True),
        # Passport
        sa.Column("passport_number", sa.String(32), nullable=True),
        sa.Column("passport_expiry", sa.Date(), nullable=True),
        # Visa
        sa.Column("visa_number", sa.String(64), nullable=True),
        sa.Column("visa_type", sa.String(64), nullable=True),
        sa.Column("visa_expiry", sa.Date(), nullable=True),
        sa.Column("visa_sponsor", sa.String(256), nullable=True),
        # Emirates ID
        sa.Column("emirates_id", sa.String(20), nullable=True, unique=True),
        sa.Column("emirates_id_expiry", sa.Date(), nullable=True),
        # Labour card
        sa.Column("labour_card_number", sa.String(64), nullable=True),
        sa.Column("labour_card_expiry", sa.Date(), nullable=True),
        sa.Column("mohre_person_id", sa.String(14), nullable=True),  # 14-digit WPS ID
        # Banking (for WPS)
        sa.Column("bank_name", sa.String(128), nullable=True),
        sa.Column("bank_iban", sa.String(34), nullable=True),
        # Contract
        sa.Column("contract_type", sa.String(32), nullable=True),  # full-time/part-time/flexible/remote
        sa.Column("contract_start", sa.Date(), nullable=True),
        sa.Column("contract_end", sa.Date(), nullable=True),
        sa.Column("probation_end_date", sa.Date(), nullable=True),
        sa.Column("notice_period_days", sa.Integer(), nullable=True),
        # Insurance
        sa.Column("insurance_provider", sa.String(128), nullable=True),
        sa.Column("insurance_policy_number", sa.String(64), nullable=True),
        sa.Column("insurance_expiry", sa.Date(), nullable=True),
        sa.Column("insurance_dependents_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("iloe_enrolled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        # Air ticket
        sa.Column("air_ticket_entitlement", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("air_ticket_last_used_date", sa.Date(), nullable=True),
        sa.Column("air_ticket_value_aed", sa.Numeric(10, 2), server_default="3000.00", nullable=False),
        # Emiratisation
        sa.Column("is_emirati", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("nafis_enrolled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("work_location", sa.String(64), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_uae_profile_employee_id",  "employees_uae_profile", ["employee_id"])
    op.create_index("ix_uae_profile_company_id",   "employees_uae_profile", ["company_id"])
    op.create_index("ix_uae_profile_is_emirati",   "employees_uae_profile", ["is_emirati"])
    op.create_index("ix_uae_profile_visa_expiry",  "employees_uae_profile", ["visa_expiry"])
    op.create_index("ix_uae_profile_passport_exp", "employees_uae_profile", ["passport_expiry"])
    op.create_index("ix_uae_profile_contract_end", "employees_uae_profile", ["contract_end"])
    op.create_unique_constraint(
        "uq_uae_profile_employee_company",
        "employees_uae_profile", ["employee_id", "company_id"]
    )

    # ── 3. salary_structure_uae ───────────────────────────────────────────────
    op.create_table(
        "salary_structure_uae",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("basic_salary", sa.Numeric(12, 2), nullable=False),
        sa.Column("housing_allowance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("transport_allowance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("food_allowance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("phone_allowance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("other_allowances", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("effective_from_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_salary_uae_employee_id", "salary_structure_uae", ["employee_id"])
    op.create_index("ix_salary_uae_company_id",  "salary_structure_uae", ["company_id"])

    # ── 4. payroll_uae ────────────────────────────────────────────────────────
    op.create_table(
        "payroll_uae",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("payroll_month", sa.Integer(), nullable=False),
        sa.Column("payroll_year", sa.Integer(), nullable=False),
        sa.Column("working_days", sa.Integer(), server_default="26", nullable=False),
        sa.Column("actual_days_worked", sa.Integer(), server_default="26", nullable=False),
        sa.Column("basic_salary", sa.Numeric(12, 2), nullable=False),
        sa.Column("housing_allowance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("transport_allowance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("food_allowance", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("other_allowances", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("overtime_hours", sa.Numeric(8, 2), server_default="0", nullable=False),
        sa.Column("overtime_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("leave_deduction_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("leave_deduction_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("loan_deduction", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("advance_deduction", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("iloe_deduction", sa.Numeric(8, 2), server_default="5", nullable=False),
        sa.Column("other_deductions", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("gross_salary", sa.Numeric(14, 2), nullable=True),
        sa.Column("total_deductions", sa.Numeric(14, 2), nullable=True),
        sa.Column("net_salary", sa.Numeric(14, 2), nullable=False),
        sa.Column("wps_included", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=True),
        sa.Column("payment_status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_payroll_uae_company_id",     "payroll_uae", ["company_id"])
    op.create_index("ix_payroll_uae_employee_id",    "payroll_uae", ["employee_id"])
    op.create_index("ix_payroll_uae_month_year",     "payroll_uae", ["payroll_month", "payroll_year"])
    op.create_index("ix_payroll_uae_payment_status", "payroll_uae", ["payment_status"])

    # ── 5. wps_submissions ────────────────────────────────────────────────────
    op.create_table(
        "wps_submissions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("submission_month", sa.Integer(), nullable=False),
        sa.Column("submission_year", sa.Integer(), nullable=False),
        sa.Column("sif_file_path", sa.String(512), nullable=True),
        sa.Column("sif_file_format", sa.String(8), server_default="XML", nullable=False),
        sa.Column("total_employees_included", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_amount_aed", sa.Numeric(16, 2), server_default="0", nullable=False),
        sa.Column("submission_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), server_default="draft", nullable=False),
        sa.Column("bank_reference_number", sa.String(128), nullable=True),
        sa.Column("mohre_confirmation_number", sa.String(128), nullable=True),
        sa.Column("late_days", sa.Integer(), server_default="0", nullable=False),
        sa.Column("fine_risk_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_wps_company_id",   "wps_submissions", ["company_id"])
    op.create_index("ix_wps_month_year",   "wps_submissions", ["submission_month", "submission_year"])
    op.create_index("ix_wps_status",       "wps_submissions", ["status"])
    op.create_unique_constraint("uq_wps_company_month_year", "wps_submissions",
                                ["company_id", "submission_month", "submission_year"])

    # ── 6. gratuity_ledger ────────────────────────────────────────────────────
    op.create_table(
        "gratuity_ledger",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("calculation_date", sa.Date(), nullable=False),
        sa.Column("service_years", sa.Numeric(6, 3), nullable=False),
        sa.Column("basic_salary_at_calculation", sa.Numeric(12, 2), nullable=False),
        sa.Column("gratuity_amount_accrued", sa.Numeric(14, 2), nullable=False),
        sa.Column("gratuity_scenario", sa.String(32), nullable=False),
        sa.Column("is_final_settlement", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("paid_date", sa.Date(), nullable=True),
        sa.Column("paid_amount", sa.Numeric(14, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_gratuity_employee_id",      "gratuity_ledger", ["employee_id"])
    op.create_index("ix_gratuity_company_id",       "gratuity_ledger", ["company_id"])
    op.create_index("ix_gratuity_is_final",         "gratuity_ledger", ["is_final_settlement"])

    # ── 7. leave_balances_uae ─────────────────────────────────────────────────
    op.create_table(
        "leave_balances_uae",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("leave_year", sa.Integer(), nullable=False),
        sa.Column("leave_type", sa.String(32), nullable=False),
        sa.Column("entitled_days", sa.Numeric(8, 2), server_default="0", nullable=False),
        sa.Column("used_days", sa.Numeric(8, 2), server_default="0", nullable=False),
        sa.Column("balance_days", sa.Numeric(8, 2), server_default="0", nullable=False),
        sa.Column("carried_forward_days", sa.Numeric(8, 2), server_default="0", nullable=False),
        sa.Column("encashable_days", sa.Numeric(8, 2), server_default="0", nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_leave_bal_uae_employee",  "leave_balances_uae", ["employee_id"])
    op.create_index("ix_leave_bal_uae_company",   "leave_balances_uae", ["company_id"])
    op.create_index("ix_leave_bal_uae_year_type", "leave_balances_uae", ["leave_year", "leave_type"])
    op.create_unique_constraint(
        "uq_leave_bal_uae_emp_co_year_type",
        "leave_balances_uae", ["employee_id", "company_id", "leave_year", "leave_type"]
    )

    # ── 8. documents_tracker ──────────────────────────────────────────────────
    op.create_table(
        "documents_tracker",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("document_type", sa.String(32), nullable=False),
        sa.Column("document_number", sa.String(64), nullable=True),
        sa.Column("document_name_custom", sa.String(256), nullable=True),
        sa.Column("issue_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(32), server_default="valid", nullable=False),
        sa.Column("alert_sent_90", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("alert_sent_30", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("alert_sent_14", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("alert_sent_7",  sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("file_url", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_docs_tracker_employee",    "documents_tracker", ["employee_id"])
    op.create_index("ix_docs_tracker_company",     "documents_tracker", ["company_id"])
    op.create_index("ix_docs_tracker_expiry",      "documents_tracker", ["expiry_date"])
    op.create_index("ix_docs_tracker_doc_type",    "documents_tracker", ["document_type"])
    op.create_index("ix_docs_tracker_status",      "documents_tracker", ["status"])

    # ── 9. emiratisation_records ──────────────────────────────────────────────
    op.create_table(
        "emiratisation_records",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=False),
        sa.Column("record_month", sa.Integer(), nullable=False),
        sa.Column("record_year", sa.Integer(), nullable=False),
        sa.Column("total_headcount", sa.Integer(), server_default="0", nullable=False),
        sa.Column("emirati_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("emiratisation_percentage", sa.Numeric(6, 3), server_default="0", nullable=False),
        sa.Column("required_percentage", sa.Numeric(6, 3), server_default="0", nullable=False),
        sa.Column("compliance_gap", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_compliant", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("fine_risk_amount_aed", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("nafis_employees_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_emiratisation_company", "emiratisation_records", ["company_id"])
    op.create_index("ix_emiratisation_month",   "emiratisation_records", ["record_month", "record_year"])
    op.create_unique_constraint(
        "uq_emiratisation_company_month_year",
        "emiratisation_records", ["company_id", "record_month", "record_year"]
    )

    # ── 10. agent_logs_uae ────────────────────────────────────────────────────
    op.create_table(
        "agent_logs_uae",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("company_id", sa.String(36), nullable=True),
        sa.Column("agent_name", sa.String(64), nullable=False),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("employee_id", sa.String(36), nullable=True),
        sa.Column("input_data", JSONB, nullable=True),
        sa.Column("output_data", JSONB, nullable=True),
        sa.Column("status", sa.String(16), server_default="success", nullable=False),
        sa.Column("execution_time_ms", sa.Float(), nullable=True),
        sa.Column("api_mode", sa.String(8), server_default="mock", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.String(32), server_default="manual", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_agent_logs_uae_company",   "agent_logs_uae", ["company_id"])
    op.create_index("ix_agent_logs_uae_agent",     "agent_logs_uae", ["agent_name"])
    op.create_index("ix_agent_logs_uae_status",    "agent_logs_uae", ["status"])
    op.create_index("ix_agent_logs_uae_employee",  "agent_logs_uae", ["employee_id"])
    op.create_index("ix_agent_logs_uae_created",   "agent_logs_uae", ["created_at"])


def downgrade() -> None:
    op.drop_table("agent_logs_uae")
    op.drop_table("emiratisation_records")
    op.drop_table("documents_tracker")
    op.drop_table("leave_balances_uae")
    op.drop_table("gratuity_ledger")
    op.drop_table("wps_submissions")
    op.drop_table("payroll_uae")
    op.drop_table("salary_structure_uae")
    op.drop_table("employees_uae_profile")
    op.drop_table("companies")

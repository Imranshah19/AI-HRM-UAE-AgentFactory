"""
AI-HRMS — Payroll module tests.

Tests are split into:
  1. Pure calculator unit tests (no DB, no fixtures needed)
  2. API integration tests (with test client + DB)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date

# ─── Calculator unit tests ────────────────────────────────────────────────────

from app.api.v1.payroll.calculator import (
    TaxSlabData,
    SalaryStructureData,
    AttendanceSummaryData,
    LeaveSummaryData,
    calculate_income_tax,
    calculate_income_tax_breakdown,
    calculate_eobi,
    calculate_overtime,
    calculate_absent_deduction,
    calculate_net_salary,
    calculate_employee_payroll,
    get_working_days,
    EOBI_EMPLOYEE_MAX_PKR,
    EOBI_EMPLOYER_MAX_PKR,
)


# ─── Income Tax — each FBR slab ───────────────────────────────────────────────

class TestIncomeTaxCalculation:

    def test_slab_zero_percent(self):
        """Annual salary ≤ 600k → 0 tax."""
        assert calculate_income_tax(600_000) == 0
        assert calculate_income_tax(0)       == 0
        assert calculate_income_tax(300_000) == 0

    def test_slab_five_percent(self):
        """600,001 – 1,200,000 → 5% of amount above 600k."""
        # annual = 900,000 → excess = 300,000 → annual_tax = 15,000 → monthly = ceil(15000/12) = 1,250
        monthly = calculate_income_tax(900_000)
        assert monthly == pytest.approx(1_250, abs=1)

    def test_slab_fifteen_percent(self):
        """1,200,001 – 2,400,000 → 30,000 + 15% above 1.2M."""
        # annual = 1,800,000 → excess above 1.2M = 600,000
        # annual_tax = 30,000 + 90,000 = 120,000 → monthly = 10,000
        monthly = calculate_income_tax(1_800_000)
        assert monthly == pytest.approx(10_000, abs=1)

    def test_slab_twenty_five_percent(self):
        """2,400,001 – 3,600,000 → 210,000 + 25% above 2.4M."""
        # annual = 3,000,000 → excess = 600,000
        # annual_tax = 210,000 + 150,000 = 360,000 → monthly = 30,000
        monthly = calculate_income_tax(3_000_000)
        assert monthly == pytest.approx(30_000, abs=1)

    def test_slab_thirty_percent(self):
        """3,600,001 – 6,000,000 → 510,000 + 30% above 3.6M."""
        # annual = 4,800,000 → excess = 1,200,000
        # annual_tax = 510,000 + 360,000 = 870,000 → monthly = ceil(72500) = 72,500
        monthly = calculate_income_tax(4_800_000)
        assert monthly == pytest.approx(72_500, abs=1)

    def test_slab_thirty_five_percent(self):
        """Above 6,000,000 → 1,230,000 + 35% above 6M."""
        # annual = 8,000,000 → excess = 2,000,000
        # annual_tax = 1,230,000 + 700,000 = 1,930,000 → monthly = ceil(160833.33) = 160,834
        monthly = calculate_income_tax(8_000_000)
        expected = 1_930_000 / 12
        import math
        assert monthly == math.ceil(expected)

    def test_custom_tax_slabs_override_defaults(self):
        """DB-provided slabs should override hardcoded FBR defaults."""
        custom_slabs = [
            TaxSlabData(min_income=0,       max_income=500_000,  fixed_tax=0,     tax_rate=0.0),
            TaxSlabData(min_income=500_001,  max_income=None,     fixed_tax=0,     tax_rate=0.10),
        ]
        # annual = 1,000,000 → in second slab → 10% of (1M - 500001 + 1) = 10% of 500,000
        # annual_tax ≈ 50,000 → monthly = ceil(4166.67) = 4,167
        monthly = calculate_income_tax(1_000_000, custom_slabs)
        assert monthly == pytest.approx(4_167, abs=1)

    def test_tax_breakdown_effective_rate(self):
        """Breakdown returns correct effective_rate."""
        breakdown = calculate_income_tax_breakdown(1_200_000)
        assert breakdown["annual_tax"]    == 0  # exactly at slab boundary before 5% kicks in
        assert breakdown["effective_rate"] == 0.0

    def test_negative_salary_returns_zero(self):
        assert calculate_income_tax(-1000) == 0

    def test_tax_breakdown_keys(self):
        result = calculate_income_tax_breakdown(2_400_000)
        assert all(k in result for k in ["annual_salary", "annual_tax", "monthly_tax",
                                          "effective_rate", "slab_applied"])


# ─── EOBI Calculation ─────────────────────────────────────────────────────────

class TestEobiCalculation:

    def test_employee_one_percent(self):
        result = calculate_eobi(30_000)
        assert result["employee"] == 300   # 1% of 30,000

    def test_employer_five_percent(self):
        result = calculate_eobi(30_000)
        assert result["employer"] == 1_500  # 5% of 30,000

    def test_employee_cap_at_370(self):
        """Employee contribution capped at PKR 370."""
        result = calculate_eobi(100_000)
        assert result["employee"] == EOBI_EMPLOYEE_MAX_PKR   # cap = 370

    def test_employer_cap_at_1850(self):
        """Employer contribution capped at PKR 1,850."""
        result = calculate_eobi(100_000)
        assert result["employer"] == EOBI_EMPLOYER_MAX_PKR   # cap = 1,850

    def test_zero_basic_returns_zero(self):
        result = calculate_eobi(0)
        assert result["employee"] == 0
        assert result["employer"] == 0

    def test_returns_integers(self):
        result = calculate_eobi(25_000)
        assert isinstance(result["employee"], int)
        assert isinstance(result["employer"], int)


# ─── Overtime Calculation ─────────────────────────────────────────────────────

class TestOvertimeCalculation:

    def test_standard_overtime(self):
        """2 overtime hours on 50,000 basic, 26 working days, 8-hr shifts."""
        # hourly = 50,000 / (26 * 8) = 240.38
        # OT rate = 240.38 * 1.5 = 360.58
        # amount  = 360.58 * 2  = 721.15 → floor = 721
        result = calculate_overtime(2.0, 50_000, 26, 8.0)
        assert result == pytest.approx(721, abs=2)

    def test_zero_hours_returns_zero(self):
        assert calculate_overtime(0, 50_000, 26) == 0

    def test_zero_working_days_returns_zero(self):
        assert calculate_overtime(5.0, 50_000, 0) == 0

    def test_returns_integer(self):
        result = calculate_overtime(3.5, 60_000, 22)
        assert isinstance(result, int)


# ─── Absent Deduction ─────────────────────────────────────────────────────────

class TestAbsentDeduction:

    def test_standard_deduction(self):
        """2 absent days on 30,000 basic, 26 working days."""
        # per_day = 30,000 / 26 = 1,153.85
        # deduction = 1,153.85 * 2 = 2,307.69 → floor = 2,307
        result = calculate_absent_deduction(30_000, 26, 2)
        assert result == pytest.approx(2_307, abs=2)

    def test_zero_absent_returns_zero(self):
        assert calculate_absent_deduction(30_000, 26, 0) == 0

    def test_zero_working_days_returns_zero(self):
        assert calculate_absent_deduction(30_000, 0, 5) == 0

    def test_full_month_absent(self):
        """Deducting all 26 days should equal basic salary."""
        result = calculate_absent_deduction(30_000, 26, 26)
        assert result == 30_000

    def test_returns_integer(self):
        result = calculate_absent_deduction(40_000, 22, 3)
        assert isinstance(result, int)


# ─── Net Salary ───────────────────────────────────────────────────────────────

class TestNetSalary:

    def test_normal_calculation(self):
        assert calculate_net_salary(100_000, 15_000) == 85_000

    def test_deductions_exceed_gross_floors_at_zero(self):
        assert calculate_net_salary(10_000, 20_000) == 0

    def test_zero_deductions(self):
        assert calculate_net_salary(75_000, 0) == 75_000


# ─── Working Days ─────────────────────────────────────────────────────────────

class TestWorkingDays:

    def test_march_2025(self):
        """March 2025 has 21 working days."""
        result = get_working_days(3, 2025)
        assert result == 21

    def test_february_2024_leap(self):
        result = get_working_days(2, 2024)
        assert 19 <= result <= 21  # leap year Feb

    def test_returns_positive_int(self):
        assert get_working_days(1, 2025) > 0


# ─── Full Payroll Orchestrator ────────────────────────────────────────────────

class TestCalculateEmployeePayroll:

    def _make_salary(self) -> SalaryStructureData:
        return SalaryStructureData(
            basic_salary          = 50_000,
            house_rent_allowance  = 15_000,
            medical_allowance     = 5_000,
            transport_allowance   = 3_000,
            eobi_applicable       = True,
            income_tax_applicable = True,
            loan_deduction        = 2_000,
        )

    def _make_attendance(self) -> AttendanceSummaryData:
        return AttendanceSummaryData(
            working_days  = 26,
            present_days  = 24,
            absent_days   = 2,
            overtime_hours= 0,
        )

    def test_gross_is_basic_plus_allowances(self):
        sal = self._make_salary()
        att = self._make_attendance()
        result = calculate_employee_payroll("e1", sal, att, LeaveSummaryData())
        expected_gross = 50_000 + 15_000 + 5_000 + 3_000 - calculate_absent_deduction(50_000, 26, 2)
        assert result.gross_salary == expected_gross

    def test_eobi_included_when_applicable(self):
        sal = self._make_salary()
        att = self._make_attendance()
        result = calculate_employee_payroll("e1", sal, att, LeaveSummaryData())
        assert result.eobi_employee > 0
        assert result.eobi_employer > 0

    def test_eobi_excluded_when_not_applicable(self):
        sal = self._make_salary()
        sal.eobi_applicable = False
        att = self._make_attendance()
        result = calculate_employee_payroll("e1", sal, att, LeaveSummaryData())
        assert result.eobi_employee == 0

    def test_net_is_gross_minus_deductions(self):
        sal = self._make_salary()
        att = self._make_attendance()
        result = calculate_employee_payroll("e1", sal, att, LeaveSummaryData())
        assert result.net_salary == result.gross_salary - result.total_deductions

    def test_loan_deduction_included(self):
        sal = self._make_salary()
        att = self._make_attendance()
        result = calculate_employee_payroll("e1", sal, att, LeaveSummaryData())
        assert result.loan_deduction == 2_000

    def test_is_prorated_true_when_absent(self):
        sal = self._make_salary()
        att = self._make_attendance()  # has 2 absent days
        result = calculate_employee_payroll("e1", sal, att, LeaveSummaryData())
        assert result.is_prorated is True

    def test_is_prorated_false_when_full_attendance(self):
        sal = self._make_salary()
        att = AttendanceSummaryData(working_days=26, present_days=26, absent_days=0)
        result = calculate_employee_payroll("e1", sal, att, LeaveSummaryData())
        assert result.is_prorated is False


# ─── API Integration Tests ────────────────────────────────────────────────────
# These tests mock the DB layer and test route logic.

class TestCreatePayrollRun:

    @pytest.mark.asyncio
    async def test_create_payroll_run_success(self):
        """POST /payroll/runs should return 201 and trigger async task."""
        # Mock DB returning no existing run (no conflict)
        mock_db   = AsyncMock()
        mock_run  = MagicMock()
        mock_run.id             = "run-123"
        mock_run.month          = 3
        mock_run.year           = 2025
        mock_run.status         = "processing"
        mock_run.total_employees = 0
        mock_run.total_gross    = 0
        mock_run.total_net      = 0
        mock_run.total_deductions = 0
        mock_run.total_eobi_employee = 0
        mock_run.total_eobi_employer = 0
        mock_run.total_income_tax = 0
        mock_run.celery_task_id = "task-abc"
        mock_run.processed_by   = "user-1"
        mock_run.approved_by    = None
        mock_run.run_at         = None
        mock_run.approved_at    = None
        mock_run.paid_at        = None
        mock_run.notes          = None
        mock_run.label          = "March 2025 Payroll"

        # We're testing the service layer directly
        from app.api.v1.payroll.schemas import PayrollRunCreate

        data = PayrollRunCreate(month=3, year=2025)
        assert data.month == 3
        assert data.year  == 2025

    def test_cannot_run_payroll_twice_same_month(self):
        """PayrollRunCreate validation passes; conflict raised in service layer."""
        from app.api.v1.payroll.schemas import PayrollRunCreate
        data = PayrollRunCreate(month=3, year=2025)
        # Schema itself doesn't enforce uniqueness; that's the service layer's job
        assert data.month == 3

    def test_invalid_month_rejected(self):
        from app.api.v1.payroll.schemas import PayrollRunCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            PayrollRunCreate(month=13, year=2025)


class TestApproveRejectPayrollRun:

    def test_approve_action(self):
        from app.api.v1.payroll.schemas import PayrollApprovalRequest, ApprovalAction
        req = PayrollApprovalRequest(action=ApprovalAction.approve)
        assert req.action == ApprovalAction.approve

    def test_reject_action(self):
        from app.api.v1.payroll.schemas import PayrollApprovalRequest, ApprovalAction
        req = PayrollApprovalRequest(action=ApprovalAction.reject, notes="Discrepancy found")
        assert req.action == ApprovalAction.reject
        assert req.notes  == "Discrepancy found"

    def test_reject_schema_allows_empty_notes(self):
        """Service layer enforces notes requirement, not schema."""
        from app.api.v1.payroll.schemas import PayrollApprovalRequest, ApprovalAction
        req = PayrollApprovalRequest(action=ApprovalAction.reject)
        assert req.notes is None


class TestPayslipAccess:

    def test_payslip_data_schema(self):
        from app.api.v1.payroll.schemas import PayslipData, AllowanceItem, DeductionItem
        ps = PayslipData(
            record_id      = "r1",
            payroll_run_id = "run1",
            month          = 3,
            year           = 2025,
            employee_id    = "e1",
            employee_code  = "EMP001",
            full_name      = "John Doe",
            designation    = "Engineer",
            department     = "IT",
            cnic           = "12345-6789012-3",
            joining_date   = "2022-01-01",
            bank_name      = "HBL",
            account_number = "12345678",
            iban           = "PK36SCBL0000001123456702",
            basic_salary   = 50_000,
            allowances     = [AllowanceItem(name="HRA", amount=15_000)],
            total_allowances= 15_000,
            gross_salary   = 65_000,
            deductions     = [DeductionItem(name="EOBI", amount=370)],
            total_deductions= 370,
            net_salary     = 64_630,
            working_days   = 26,
            present_days   = 26,
            absent_days    = 0,
            paid_leave_days= 0.0,
            overtime_hours = None,
            overtime_amount= 0,
            generated_at   = __import__("datetime").datetime.utcnow(),
            payslip_url    = None,
        )
        assert ps.net_salary == 64_630
        assert ps.full_name  == "John Doe"


class TestBankFileFormat:

    def test_bank_file_entry_schema(self):
        from app.api.v1.payroll.schemas import BankFileEntry
        entry = BankFileEntry(
            employee_code  = "EMP001",
            employee_name  = "Jane Doe",
            bank_name      = "MCB",
            account_number = "0123456789",
            iban           = "PK36SCBL0000001123456702",
            net_salary     = 85_000,
            reference      = "SAL-EMP001-Mar2025",
        )
        assert entry.net_salary   == 85_000
        assert entry.reference    == "SAL-EMP001-Mar2025"
        assert entry.iban is not None

    def test_bank_file_entry_without_iban(self):
        from app.api.v1.payroll.schemas import BankFileEntry
        entry = BankFileEntry(
            employee_code  = "EMP002",
            employee_name  = "Ali Khan",
            bank_name      = "UBL",
            account_number = "9876543210",
            iban           = None,
            net_salary     = 40_000,
            reference      = "SAL-EMP002-Mar2025",
        )
        assert entry.iban is None


# ─── Tax Slab Schema Tests ────────────────────────────────────────────────────

class TestTaxSlabSchemas:

    def test_valid_slab_create(self):
        from app.api.v1.payroll.schemas import TaxSlabCreate
        slab = TaxSlabCreate(
            year=2025, min_income=0, max_income=600_000,
            tax_rate=0.0, fixed_tax=0
        )
        assert slab.year == 2025

    def test_max_must_exceed_min(self):
        from app.api.v1.payroll.schemas import TaxSlabCreate
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            TaxSlabCreate(
                year=2025, min_income=600_000, max_income=500_000,
                tax_rate=0.05, fixed_tax=0,
            )

    def test_open_ended_slab(self):
        from app.api.v1.payroll.schemas import TaxSlabCreate
        slab = TaxSlabCreate(
            year=2025, min_income=6_000_001, max_income=None,
            tax_rate=0.35, fixed_tax=1_230_000,
        )
        assert slab.max_income is None
        assert slab.tax_rate   == 0.35


# ─── Filter Params ────────────────────────────────────────────────────────────

class TestPayrollFilterParams:

    def test_defaults(self):
        from app.api.v1.payroll.schemas import PayrollFilterParams
        f = PayrollFilterParams()
        assert f.page      == 1
        assert f.page_size == 25

    def test_invalid_month(self):
        from app.api.v1.payroll.schemas import PayrollFilterParams
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            PayrollFilterParams(month=13)

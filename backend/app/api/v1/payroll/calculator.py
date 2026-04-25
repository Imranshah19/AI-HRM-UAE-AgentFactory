"""
AI-HRMS — Payroll calculation engine.

Pure functions only — no database calls, fully unit-testable.
All monetary values are integers (PKR paisa-less; rounded to nearest rupee).

Pakistan FBR 2024-25 income tax slabs are hardcoded as fallback.
If tax_slabs are provided from DB, they override the hardcoded defaults.
"""

from __future__ import annotations

import calendar
import math
from dataclasses import dataclass, field
from typing      import Optional


# ─── Pakistan FBR 2024-25 Tax Slabs ──────────────────────────────────────────
# (min_income, max_income_or_None, fixed_tax, rate_on_excess)
# All values in PKR annually.

DEFAULT_FBR_SLABS: list[tuple[int, Optional[int], int, float]] = [
    (0,         600_000,  0,         0.00),   # 0%
    (600_001,   1_200_000, 0,        0.05),   # 5% of amount above 600k
    (1_200_001, 2_400_000, 30_000,   0.15),   # 30k + 15% above 1.2M
    (2_400_001, 3_600_000, 210_000,  0.25),   # 210k + 25% above 2.4M
    (3_600_001, 6_000_000, 510_000,  0.30),   # 510k + 30% above 3.6M
    (6_000_001, None,      1_230_000, 0.35),  # 1.23M + 35% above 6M
]


# ─── Data containers ─────────────────────────────────────────────────────────

@dataclass
class TaxSlabData:
    min_income: int
    max_income: Optional[int]
    fixed_tax:  int
    tax_rate:   float          # e.g. 0.15 = 15%


@dataclass
class SalaryStructureData:
    basic_salary:          int
    house_rent_allowance:  int = 0
    medical_allowance:     int = 0
    transport_allowance:   int = 0
    fuel_allowance:        int = 0
    utility_allowance:     int = 0
    other_allowances:      dict = field(default_factory=dict)
    eobi_applicable:       bool = True
    sessi_applicable:      bool = False
    income_tax_applicable: bool = True
    loan_deduction:        int = 0
    advance_deduction:     int = 0


@dataclass
class AttendanceSummaryData:
    working_days:  int
    present_days:  int
    absent_days:   int
    late_days:     int = 0
    overtime_hours: float = 0.0
    shift_hours:   float = 8.0   # standard shift hours per day


@dataclass
class LeaveSummaryData:
    paid_leave_days:   float = 0.0
    unpaid_leave_days: float = 0.0


@dataclass
class PayrollRecordData:
    employee_id:           str
    basic_salary:          int
    house_rent_allowance:  int
    medical_allowance:     int
    transport_allowance:   int
    fuel_allowance:        int
    utility_allowance:     int
    other_allowances:      dict
    total_allowances:      int
    gross_salary:          int
    eobi_employee:         int
    eobi_employer:         int
    sessi:                 int
    income_tax:            int
    loan_deduction:        int
    advance_deduction:     int
    other_deductions:      dict
    total_deductions:      int
    net_salary:            int
    working_days:          int
    present_days:          int
    absent_days:           int
    late_days:             int
    overtime_hours:        float
    overtime_amount:       int
    paid_leave_days:       float
    unpaid_leave_days:     float
    is_prorated:           bool


# ─── Tax Calculation ──────────────────────────────────────────────────────────

def _build_slabs(tax_slabs: list[TaxSlabData] | None) -> list[tuple[int, Optional[int], int, float]]:
    """Convert TaxSlabData list to sorted internal tuples, falling back to FBR defaults."""
    if not tax_slabs:
        return DEFAULT_FBR_SLABS
    slabs = sorted(
        [(s.min_income, s.max_income, s.fixed_tax, s.tax_rate) for s in tax_slabs],
        key=lambda x: x[0],
    )
    return slabs if slabs else DEFAULT_FBR_SLABS


def calculate_income_tax(
    annual_salary: int,
    tax_slabs: list[TaxSlabData] | None = None,
) -> int:
    """
    Calculate monthly income tax from annual gross salary.

    Uses Pakistan FBR 2024-25 slabs by default.
    If tax_slabs provided (from DB), uses those instead.

    Returns: monthly tax amount (integer, rounded up).
    """
    if annual_salary <= 0:
        return 0

    slabs = _build_slabs(tax_slabs)

    annual_tax = 0
    for min_inc, max_inc, fixed, rate in slabs:
        if annual_salary < min_inc:
            break
        if max_inc is None or annual_salary <= max_inc:
            excess = annual_salary - (min_inc - 1)
            annual_tax = fixed + math.floor(excess * rate)
            break
        # salary is above this slab's max — continue to next slab

    monthly_tax = math.ceil(annual_tax / 12)
    return monthly_tax


def calculate_income_tax_breakdown(
    annual_salary: int,
    tax_slabs: list[TaxSlabData] | None = None,
) -> dict:
    """
    Returns detailed tax breakdown (used by TaxCalculatorWidget).
    """
    if annual_salary <= 0:
        return {
            "annual_salary": annual_salary,
            "annual_tax":    0,
            "monthly_tax":   0,
            "effective_rate": 0.0,
            "slab_applied":  None,
        }

    slabs = _build_slabs(tax_slabs)
    annual_tax   = 0
    slab_applied = None

    for min_inc, max_inc, fixed, rate in slabs:
        if annual_salary < min_inc:
            break
        if max_inc is None or annual_salary <= max_inc:
            excess = annual_salary - (min_inc - 1)
            annual_tax   = fixed + math.floor(excess * rate)
            slab_applied = {
                "min_income": min_inc,
                "max_income": max_inc,
                "fixed_tax":  fixed,
                "tax_rate":   rate,
            }
            break

    effective_rate = (annual_tax / annual_salary) if annual_salary > 0 else 0.0
    monthly_tax    = math.ceil(annual_tax / 12)

    return {
        "annual_salary":  annual_salary,
        "annual_tax":     annual_tax,
        "monthly_tax":    monthly_tax,
        "effective_rate": round(effective_rate, 4),
        "slab_applied":   slab_applied,
    }


# ─── EOBI Calculation ─────────────────────────────────────────────────────────

EOBI_EMPLOYEE_RATE    = 0.01    # 1% of basic
EOBI_EMPLOYER_RATE    = 0.05    # 5% of basic
EOBI_EMPLOYEE_MAX_PKR = 370     # PKR/month cap
EOBI_EMPLOYER_MAX_PKR = 1_850   # PKR/month cap


def calculate_eobi(basic_salary: int) -> dict[str, int]:
    """
    Calculate EOBI (Employees' Old-Age Benefits Institution) contributions.

    Employee: 1% of basic, capped at PKR 370/month
    Employer: 5% of basic, capped at PKR 1,850/month

    Returns: {"employee": int, "employer": int}
    """
    employee = min(math.floor(basic_salary * EOBI_EMPLOYEE_RATE), EOBI_EMPLOYEE_MAX_PKR)
    employer = min(math.floor(basic_salary * EOBI_EMPLOYER_RATE), EOBI_EMPLOYER_MAX_PKR)
    return {"employee": employee, "employer": employer}


# ─── Overtime Calculation ─────────────────────────────────────────────────────

def calculate_overtime(
    overtime_hours: float,
    basic_salary:   int,
    working_days:   int,
    shift_hours:    float = 8.0,
) -> int:
    """
    Calculate overtime pay.

    hourly_rate   = basic_salary / (working_days * shift_hours)
    overtime_rate = hourly_rate * 1.5
    amount        = overtime_rate * overtime_hours

    Returns: overtime amount (integer PKR).
    """
    if overtime_hours <= 0 or working_days <= 0 or shift_hours <= 0:
        return 0
    hourly_rate   = basic_salary / (working_days * shift_hours)
    overtime_rate = hourly_rate * 1.5
    return math.floor(overtime_rate * overtime_hours)


# ─── Absent Deduction ─────────────────────────────────────────────────────────

def calculate_absent_deduction(
    basic_salary: int,
    working_days: int,
    absent_days:  int,
) -> int:
    """
    Deduct salary for absent days.

    per_day_rate = basic_salary / working_days
    deduction    = per_day_rate * absent_days

    Returns: deduction amount (integer PKR).
    """
    if absent_days <= 0 or working_days <= 0:
        return 0
    per_day   = basic_salary / working_days
    deduction = math.floor(per_day * absent_days)
    return deduction


# ─── Net Salary ───────────────────────────────────────────────────────────────

def calculate_net_salary(gross: int, total_deductions: int) -> int:
    """net = gross - deductions (floored at 0)."""
    return max(0, gross - total_deductions)


# ─── Total Allowances ─────────────────────────────────────────────────────────

def calculate_total_allowances(salary: SalaryStructureData) -> int:
    fixed = (
        salary.house_rent_allowance
        + salary.medical_allowance
        + salary.transport_allowance
        + salary.fuel_allowance
        + salary.utility_allowance
    )
    other = sum(salary.other_allowances.values()) if salary.other_allowances else 0
    return fixed + other


# ─── Working days in month ────────────────────────────────────────────────────

def get_working_days(month: int, year: int) -> int:
    """
    Return the number of Mon-Fri working days in a given month.
    Does NOT account for public holidays (caller handles that if needed).
    """
    _, days_in_month = calendar.monthrange(year, month)
    count = 0
    for day in range(1, days_in_month + 1):
        if calendar.weekday(year, month, day) < 5:  # 0=Mon … 4=Fri
            count += 1
    return count


# ─── Orchestrator ─────────────────────────────────────────────────────────────

def calculate_employee_payroll(
    employee_id:        str,
    salary:             SalaryStructureData,
    attendance:         AttendanceSummaryData,
    leaves:             LeaveSummaryData,
    tax_slabs:          list[TaxSlabData] | None = None,
    month:              int = 1,
    year:               int = 2025,
) -> PayrollRecordData:
    """
    Full payroll calculation for one employee in one pay period.
    Orchestrates all sub-calculations. Pure function — no DB I/O.
    """
    # 1. Allowances & gross
    total_allowances = calculate_total_allowances(salary)
    gross_salary     = salary.basic_salary + total_allowances

    # 2. Absent deduction (unpaid leave days also treated as absent for pay purposes)
    effective_absent = attendance.absent_days + math.floor(leaves.unpaid_leave_days)
    absent_deduction = calculate_absent_deduction(
        salary.basic_salary, attendance.working_days, effective_absent
    )

    # 3. Overtime
    overtime_amount = calculate_overtime(
        attendance.overtime_hours,
        salary.basic_salary,
        attendance.working_days,
        attendance.shift_hours,
    )

    # Adjust gross for overtime and absent deduction
    adjusted_gross = max(0, gross_salary - absent_deduction + overtime_amount)

    # 4. EOBI
    eobi = {"employee": 0, "employer": 0}
    if salary.eobi_applicable:
        eobi = calculate_eobi(salary.basic_salary)

    # 5. Income tax (on annualised adjusted gross)
    income_tax = 0
    if salary.income_tax_applicable:
        annual_gross = adjusted_gross * 12
        income_tax   = calculate_income_tax(annual_gross, tax_slabs)

    # 6. Deductions total
    total_deductions = (
        eobi["employee"]
        + income_tax
        + salary.loan_deduction
        + salary.advance_deduction
    )

    # 7. Net
    net_salary = calculate_net_salary(adjusted_gross, total_deductions)

    return PayrollRecordData(
        employee_id           = employee_id,
        basic_salary          = salary.basic_salary,
        house_rent_allowance  = salary.house_rent_allowance,
        medical_allowance     = salary.medical_allowance,
        transport_allowance   = salary.transport_allowance,
        fuel_allowance        = salary.fuel_allowance,
        utility_allowance     = salary.utility_allowance,
        other_allowances      = salary.other_allowances or {},
        total_allowances      = total_allowances,
        gross_salary          = adjusted_gross,
        eobi_employee         = eobi["employee"],
        eobi_employer         = eobi["employer"],
        sessi                 = 0,
        income_tax            = income_tax,
        loan_deduction        = salary.loan_deduction,
        advance_deduction     = salary.advance_deduction,
        other_deductions      = {},
        total_deductions      = total_deductions,
        net_salary            = net_salary,
        working_days          = attendance.working_days,
        present_days          = attendance.present_days,
        absent_days           = attendance.absent_days,
        late_days             = attendance.late_days,
        overtime_hours        = attendance.overtime_hours,
        overtime_amount       = overtime_amount,
        paid_leave_days       = leaves.paid_leave_days,
        unpaid_leave_days     = leaves.unpaid_leave_days,
        is_prorated           = effective_absent > 0,
    )

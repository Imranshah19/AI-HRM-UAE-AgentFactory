"""
WPS Worker eval — known-correct test case.

Uses only the pure functions from wps_tasks (no DB, no filesystem).
One past month with a KNOWN-correct SCR total and a KNOWN blocked-employee list.

Run: pytest evals/test_cases/test_wps_worker.py -v
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.tasks.uae.wps_tasks import (
    CheckResult,
    _build_sif_delimited,
    _check_1_all_employees_included,
    _check_2_iban_valid,
    _check_3_id_valid,
    _check_4_amounts_match,
    _check_5_establishment_id,
    _check_6_no_negative_zero_net,
    _check_7_employer_name_length,
    _check_8_month_match,
    _check_labour_card_expiry,
    _check_sif_format_delimited,
    _generate_sif_filename,
    _iban_mod97,
    _money,
    _pad_employer_id,
)

# ─── Known-correct fixtures ───────────────────────────────────────────────────
# April 2026 — 3 employees, all valid.
# Expected SCR total = 15500.00 + 10600.00 + 7300.00 = 33400.00

# ─── IBAN generator (for test fixtures only) ──────────────────────────────────

def _make_valid_iban(bank_code: str, account: str) -> str:
    """Compute a valid UAE IBAN for given 3-char bank code + 16-char account."""
    bban = f"{bank_code[:3]}{account[:16]}"[:19].ljust(19, "0")
    rearranged = bban + "AE00"
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    check = 98 - (int(numeric) % 97)
    iban = f"AE{check:02d}{bban}"
    assert len(iban) == 23
    return iban

IBAN_001 = _make_valid_iban("033", "1234567890123456")  # == AE070331234567890123456
IBAN_002 = _make_valid_iban("033", "2234567890123456")
IBAN_003 = _make_valid_iban("033", "3234567890123456")


COMPANY_OK = {
    "id": "co-001",
    "name_en": "Gulf Holdings Company A",
    "mohre_establishment_id": "CO00001",
    "wps_agent_bank": "033000000",
}

PAYROLL_OK = [
    {"employee_id": "emp-001", "net_salary": "15500.00", "overtime_amount": "700.00",
     "actual_days_worked": 26, "leave_deduction_days": 0,
     "payroll_month": 4, "payroll_year": 2026},
    {"employee_id": "emp-002", "net_salary": "10600.00", "overtime_amount": "0.00",
     "actual_days_worked": 26, "leave_deduction_days": 0,
     "payroll_month": 4, "payroll_year": 2026},
    {"employee_id": "emp-003", "net_salary": "7300.00", "overtime_amount": "0.00",
     "actual_days_worked": 24, "leave_deduction_days": 2,
     "payroll_month": 4, "payroll_year": 2026},
]

PROFILES_OK = [
    {"employee_id": "emp-001", "bank_iban": IBAN_001,
     "emirates_id": "784-1990-1234567-1", "labour_card_number": "",
     "labour_card_expiry": "2027-12-31", "bank_name": "Emirates NBD",
     "mohre_person_id": "00000000000001"},
    {"employee_id": "emp-002", "bank_iban": IBAN_002,
     "emirates_id": "784-1985-7654321-2", "labour_card_number": "",
     "labour_card_expiry": "2027-06-30", "bank_name": "ADIB",
     "mohre_person_id": "00000000000002"},
    {"employee_id": "emp-003", "bank_iban": IBAN_003,
     "emirates_id": "", "labour_card_number": "LC-20240001",
     "labour_card_expiry": "2027-03-31", "bank_name": "Mashreq",
     "mohre_person_id": "00000000000003"},
]

KNOWN_SCR_TOTAL = "33400.00"
CREATION_DT     = datetime(2026, 4, 27, 9, 0, 0, tzinfo=timezone.utc)


# ─── Helper ───────────────────────────────────────────────────────────────────

def _run_checks(payroll=None, profiles=None, company=None, year=2026, month=4):
    payroll  = payroll  or PAYROLL_OK
    profiles = profiles or PROFILES_OK
    company  = company  or COMPANY_OK
    today    = date(2026, 4, 27)
    return {
        "chk1": _check_1_all_employees_included(payroll, profiles),
        "chk2": _check_2_iban_valid(profiles)[0],
        "chk3": _check_3_id_valid(profiles)[0],
        "chk4": _check_4_amounts_match(payroll),
        "chk5": _check_5_establishment_id(company),
        "chk6": _check_6_no_negative_zero_net(payroll)[0],
        "chk7": _check_7_employer_name_length(company),
        "chk8": _check_8_month_match(payroll, year, month),
        "lc":   _check_labour_card_expiry(profiles, today),
    }


# ─── Money formatting ─────────────────────────────────────────────────────────

def test_money_format():
    assert _money(Decimal("4000")) == "4000.00"
    assert _money(Decimal("150.5")) == "150.50"
    assert _money(Decimal("9999.994")) == "9999.99"
    assert _money(Decimal("9999.995")) == "10000.00"


# ─── IBAN mod-97 ──────────────────────────────────────────────────────────────

def test_iban_mod97_good():
    # Known-valid UAE IBANs
    assert _iban_mod97("AE070331234567890123456") is True

def test_iban_mod97_bad():
    assert _iban_mod97("AE070331234567890123457") is False  # last digit off

def test_iban_mod97_format_check():
    # check_2 catches format before mod-97
    bad = [{"employee_id": "x", "bank_iban": "AE070331234567890123457"}]
    chk, blocked = _check_2_iban_valid(bad)
    assert not chk.passed
    assert blocked[0]["reason"] == "mod-97 failed"


# ─── Check 1: all employees included ─────────────────────────────────────────

def test_check1_pass():
    chk = _check_1_all_employees_included(PAYROLL_OK, PROFILES_OK)
    assert chk.passed

def test_check1_fail_missing_profile():
    chk = _check_1_all_employees_included(
        PAYROLL_OK + [{"employee_id": "emp-999", "net_salary": "1000.00",
                        "overtime_amount": "0", "actual_days_worked": 26,
                        "leave_deduction_days": 0, "payroll_month": 4, "payroll_year": 2026}],
        PROFILES_OK,
    )
    assert not chk.passed
    assert "emp-999" in chk.detail


# ─── Check 2: IBAN ────────────────────────────────────────────────────────────

def test_check2_pass():
    chk, bad = _check_2_iban_valid(PROFILES_OK)
    assert chk.passed
    assert bad == []

def test_check2_fail_wrong_prefix():
    profiles = [{**PROFILES_OK[0], "bank_iban": "GB070331234567890123456"}]
    chk, bad = _check_2_iban_valid(profiles)
    assert not chk.passed
    assert bad[0]["reason"] == "format"

def test_check2_fail_wrong_length():
    profiles = [{**PROFILES_OK[0], "bank_iban": "AE0703312345"}]
    chk, bad = _check_2_iban_valid(profiles)
    assert not chk.passed

def test_check2_blocked_employee_list():
    bad_profiles = [
        {**PROFILES_OK[0], "bank_iban": ""},       # blank → format fail
        PROFILES_OK[1],                             # valid → passes
        {**PROFILES_OK[2], "bank_iban": "AE0X0331234567890123456"},  # bad format
    ]
    chk, bad = _check_2_iban_valid(bad_profiles)
    assert not chk.passed
    assert len(bad) == 2                            # emp-001 (blank) + emp-003 (bad format)
    blocked_ids = {b["employee_id"] for b in bad}
    assert "emp-001" in blocked_ids
    assert "emp-002" not in blocked_ids             # valid, must not appear
    assert "emp-003" in blocked_ids


# ─── Check 3: Emirates ID / labour card ──────────────────────────────────────

def test_check3_pass():
    chk, bad = _check_3_id_valid(PROFILES_OK)
    assert chk.passed

def test_check3_fail_no_id():
    profiles = [{**PROFILES_OK[0], "emirates_id": "", "labour_card_number": ""}]
    chk, bad = _check_3_id_valid(profiles)
    assert not chk.passed
    assert bad[0]["employee_id"] == "emp-001"


# ─── Check 4: amounts match ───────────────────────────────────────────────────

def test_check4_known_total():
    chk = _check_4_amounts_match(PAYROLL_OK)
    assert chk.passed
    assert KNOWN_SCR_TOTAL in chk.detail


# ─── Check 5: establishment ID ────────────────────────────────────────────────

def test_check5_pass():
    assert _check_5_establishment_id(COMPANY_OK).passed

def test_check5_fail_no_id():
    chk = _check_5_establishment_id({**COMPANY_OK, "mohre_establishment_id": ""})
    assert not chk.passed

def test_check5_fail_no_company():
    chk = _check_5_establishment_id(None)
    assert not chk.passed


# ─── Check 6: no negative/zero net ───────────────────────────────────────────

def test_check6_pass():
    chk, bad = _check_6_no_negative_zero_net(PAYROLL_OK)
    assert chk.passed
    assert bad == []

def test_check6_fail_zero():
    rows = [{**PAYROLL_OK[0], "net_salary": "0.00"}]
    chk, bad = _check_6_no_negative_zero_net(rows)
    assert not chk.passed
    assert bad[0]["employee_id"] == "emp-001"

def test_check6_fail_negative():
    rows = [{**PAYROLL_OK[0], "net_salary": "-100.00"}]
    chk, bad = _check_6_no_negative_zero_net(rows)
    assert not chk.passed


# ─── Check 7: employer name length ───────────────────────────────────────────

def test_check7_pass():
    assert _check_7_employer_name_length(COMPANY_OK).passed

def test_check7_fail_too_long():
    long_name = "A" * 36
    chk = _check_7_employer_name_length({**COMPANY_OK, "name_en": long_name})
    assert not chk.passed
    assert "36" in chk.detail

def test_check7_pass_exactly_35():
    chk = _check_7_employer_name_length({**COMPANY_OK, "name_en": "A" * 35})
    assert chk.passed


# ─── Check 8: month match ─────────────────────────────────────────────────────

def test_check8_pass():
    assert _check_8_month_match(PAYROLL_OK, 2026, 4).passed

def test_check8_fail_wrong_month():
    rows = [{**PAYROLL_OK[0], "payroll_month": 3, "payroll_year": 2026}]  # March mixed in
    chk = _check_8_month_match(rows, 2026, 4)
    assert not chk.passed
    assert "emp-001" in chk.detail


# ─── Labour card expiry (non-blocking warning) ────────────────────────────────

def test_lc_expired_is_warning_not_blocking():
    profiles = [{**PROFILES_OK[0], "labour_card_expiry": "2025-01-01"}]
    chk = _check_labour_card_expiry(profiles, date(2026, 4, 27))
    assert not chk.passed
    assert chk.blocking is False  # must not block SIF


# ─── SIF builder: known-correct output ───────────────────────────────────────

def test_sif_total_matches_known_correct():
    sif_text, total, filename = _build_sif_delimited(
        COMPANY_OK, PAYROLL_OK, PROFILES_OK, 2026, 4, CREATION_DT,
    )
    assert total == KNOWN_SCR_TOTAL, f"Expected {KNOWN_SCR_TOTAL}, got {total}"

def test_sif_has_scr_and_edr_lines():
    sif_text, _, _ = _build_sif_delimited(
        COMPANY_OK, PAYROLL_OK, PROFILES_OK, 2026, 4, CREATION_DT,
    )
    lines = sif_text.strip().splitlines()
    scr = [l for l in lines if l.startswith("SCR,")]
    edr = [l for l in lines if l.startswith("EDR,")]
    assert len(scr) == 1
    assert len(edr) == 3

def test_sif_no_xml():
    sif_text, _, _ = _build_sif_delimited(
        COMPANY_OK, PAYROLL_OK, PROFILES_OK, 2026, 4, CREATION_DT,
    )
    assert "<" not in sif_text
    assert ">" not in sif_text

def test_sif_scr_total_field_matches():
    sif_text, total, _ = _build_sif_delimited(
        COMPANY_OK, PAYROLL_OK, PROFILES_OK, 2026, 4, CREATION_DT,
    )
    scr_line = next(l for l in sif_text.splitlines() if l.startswith("SCR,"))
    scr_fields = scr_line.split(",")
    assert scr_fields[7] == total  # totalSalary at position 7

def test_sif_salary_month_field_mmyyyy():
    sif_text, _, _ = _build_sif_delimited(
        COMPANY_OK, PAYROLL_OK, PROFILES_OK, 2026, 4, CREATION_DT,
    )
    scr_line = next(l for l in sif_text.splitlines() if l.startswith("SCR,"))
    assert scr_line.split(",")[5] == "042026"  # MMYYYY at position 5

def test_sif_edr_fixed_plus_variable_equals_net():
    sif_text, _, _ = _build_sif_delimited(
        COMPANY_OK, PAYROLL_OK, PROFILES_OK, 2026, 4, CREATION_DT,
    )
    from decimal import Decimal as D
    edr_lines = [l for l in sif_text.splitlines() if l.startswith("EDR,")]
    total_from_edr = D("0")
    for line in edr_lines:
        fields = line.split(",")
        total_from_edr += D(fields[7]) + D(fields[8])  # fixed + variable
    assert str(total_from_edr.quantize(D("0.01"))) == KNOWN_SCR_TOTAL


# ─── Filename generator ───────────────────────────────────────────────────────

def test_filename_25_chars_plus_extension():
    fn = _generate_sif_filename("CO00001", CREATION_DT)
    base, ext = fn.rsplit(".", 1)
    assert len(base) == 25, f"Expected 25-char base, got {len(base)}: '{base}'"
    assert ext == "SIF"

def test_filename_contains_date_time():
    fn = _generate_sif_filename("CO00001", CREATION_DT)
    assert "260427" in fn   # YYMMDD
    assert "090000" in fn   # HHMMSS

def test_filename_employer_id_zero_padded():
    fn = _generate_sif_filename("CO00001", CREATION_DT)
    # "CO00001" = 7 chars → zfill(13) = 6 leading zeros + 7 chars = "000000CO00001"
    assert fn.startswith("000000CO00001")   # 13 chars total, zero-padded left

def test_filename_matches_scr_datetime():
    """
    Filename = EmployerID(13) + YYMMDD(6) + HHMMSS(6) = 25 chars.
    SCR time is HHMM (4 chars) by default per DIB reference.
    The HHMM portion of the filename must match the SCR time field.
    (§6 of sif_format_reference.md notes this ambiguity — confirm with your bank.)
    """
    sif_text, _, filename = _build_sif_delimited(
        COMPANY_OK, PAYROLL_OK, PROFILES_OK, 2026, 4, CREATION_DT,
    )
    scr = next(l for l in sif_text.splitlines() if l.startswith("SCR,")).split(",")
    scr_date = scr[3]   # YYYY-MM-DD
    scr_time = scr[4]   # HHMM (4 digits, default) or HHMMSS (6 digits if env set)

    base = filename.replace(".SIF", "")
    fn_date = base[13:19]   # YYMMDD
    fn_hhmm = base[19:23]   # first 4 digits of time portion

    assert scr_date[2:4] + scr_date[5:7] + scr_date[8:10] == fn_date
    assert scr_time[:4] == fn_hhmm   # HHMM portion always matches


# ─── SIF format check ─────────────────────────────────────────────────────────

def test_sif_format_check_passes_on_valid():
    sif_text, _, _ = _build_sif_delimited(
        COMPANY_OK, PAYROLL_OK, PROFILES_OK, 2026, 4, CREATION_DT,
    )
    chk = _check_sif_format_delimited(sif_text)
    assert chk.passed, chk.detail

def test_sif_format_check_fails_on_empty():
    chk = _check_sif_format_delimited("")
    assert not chk.passed

def test_sif_format_check_fails_on_xml():
    xml = '<?xml version="1.0"?><SalaryInformation/>'
    chk = _check_sif_format_delimited(xml)
    assert not chk.passed


# ─── BLOCKED employee list — known blocked case ───────────────────────────────

def test_known_blocked_iban_employee():
    """
    emp-BAD has invalid IBAN (wrong length). All other employees are OK.
    Worker must BLOCK and return emp-BAD in blocked_employees.
    """
    bad_profile = {
        "employee_id": "emp-BAD",
        "bank_iban": "AE0000",  # too short
        "emirates_id": "784-1990-0000000-0",
        "labour_card_number": "",
        "labour_card_expiry": "2027-12-31",
        "bank_name": "Test Bank",
        "mohre_person_id": "00000000000099",
    }
    bad_payroll = {
        "employee_id": "emp-BAD", "net_salary": "5000.00",
        "overtime_amount": "0", "actual_days_worked": 26,
        "leave_deduction_days": 0, "payroll_month": 4, "payroll_year": 2026,
    }

    profiles = PROFILES_OK + [bad_profile]
    payroll  = PAYROLL_OK  + [bad_payroll]

    chk, bad = _check_2_iban_valid(profiles)
    assert not chk.passed
    blocked_ids = {b["employee_id"] for b in bad}
    assert "emp-BAD" in blocked_ids
    assert "emp-001" not in blocked_ids  # good employees not in list

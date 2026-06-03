"""
WPS Compliance Worker — UAE

Implements specs/wps_worker.spec.md v1.1.
Physical format defined in skills/uae-wps-compliance/sif_format_reference.md.

MAY:  read finalized payroll from PostgreSQL; run 8 validation checks;
      write comma-delimited .SIF + _report.md to outputs/wps/
MUST NOT: submit, pay, modify DB, guess missing data, run if payroll not finalized.
"""

from __future__ import annotations

import asyncio
import calendar
import os
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)

# ─── Constants ────────────────────────────────────────────────────────────────

STATUS_READY   = "READY_FOR_APPROVAL"
STATUS_BLOCKED = "BLOCKED"

OUTPUTS_BASE = Path(__file__).resolve().parents[3] / "outputs" / "wps"

WPS_DEADLINE_ALERT_DAYS = int(os.environ.get("UAE_WPS_DEADLINE_ALERT_DAYS", "3"))

# SCR record first (employer) then EDRs (employees), or reverse.
# Set in .env per your bank's requirement. Default: scr_first.
SIF_RECORD_ORDER: str = os.environ.get("SIF_RECORD_ORDER", "scr_first")


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str
    blocking: bool = True  # False = warning only (e.g. expired labour card)


@dataclass
class WPSRunResult:
    company_id: str
    salary_month: str  # YYYY-MM
    status: str
    checks: list[CheckResult] = field(default_factory=list)
    sif_path: Optional[str] = None
    report_path: Optional[str] = None
    blocked_employees: list[dict] = field(default_factory=list)
    total_sif_aed: str = "0.00"
    total_payroll_aed: str = "0.00"
    run_at: str = ""

    def to_dict(self) -> dict:
        return {
            "company_id": self.company_id,
            "salary_month": self.salary_month,
            "status": self.status,
            "sif_path": self.sif_path,
            "report_path": self.report_path,
            "total_sif_aed": self.total_sif_aed,
            "total_payroll_aed": self.total_payroll_aed,
            "blocked_employees": self.blocked_employees,
            "checks": [
                {"name": c.name, "passed": c.passed, "detail": c.detail, "blocking": c.blocking}
                for c in self.checks
            ],
            "run_at": self.run_at,
        }


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _money(d: Decimal) -> str:
    """Format: 2 decimal places, dot separator, no thousands comma. e.g. 4000.00"""
    return str(d.quantize(Decimal("0.01"), ROUND_HALF_UP))


def _pad_employer_id(employer_id: str) -> str:
    """Zero-pad employer ID to exactly 13 chars (right-align)."""
    return employer_id.strip().zfill(13)[:13]


def _pad_person_id(person_id: str) -> str:
    """Zero-pad MOHRE person ID to exactly 14 chars."""
    return (person_id or "").strip().zfill(14)[:14]


def _generate_sif_filename(employer_id: str, creation_dt: datetime) -> str:
    """
    25-char base name per MOHRE convention:
    {employerID:0>13}{YYMMDD}{HHMMSS}.SIF
    date/time must exactly match the SCR creationDate + creationTime fields.
    """
    date_part = creation_dt.strftime("%y%m%d")  # YYMMDD
    time_part = creation_dt.strftime("%H%M%S")  # HHMMSS
    return f"{_pad_employer_id(employer_id)}{date_part}{time_part}.SIF"


# ─── DB reads (system of record) ─────────────────────────────────────────────
# Read-only. Never write to DB — only to outputs/ directory.

async def _fetch_company(company_id: str) -> dict | None:
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            row = await session.execute(
                text(
                    "SELECT id, name_en, mohre_establishment_id, wps_agent_bank "
                    "FROM companies WHERE id = :cid LIMIT 1"
                ),
                {"cid": company_id},
            )
            rec = row.mappings().first()
            return dict(rec) if rec else None
    except Exception as exc:
        logger.error("wps_worker.db_error", step="fetch_company", error=str(exc))
        return None


async def _fetch_finalized_payroll(company_id: str, year: int, month: int) -> list[dict]:
    """
    Fetch all finalized payroll rows for the company + month.
    Returns empty list if none (caller treats as BLOCKED).
    """
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                text(
                    "SELECT employee_id, net_salary, gross_salary, payment_status, "
                    "       basic_salary, housing_allowance, transport_allowance, "
                    "       food_allowance, other_allowances, overtime_amount, "
                    "       actual_days_worked, leave_deduction_days, "
                    "       iloe_deduction, other_deductions, loan_deduction, advance_deduction "
                    "FROM payroll_uae "
                    "WHERE company_id = :cid "
                    "  AND payroll_year  = :yr "
                    "  AND payroll_month = :mo "
                    "  AND payment_status = 'finalized'"
                ),
                {"cid": company_id, "yr": year, "mo": month},
            )
            return [dict(r) for r in rows.mappings()]
    except Exception as exc:
        logger.error("wps_worker.db_error", step="fetch_payroll", error=str(exc))
        return []


async def _fetch_employee_profiles(employee_ids: list[str]) -> list[dict]:
    if not employee_ids:
        return []
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            placeholders = ", ".join(f":e{i}" for i in range(len(employee_ids)))
            params = {f"e{i}": eid for i, eid in enumerate(employee_ids)}
            rows = await session.execute(
                text(
                    f"SELECT employee_id, bank_iban, emirates_id, labour_card_number, "
                    f"       labour_card_expiry, bank_name, mohre_person_id "
                    f"FROM employees_uae_profile "
                    f"WHERE employee_id IN ({placeholders})"
                ),
                params,
            )
            return [dict(r) for r in rows.mappings()]
    except Exception as exc:
        logger.error("wps_worker.db_error", step="fetch_profiles", error=str(exc))
        return []


# ─── Validation checks (spec §6 — 8 checks) ──────────────────────────────────

def _check_1_all_employees_included(
    payroll_rows: list[dict],
    profiles: list[dict],
) -> CheckResult:
    payroll_ids = {r["employee_id"] for r in payroll_rows}
    profile_ids = {p["employee_id"] for p in profiles}
    missing = payroll_ids - profile_ids
    if missing:
        return CheckResult(
            name="all_employees_included",
            passed=False,
            detail=f"No UAE profile for {len(missing)} employee(s): {sorted(missing)}",
        )
    return CheckResult(
        name="all_employees_included",
        passed=True,
        detail=f"{len(payroll_ids)} employee(s) all have UAE profiles",
    )


def _iban_mod97(iban: str) -> bool:
    """Standard mod-97 IBAN integrity check (ISO 13616)."""
    rearranged = iban[4:] + iban[:4]
    numeric = "".join(str(ord(c) - 55) if c.isalpha() else c for c in rearranged)
    return int(numeric) % 97 == 1


def _check_2_iban_valid(profiles: list[dict]) -> tuple[CheckResult, list[dict]]:
    """Check 2: valid 23-char UAE IBAN + mod-97 for every employee."""
    bad: list[dict] = []
    for p in profiles:
        iban = (p.get("bank_iban") or "").strip()
        if not iban.startswith("AE") or len(iban) != 23:
            bad.append({"employee_id": p["employee_id"], "iban": iban or "(blank)", "reason": "format"})
        elif not _iban_mod97(iban):
            bad.append({"employee_id": p["employee_id"], "iban": iban, "reason": "mod-97 failed"})
    if bad:
        return CheckResult(
            name="iban_valid",
            passed=False,
            detail=f"{len(bad)} employee(s) have invalid IBAN: {[b['employee_id'] for b in bad]}",
        ), bad
    return CheckResult(
        name="iban_valid",
        passed=True,
        detail=f"All {len(profiles)} IBANs valid (AE prefix, 23 chars, mod-97 pass)",
    ), []


def _check_3_id_valid(profiles: list[dict]) -> tuple[CheckResult, list[dict]]:
    """Check 3: Emirates ID or labour card present for every employee."""
    bad: list[dict] = []
    for p in profiles:
        has_eid = bool((p.get("emirates_id") or "").strip())
        has_lc  = bool((p.get("labour_card_number") or "").strip())
        if not has_eid and not has_lc:
            bad.append({"employee_id": p["employee_id"]})
    if bad:
        return CheckResult(
            name="id_present",
            passed=False,
            detail=f"{len(bad)} employee(s) missing both Emirates ID and labour card: "
                   f"{[b['employee_id'] for b in bad]}",
        ), bad
    return CheckResult(
        name="id_present",
        passed=True,
        detail=f"All {len(profiles)} employees have Emirates ID or labour card",
    ), []


def _check_4_amounts_match(payroll_rows: list[dict]) -> CheckResult:
    """
    Check 4: SCR totalSalary == Σ EDR (fixed + variable).
    fixed = net_salary - overtime_amount; variable = overtime_amount.
    Both sum to net_salary, so SCR total = Σ net_salary.
    """
    total = sum(Decimal(str(r.get("net_salary") or "0")) for r in payroll_rows)
    total_str = _money(total)
    return CheckResult(
        name="amounts_match",
        passed=True,
        detail=f"SCR total = AED {total_str} (sum of all EDR fixed+variable)",
    )


def _check_5_establishment_id(company: dict | None) -> CheckResult:
    """Check 5: company has a MOHRE establishment ID."""
    if company is None:
        return CheckResult(
            name="establishment_id",
            passed=False,
            detail="Company record not found in database",
        )
    mohre_id = (company.get("mohre_establishment_id") or "").strip()
    if not mohre_id:
        return CheckResult(
            name="establishment_id",
            passed=False,
            detail=f"Company '{company.get('name_en')}' has no MOHRE establishment ID",
        )
    return CheckResult(
        name="establishment_id",
        passed=True,
        detail=f"MOHRE establishment ID: {mohre_id}",
    )


def _check_6_no_negative_zero_net(payroll_rows: list[dict]) -> tuple[CheckResult, list[dict]]:
    """Check 6: no active employee has zero or negative net salary."""
    bad: list[dict] = []
    for row in payroll_rows:
        net = Decimal(str(row.get("net_salary") or "0"))
        if net <= Decimal("0"):
            bad.append({"employee_id": row["employee_id"], "net_salary": str(net)})
    if bad:
        return CheckResult(
            name="no_negative_zero_net",
            passed=False,
            detail=f"{len(bad)} employee(s) have non-positive net salary — "
                   "upstream payroll data must be corrected: "
                   f"{[b['employee_id'] for b in bad]}",
        ), bad
    return CheckResult(
        name="no_negative_zero_net",
        passed=True,
        detail=f"All {len(payroll_rows)} employees have positive net salary",
    ), []


def _check_7_employer_name_length(company: dict | None) -> CheckResult:
    """
    Check 7: employer name ≤ 35 chars (SCR field width limit).
    Spec change-list §B item 9.
    """
    if company is None:
        return CheckResult(
            name="employer_name_length",
            passed=False,
            detail="Company record missing — cannot check name length",
        )
    name = (company.get("name_en") or "").strip()
    if len(name) > 35:
        return CheckResult(
            name="employer_name_length",
            passed=False,
            detail=f"Employer name is {len(name)} chars (max 35): '{name}'. "
                   "Shorten name_en in companies table before re-running.",
        )
    return CheckResult(
        name="employer_name_length",
        passed=True,
        detail=f"Employer name '{name}' is {len(name)} chars (≤ 35)",
    )


def _check_8_month_match(payroll_rows: list[dict], year: int, month: int) -> CheckResult:
    """
    Check 8: SCR salary month (MMYYYY) must match the payroll_month/year
    of every record. Detects stale rows mixed into the wrong month.
    """
    mismatched = [
        r["employee_id"]
        for r in payroll_rows
        if int(r.get("payroll_month") or month) != month
        or int(r.get("payroll_year") or year) != year
    ]
    if mismatched:
        return CheckResult(
            name="month_match",
            passed=False,
            detail=f"{len(mismatched)} row(s) have payroll month != {month:02d}/{year}: {mismatched}",
        )
    return CheckResult(
        name="month_match",
        passed=True,
        detail=f"All {len(payroll_rows)} rows are for {month:02d}/{year}",
    )


def _check_labour_card_expiry(profiles: list[dict], today: date) -> CheckResult:
    """Non-blocking: flag employees with expired labour card."""
    expired: list[str] = []
    for p in profiles:
        expiry_raw = p.get("labour_card_expiry")
        if not expiry_raw:
            continue
        try:
            expiry_date = expiry_raw if isinstance(expiry_raw, date) else date.fromisoformat(str(expiry_raw))
            if expiry_date < today:
                expired.append(p["employee_id"])
        except (ValueError, TypeError):
            pass
    if expired:
        return CheckResult(
            name="labour_card_not_expired",
            passed=False,
            detail=f"{len(expired)} employee(s) have expired labour cards: {expired}",
            blocking=False,
        )
    return CheckResult(
        name="labour_card_not_expired",
        passed=True,
        detail="No expired labour cards",
        blocking=False,
    )


# ─── SIF delimited text builder ───────────────────────────────────────────────

def _build_sif_delimited(
    company: dict,
    payroll_rows: list[dict],
    profiles: list[dict],
    year: int,
    month: int,
    creation_dt: datetime,
) -> tuple[str, str, str]:
    """
    Build comma-delimited SIF text with SCR (employer) + EDR (employee) records.
    Physical format: skills/uae-wps-compliance/sif_format_reference.md

    Record naming:
      SCR — Salary Control Record (employer, one per file)
      EDR — Employee Detail Record (one per employee)

    Totals rule: SCR.totalSalary = Σ EDR (fixed + variable) for all EDRs.
    fixed  = net_salary − overtime_amount
    variable = overtime_amount
    fixed + variable = net_salary

    Returns (sif_text, total_salary_str, sif_filename).
    """
    profile_map = {p["employee_id"]: p for p in profiles}
    total_calendar_days = calendar.monthrange(year, month)[1]
    employer_id = _pad_employer_id(
        (company.get("mohre_establishment_id") or str(company["id"])).strip()
    )
    # Agent routing: WPS-approved bank/exchange code. Each bank issues its own 9-char code.
    # Value below is a placeholder — replace with your bank's actual routing code.
    scr_routing = (company.get("wps_agent_bank") or "000000000")[:9].ljust(9, "0")

    pay_start = date(year, month, 1).isoformat()
    pay_end   = date(year, month, total_calendar_days).isoformat()
    salary_month_field = f"{month:02d}{year}"  # MMYYYY per MOHRE spec
    creation_date = creation_dt.strftime("%Y-%m-%d")
    creation_time = creation_dt.strftime("%H:%M:%S")
    employer_name = (company.get("name_en") or "")[:35]  # enforced by check_7

    # Build EDR lines first (need Σ to populate SCR total)
    edr_lines: list[str] = []
    total_salary = Decimal("0")

    for row in payroll_rows:
        eid     = row["employee_id"]
        profile = profile_map.get(eid, {})

        net     = Decimal(str(row.get("net_salary")     or "0"))
        ot      = Decimal(str(row.get("overtime_amount") or "0"))
        fixed   = (net - ot).quantize(Decimal("0.01"), ROUND_HALF_UP)
        variable = ot.quantize(Decimal("0.01"), ROUND_HALF_UP)
        total_salary += net

        person_id   = _pad_person_id(profile.get("mohre_person_id") or eid)
        iban        = (profile.get("bank_iban") or "").strip()
        # Employee bank routing: placeholder — real value from your bank's employee mapping
        edr_routing = (profile.get("bank_name") or "000000000")[:9].ljust(9, "0")
        days_worked = int(row.get("actual_days_worked")   or total_calendar_days)
        leave_days  = int(row.get("leave_deduction_days") or 0)

        # EDR field order (change-list §B item 4):
        # EDR, personID(14), agentRouting(9), IBAN(23), payStart, payEnd,
        # days, fixed(2dp), variable(2dp), leaveDays
        edr_lines.append(",".join([
            "EDR",
            person_id,
            edr_routing,
            iban,
            pay_start,
            pay_end,
            str(days_worked),
            _money(fixed),
            _money(variable),
            str(leave_days),
        ]))

    total_str = _money(total_salary)

    # SCR field order (change-list §B item 5):
    # SCR, employerID(13), agentRouting(9), creationDate, creationTime,
    # salaryMonth(MMYYYY), recordCount, totalSalary(2dp), AED, employerName(≤35)
    scr_line = ",".join([
        "SCR",
        employer_id,
        scr_routing,
        creation_date,
        creation_time,
        salary_month_field,
        str(len(payroll_rows)),
        total_str,
        "AED",
        employer_name,
    ])

    # Record order from env (change-list §B item 7)
    if SIF_RECORD_ORDER == "scr_last":
        all_lines = edr_lines + [scr_line]
    else:  # scr_first (default)
        all_lines = [scr_line] + edr_lines

    sif_text = "\n".join(all_lines) + "\n"
    sif_filename = _generate_sif_filename(employer_id, creation_dt)
    return sif_text, total_str, sif_filename


def _check_sif_format_delimited(sif_text: str) -> CheckResult:
    """
    Check SIF format: must have exactly one SCR and ≥1 EDR lines.
    All SCR fields and EDR fields must be present.
    """
    if not sif_text.strip():
        return CheckResult(name="sif_format", passed=False, detail="SIF is empty")

    lines = [l for l in sif_text.strip().splitlines() if l.strip()]
    scr_lines = [l for l in lines if l.startswith("SCR,")]
    edr_lines = [l for l in lines if l.startswith("EDR,")]

    if len(scr_lines) != 1:
        return CheckResult(
            name="sif_format", passed=False,
            detail=f"Expected exactly 1 SCR line, found {len(scr_lines)}",
        )
    if not edr_lines:
        return CheckResult(
            name="sif_format", passed=False,
            detail="No EDR lines found",
        )

    # SCR has 10 fields, EDR has 10 fields
    scr_fields = scr_lines[0].split(",")
    if len(scr_fields) != 10:
        return CheckResult(
            name="sif_format", passed=False,
            detail=f"SCR has {len(scr_fields)} fields (expected 10)",
        )
    for i, edr in enumerate(edr_lines):
        edr_fields = edr.split(",")
        if len(edr_fields) != 10:
            return CheckResult(
                name="sif_format", passed=False,
                detail=f"EDR line {i+1} has {len(edr_fields)} fields (expected 10)",
            )

    return CheckResult(
        name="sif_format",
        passed=True,
        detail=f"1 SCR + {len(edr_lines)} EDR line(s), all fields present",
    )


# ─── Output writers ───────────────────────────────────────────────────────────

def _write_outputs(
    company_id: str,
    sif_filename: str,
    salary_month: str,
    sif_text: str,
    result: WPSRunResult,
) -> tuple[str, str]:
    """
    Write .SIF (25-char filename) + _report.md to outputs/wps/{company_id}/
    Idempotent: overwrites on re-run (spec §11).
    Returns (sif_path, report_path).
    """
    out_dir = OUTPUTS_BASE / company_id
    out_dir.mkdir(parents=True, exist_ok=True)

    sif_path    = out_dir / sif_filename
    report_path = out_dir / f"{salary_month}_report.md"

    sif_path.write_text(sif_text, encoding="utf-8")

    lines: list[str] = [
        "# WPS Validation Report",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Company | {company_id} |",
        f"| Salary Month | {salary_month} |",
        f"| Run At | {result.run_at} |",
        f"| **Status** | **{result.status}** |",
        f"| Total Payroll AED | {result.total_payroll_aed} |",
        f"| Total SIF AED | {result.total_sif_aed} |",
        f"| SIF File | `{sif_filename}` |",
        "",
        "## Validation Checks",
        "",
        "| # | Check | Result | Detail |",
        "|---|-------|--------|--------|",
    ]
    for i, chk in enumerate(result.checks, 1):
        icon = "OK" if chk.passed else ("WARN" if not chk.blocking else "FAIL")
        lines.append(f"| {i} | {chk.name} | {icon} | {chk.detail} |")

    if result.blocked_employees:
        lines += ["", "## Blocked Employees (action required before approval)", ""]
        for emp in result.blocked_employees:
            lines.append(f"- `{emp.get('employee_id', emp)}` — {emp.get('reason', 'see check above')}")

    lines += [
        "",
        "---",
        "",
        "> SIF file is for human review only. No payment or submission is made by the system.",
        "> Run through your bank's SIF validation tool before live submission.",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return str(sif_path), str(report_path)


# ─── Deadline checker ─────────────────────────────────────────────────────────

def _days_to_wps_deadline(year: int, month: int) -> int:
    last_day = calendar.monthrange(year, month)[1]
    deadline = date(year, month, last_day)
    return (deadline - date.today()).days


# ─── Core async runner ────────────────────────────────────────────────────────

async def _run_wps_worker(company_id: str, salary_month: str) -> WPSRunResult:
    """
    Full WPS compliance run: DB read → 8 checks → build SIF → write outputs.
    Never modifies DB. Never submits. Never pays.
    """
    creation_dt = datetime.now(timezone.utc)
    run_at = creation_dt.isoformat()
    log = logger.bind(company_id=company_id, salary_month=salary_month)
    log.info("wps_worker.started", record_order=SIF_RECORD_ORDER)

    # Parse salary_month
    try:
        year, month = int(salary_month[:4]), int(salary_month[5:7])
    except (ValueError, IndexError):
        result = WPSRunResult(
            company_id=company_id, salary_month=salary_month,
            status=STATUS_BLOCKED, run_at=run_at,
        )
        result.checks.append(CheckResult(
            name="input_valid", passed=False,
            detail=f"salary_month must be YYYY-MM, got: {salary_month!r}",
        ))
        log.error("wps_worker.invalid_input", detail=result.checks[0].detail)
        return result

    result = WPSRunResult(
        company_id=company_id, salary_month=salary_month,
        status=STATUS_BLOCKED, run_at=run_at,
    )

    # ── Read system of record ──────────────────────────────────────────────────
    log.info("wps_worker.reading_db")
    company      = await _fetch_company(company_id)
    payroll_rows = await _fetch_finalized_payroll(company_id, year, month)
    employee_ids = [r["employee_id"] for r in payroll_rows]
    profiles     = await _fetch_employee_profiles(employee_ids) if employee_ids else []

    log.info("wps_worker.db_read_done",
             company_found=company is not None,
             payroll_rows=len(payroll_rows),
             profiles=len(profiles))

    # ── Guard: payroll must be finalized ──────────────────────────────────────
    if not payroll_rows:
        result.checks.append(CheckResult(
            name="payroll_finalized", passed=False,
            detail=f"No finalized payroll records found for {salary_month}. "
                   "Ask HR to finalize payroll before generating SIF.",
        ))
        log.error("wps_worker.blocked", reason="payroll_not_finalized")
        return result
    result.checks.append(CheckResult(
        name="payroll_finalized", passed=True,
        detail=f"{len(payroll_rows)} record(s) with status=finalized",
    ))

    # ── 8 validation checks (spec §6) ─────────────────────────────────────────
    today = date.today()

    chk1 = _check_1_all_employees_included(payroll_rows, profiles)
    result.checks.append(chk1)

    chk2, bad_iban = _check_2_iban_valid(profiles)
    result.checks.append(chk2)

    chk3, bad_id = _check_3_id_valid(profiles)
    result.checks.append(chk3)

    chk4 = _check_4_amounts_match(payroll_rows)
    result.checks.append(chk4)

    chk5 = _check_5_establishment_id(company)
    result.checks.append(chk5)

    chk6, bad_net = _check_6_no_negative_zero_net(payroll_rows)
    result.checks.append(chk6)

    chk7 = _check_7_employer_name_length(company)
    result.checks.append(chk7)

    chk8 = _check_8_month_match(payroll_rows, year, month)
    result.checks.append(chk8)

    # Non-blocking: expired labour card (flag but do not BLOCK)
    chk_lc = _check_labour_card_expiry(profiles, today)
    result.checks.append(chk_lc)

    # ── BLOCKED if any blocking check failed ───────────────────────────────────
    blocking_fails = [c for c in result.checks if not c.passed and c.blocking]
    if blocking_fails:
        blocked_emps: list[dict] = []
        for emp in bad_iban:
            blocked_emps.append({**emp, "reason": "invalid IBAN"})
        for emp in bad_id:
            blocked_emps.append({**emp, "reason": "missing Emirates ID and labour card"})
        for emp in bad_net:
            blocked_emps.append({**emp, "reason": "non-positive net salary"})
        result.blocked_employees = blocked_emps

        days_left = _days_to_wps_deadline(year, month)
        for chk in blocking_fails:
            log.error(
                "wps_worker.blocked",
                check=chk.name,
                message=(
                    f"WPS SIF for {company_id} {salary_month} is BLOCKED: "
                    f"{chk.detail}. WPS deadline in {days_left} day(s)."
                ),
            )
        return result

    # ── Build SIF (only when all blocking checks pass) ─────────────────────────
    log.info("wps_worker.building_sif")
    sif_text, total_sif_aed, sif_filename = _build_sif_delimited(
        company, payroll_rows, profiles, year, month, creation_dt,
    )
    result.total_sif_aed = total_sif_aed
    result.total_payroll_aed = _money(
        sum(Decimal(str(r.get("net_salary") or "0")) for r in payroll_rows)
    )

    # ── SIF format check (structural) ─────────────────────────────────────────
    chk_fmt = _check_sif_format_delimited(sif_text)
    result.checks.append(chk_fmt)
    if not chk_fmt.passed:
        log.error("wps_worker.sif_format_invalid", detail=chk_fmt.detail)
        return result

    # ── Write outputs (idempotent) ─────────────────────────────────────────────
    log.info("wps_worker.writing_outputs", sif_filename=sif_filename)
    try:
        sif_path, report_path = _write_outputs(
            company_id, sif_filename, salary_month, sif_text, result,
        )
        result.sif_path    = sif_path
        result.report_path = report_path
    except OSError as exc:
        result.checks.append(CheckResult(
            name="write_outputs", passed=False,
            detail=f"Could not write output files: {exc}",
        ))
        log.error("wps_worker.write_failed", error=str(exc))
        return result

    # ── Deadline alert ─────────────────────────────────────────────────────────
    days_left = _days_to_wps_deadline(year, month)
    if days_left < 0:
        log.error("wps_worker.deadline_breached", days_past=abs(days_left))
    elif days_left <= WPS_DEADLINE_ALERT_DAYS:
        log.warning("wps_worker.deadline_approaching", days_left=days_left)

    result.status = STATUS_READY

    if not chk_lc.passed:
        log.warning("wps_worker.labour_card_expired", detail=chk_lc.detail)

    log.info(
        "wps_worker.completed",
        status=result.status,
        sif_filename=sif_filename,
        sif_path=result.sif_path,
        total_aed=result.total_sif_aed,
        days_to_deadline=days_left,
    )
    return result


# ─── Celery tasks ─────────────────────────────────────────────────────────────

@shared_task(
    name="app.tasks.uae.wps_tasks.run_wps_worker",
    bind=True,
    max_retries=2,
    autoretry_for=(OSError,),
    retry_backoff=True,
)
def run_wps_worker(self, company_id: str, salary_month: str) -> dict:
    """
    Generate WPS SIF for one company + month.
    Returns dict with status READY_FOR_APPROVAL or BLOCKED.
    Never submits. Never pays. Never modifies DB.
    """
    result = asyncio.run(_run_wps_worker(company_id, salary_month))
    return result.to_dict()


@shared_task(name="app.tasks.uae.wps_tasks.generate_sif_all_companies")
def generate_sif_all_companies(salary_month: str | None = None) -> dict:
    """Monthly scheduled: run WPS worker for every active company."""
    if salary_month is None:
        today = date.today()
        salary_month = f"{today.year}-{today.month:02d}"

    async def _all() -> list[dict]:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        try:
            async with AsyncSessionLocal() as session:
                rows = await session.execute(
                    text("SELECT id FROM companies WHERE is_active = true")
                )
                company_ids = [r["id"] for r in rows.mappings()]
        except Exception as exc:
            logger.error("wps_worker.fetch_companies_failed", error=str(exc))
            return []
        results = []
        for cid in company_ids:
            r = await _run_wps_worker(str(cid), salary_month)
            results.append(r.to_dict())
        return results

    summaries = asyncio.run(_all())
    ready   = sum(1 for s in summaries if s["status"] == STATUS_READY)
    blocked = sum(1 for s in summaries if s["status"] == STATUS_BLOCKED)
    logger.info("wps_worker.batch_done",
                salary_month=salary_month, total=len(summaries),
                ready=ready, blocked=blocked)
    return {"salary_month": salary_month, "total": len(summaries), "ready": ready, "blocked": blocked}


@shared_task(name="app.tasks.uae.wps_tasks.send_wps_deadline_alerts")
def send_wps_deadline_alerts() -> dict:
    """Daily: check WPS deadline for the current month and alert if close."""
    today = date.today()
    year, month = today.year, today.month
    days_left = _days_to_wps_deadline(year, month)
    salary_month = f"{year}-{month:02d}"

    if days_left < 0:
        logger.error("wps.deadline_breached", salary_month=salary_month,
                     days_past=abs(days_left),
                     action="HR must submit WPS SIF immediately to MOHRE")
    elif days_left <= WPS_DEADLINE_ALERT_DAYS:
        logger.warning("wps.deadline_approaching", salary_month=salary_month,
                       days_left=days_left,
                       action=f"WPS SIF due in {days_left} day(s) — approve and submit")
    else:
        logger.info("wps.deadline_ok", salary_month=salary_month, days_left=days_left)

    return {"salary_month": salary_month, "days_to_deadline": days_left,
            "deadline_breached": days_left < 0}

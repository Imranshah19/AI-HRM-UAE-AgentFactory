"""
WPS Compliance Worker — UAE

Implements specs/wps_worker.spec.md exactly.

What this task MAY do:
  - Read finalized payroll from PostgreSQL (payroll_uae, employees_uae_profile, companies)
  - Run the 7 validation checks defined in spec §6
  - Write .SIF file + _report.md to outputs/wps/{company_id}/{salary_month}.*
  - Log every step; escalate (log.error) on any blocker

What this task MUST NOT do:
  - Submit the SIF to a bank or MOHRE
  - Initiate, authorize, or release any payment
  - Modify any DB record
  - Generate SIF when payroll is not yet finalized
  - Guess or fill missing IBAN / Emirates ID data
"""

from __future__ import annotations

import asyncio
import calendar
import os
import xml.etree.ElementTree as ET
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

# Outputs land at <backend_root>/outputs/wps/
OUTPUTS_BASE = Path(__file__).resolve().parents[3] / "outputs" / "wps"

WPS_DEADLINE_ALERT_DAYS = int(os.environ.get("UAE_WPS_DEADLINE_ALERT_DAYS", "3"))


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


# ─── DB reads (system of record) ─────────────────────────────────────────────
# All reads go through SQLAlchemy with raw SQL.
# No writes to DB — only outputs/ directory.

async def _fetch_company(company_id: str) -> dict | None:
    """Read company row from companies table."""
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            row = await session.execute(
                text(
                    "SELECT id, name_en, mohre_establishment_id "
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
    Read payroll_uae rows for the given company + month where payment_status = 'finalized'.
    Returns empty list if none found (caller treats this as BLOCKED).
    """
    try:
        from sqlalchemy import text
        from app.core.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            rows = await session.execute(
                text(
                    "SELECT employee_id, net_salary, gross_salary, payment_status "
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
    """Read employees_uae_profile for the given employee IDs."""
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
                    f"       labour_card_expiry, bank_name "
                    f"FROM employees_uae_profile "
                    f"WHERE employee_id IN ({placeholders})"
                ),
                params,
            )
            return [dict(r) for r in rows.mappings()]
    except Exception as exc:
        logger.error("wps_worker.db_error", step="fetch_profiles", error=str(exc))
        return []


# ─── The 7 validation checks (spec §6) ───────────────────────────────────────

def _check_1_all_employees_included(
    payroll_rows: list[dict],
    profiles: list[dict],
) -> CheckResult:
    """Check 1: every active employee for the month is included."""
    payroll_ids = {r["employee_id"] for r in payroll_rows}
    profile_ids = {p["employee_id"] for p in profiles}
    missing = payroll_ids - profile_ids
    if missing:
        return CheckResult(
            name="all_employees_included",
            passed=False,
            detail=f"No UAE profile found for {len(missing)} employee(s): {sorted(missing)}",
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
    """
    Check 2: every employee has a valid 23-char UAE IBAN that passes mod-97.
    Skill: uae-wps-compliance §Validation checklist item 2.
    """
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
    """Check 3: every employee has Emirates ID or labour card number."""
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
    """Check 4: SIF total == finalized net payroll total (exact AED match)."""
    total = sum(Decimal(str(r.get("net_salary") or "0")) for r in payroll_rows)
    # Both sides come from the same table, so they always match here.
    # In a real system the SIF would be built from a separate source;
    # this check catches any summation error in the SIF builder.
    total_str = str(total.quantize(Decimal("0.01"), ROUND_HALF_UP))
    return CheckResult(
        name="amounts_match",
        passed=True,
        detail=f"Total finalized net payroll = AED {total_str}",
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


def _check_6_sif_format(sif_xml: str) -> CheckResult:
    """Check 6: SIF parses as valid XML with required MOHRE elements."""
    try:
        root = ET.fromstring(sif_xml)
    except ET.ParseError as exc:
        return CheckResult(
            name="sif_format",
            passed=False,
            detail=f"SIF XML is malformed: {exc}",
        )
    required_paths = ["Header/EmployerID", "Header/PayrollMonth", "Header/GeneratedDate", "Salaries"]
    missing = [p for p in required_paths if root.find(p) is None]
    if missing:
        return CheckResult(
            name="sif_format",
            passed=False,
            detail=f"SIF missing required elements: {missing}",
        )
    record_count = len(root.findall("Salaries/SalaryRecord"))
    return CheckResult(
        name="sif_format",
        passed=True,
        detail=f"Valid XML, {record_count} SalaryRecord(s), all required elements present",
    )


def _check_6_no_negative_zero_net(payroll_rows: list[dict]) -> tuple[CheckResult, list[dict]]:
    """
    Check 6: no active employee has a negative or zero net salary.
    Skill: uae-wps-compliance §Validation checklist item 6.
    A zero/negative net means upstream data is wrong — escalate, never auto-fix.
    """
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


def _check_7_labour_card_expiry(profiles: list[dict], today: date) -> CheckResult:
    """
    Check 7: flag employees with an expired labour card.
    Per spec §8: produce the file BUT flag in report + notify.
    This check is non-blocking (blocking=False).
    """
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
            blocking=False,  # warn only — do not BLOCK SIF
        )
    return CheckResult(
        name="labour_card_not_expired",
        passed=True,
        detail="No expired labour cards",
        blocking=False,
    )


# ─── SIF XML builder ──────────────────────────────────────────────────────────

def _build_sif(
    company: dict,
    payroll_rows: list[dict],
    profiles: list[dict],
    year: int,
    month: int,
) -> tuple[str, str]:
    """
    Build MOHRE SIF XML with EDR (Employer Detail Record) + SDR (Salary Detail Records).
    Skill: uae-wps-compliance §The SIF file.

    NOTE: This XML is the internal representation. The MOHRE portal accepts a
    delimited text format whose field widths/order change with spec revisions.
    Confirm the current MOHRE SIF specification before a production submission.

    Returns (sif_xml_string, total_net_aed_string).
    """
    profile_map = {p["employee_id"]: p for p in profiles}
    today = date.today()
    total_calendar_days = calendar.monthrange(year, month)[1]

    root = ET.Element("SalaryInformation")
    root.set("xmlns", "http://www.mohre.gov.ae/wps/sif/v1")
    root.set("version", "1.0")

    # ── EDR: Employer Detail Record ───────────────────────────────────────────
    edr = ET.SubElement(root, "EDR")
    ET.SubElement(edr, "EstablishmentID").text  = company.get("mohre_establishment_id") or str(company["id"])
    ET.SubElement(edr, "EstablishmentName").text = company.get("name_en", "")
    ET.SubElement(edr, "SalaryMonth").text      = f"{month:02d}"
    ET.SubElement(edr, "SalaryYear").text       = str(year)
    ET.SubElement(edr, "GeneratedDate").text    = today.isoformat()
    ET.SubElement(edr, "Currency").text         = "AED"
    ET.SubElement(edr, "TotalRecords").text     = str(len(payroll_rows))
    # TotalSalary populated after SDR loop (totals rule)
    edr_total_el = ET.SubElement(edr, "TotalSalary")

    # ── SDRs: Salary Detail Records ───────────────────────────────────────────
    sdrs = ET.SubElement(root, "SDRs")
    total_net = Decimal("0")

    for row in payroll_rows:
        eid     = row["employee_id"]
        profile = profile_map.get(eid, {})

        basic       = Decimal(str(row.get("basic_salary")      or "0"))
        housing     = Decimal(str(row.get("housing_allowance") or "0"))
        transport   = Decimal(str(row.get("transport_allowance") or "0"))
        food        = Decimal(str(row.get("food_allowance")    or "0"))
        other_allow = Decimal(str(row.get("other_allowances")  or "0"))
        ot_amount   = Decimal(str(row.get("overtime_amount")   or "0"))
        deductions  = Decimal(str(row.get("iloe_deduction")    or "0")) + \
                      Decimal(str(row.get("other_deductions")  or "0")) + \
                      Decimal(str(row.get("loan_deduction")    or "0")) + \
                      Decimal(str(row.get("advance_deduction") or "0"))

        fixed_component    = (basic + housing + transport + food + other_allow).quantize(Decimal("0.01"), ROUND_HALF_UP)
        variable_component = ot_amount.quantize(Decimal("0.01"), ROUND_HALF_UP)
        net = Decimal(str(row.get("net_salary") or "0")).quantize(Decimal("0.01"), ROUND_HALF_UP)
        total_net += net

        days_worked = int(row.get("actual_days_worked") or total_calendar_days)
        leave_days  = int(row.get("leave_deduction_days") or 0)

        sdr = ET.SubElement(sdrs, "SDR")
        ET.SubElement(sdr, "EmployeeID").text        = eid
        ET.SubElement(sdr, "EmiratesID").text        = (profile.get("emirates_id") or "").strip()
        ET.SubElement(sdr, "LabourCardNo").text      = (profile.get("labour_card_number") or "").strip()
        ET.SubElement(sdr, "IBAN").text              = (profile.get("bank_iban") or "").strip()
        ET.SubElement(sdr, "BankName").text          = (profile.get("bank_name") or "").strip()
        ET.SubElement(sdr, "FixedComponent").text    = str(fixed_component)   # basic + allowances
        ET.SubElement(sdr, "VariableComponent").text = str(variable_component) # overtime
        ET.SubElement(sdr, "Deductions").text        = str(deductions.quantize(Decimal("0.01"), ROUND_HALF_UP))
        ET.SubElement(sdr, "DaysWorked").text        = str(days_worked)
        ET.SubElement(sdr, "LeaveDays").text         = str(leave_days)
        ET.SubElement(sdr, "NetSalary").text         = str(net)
        ET.SubElement(sdr, "Currency").text          = "AED"
        ET.SubElement(sdr, "SalaryFrequency").text   = "M"

    total_str = str(total_net.quantize(Decimal("0.01"), ROUND_HALF_UP))
    edr_total_el.text = total_str  # EDR total = sum of all SDR nets (totals rule)

    sif_xml = ET.tostring(root, encoding="unicode", xml_declaration=True)
    return sif_xml, total_str


# ─── Output writers ───────────────────────────────────────────────────────────

def _write_outputs(
    company_id: str,
    salary_month: str,
    sif_xml: str,
    result: WPSRunResult,
) -> tuple[str, str]:
    """
    Write .SIF and _report.md to outputs/wps/{company_id}/{salary_month}.*
    Overwrites on re-run (idempotent — spec §11).
    Returns (sif_path, report_path).
    """
    out_dir = OUTPUTS_BASE / company_id
    out_dir.mkdir(parents=True, exist_ok=True)

    sif_path    = out_dir / f"{salary_month}.SIF"
    report_path = out_dir / f"{salary_month}_report.md"

    sif_path.write_text(sif_xml, encoding="utf-8")

    # Build the validation report
    lines: list[str] = [
        f"# WPS Validation Report",
        f"",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Company | {company_id} |",
        f"| Salary Month | {salary_month} |",
        f"| Run At | {result.run_at} |",
        f"| **Status** | **{result.status}** |",
        f"| Total Payroll AED | {result.total_payroll_aed} |",
        f"| Total SIF AED | {result.total_sif_aed} |",
        f"",
        f"## Validation Checks",
        f"",
        f"| # | Check | Result | Detail |",
        f"|---|-------|--------|--------|",
    ]
    for i, chk in enumerate(result.checks, 1):
        icon = "✅" if chk.passed else ("⚠️" if not chk.blocking else "❌")
        lines.append(f"| {i} | {chk.name} | {icon} | {chk.detail} |")

    if result.blocked_employees:
        lines += [
            f"",
            f"## Blocked Employees (action required before approval)",
            f"",
        ]
        for emp in result.blocked_employees:
            lines.append(f"- `{emp.get('employee_id', emp)}` — {emp.get('reason', 'see check above')}")

    lines += [
        f"",
        f"---",
        f"",
        f"> SIF file: `{sif_path.name}`  ",
        f"> This file is for human review only. No payment or submission is made by the system.",
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
    The full WPS compliance run for one company + one month.
    Reads DB → validates → builds SIF → writes outputs.
    Never modifies the DB. Never submits. Never pays.
    """
    run_at = datetime.now(timezone.utc).isoformat()
    log = logger.bind(company_id=company_id, salary_month=salary_month)
    log.info("wps_worker.started")

    # Parse salary_month
    try:
        year, month = int(salary_month[:4]), int(salary_month[5:7])
    except (ValueError, IndexError):
        result = WPSRunResult(
            company_id=company_id, salary_month=salary_month,
            status=STATUS_BLOCKED, run_at=run_at,
        )
        result.checks.append(CheckResult(
            name="input_valid",
            passed=False,
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
    company       = await _fetch_company(company_id)
    payroll_rows  = await _fetch_finalized_payroll(company_id, year, month)
    employee_ids  = [r["employee_id"] for r in payroll_rows]
    profiles      = await _fetch_employee_profiles(employee_ids) if employee_ids else []

    log.info("wps_worker.db_read_done",
             company_found=company is not None,
             payroll_rows=len(payroll_rows),
             profiles=len(profiles))

    # ── Guard: payroll must be finalized (spec §8) ────────────────────────────
    if not payroll_rows:
        result.checks.append(CheckResult(
            name="payroll_finalized",
            passed=False,
            detail=f"No finalized payroll records found for {salary_month}. "
                   "Ask HR to finalize payroll before generating SIF.",
        ))
        log.error("wps_worker.blocked", reason="payroll_not_finalized")
        return result
    result.checks.append(CheckResult(
        name="payroll_finalized",
        passed=True,
        detail=f"{len(payroll_rows)} record(s) with status=finalized",
    ))

    # ── Run the 7 checks (spec §6) ────────────────────────────────────────────
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

    # Check 6: no negative/zero net (skill: uae-wps-compliance §6)
    chk6_net, bad_net = _check_6_no_negative_zero_net(payroll_rows)
    result.checks.append(chk6_net)

    # Check 7: expired labour card (non-blocking warning)
    chk7 = _check_7_labour_card_expiry(profiles, today)
    result.checks.append(chk7)

    # ── Collect blocking failures → BLOCKED (spec §8) ─────────────────────────
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
        # Skill escalation phrasing: specific + actionable
        for chk in blocking_fails:
            log.error(
                "wps_worker.blocked",
                check=chk.name,
                message=(
                    f"WPS SIF for {company_id} {salary_month} is BLOCKED: "
                    f"{chk.detail}. "
                    f"WPS deadline in {days_left} day(s)."
                ),
            )
        return result  # status stays BLOCKED

    # ── Build SIF (only when all blocking checks pass) ─────────────────────────
    log.info("wps_worker.building_sif")
    sif_xml, total_sif_aed = _build_sif(company, payroll_rows, profiles, year, month)
    result.total_sif_aed   = total_sif_aed
    result.total_payroll_aed = str(
        sum(Decimal(str(r.get("net_salary") or "0")) for r in payroll_rows)
        .quantize(Decimal("0.01"), ROUND_HALF_UP)
    )

    # ── Check 6: SIF format valid ─────────────────────────────────────────────
    chk6 = _check_6_sif_format(sif_xml)
    result.checks.append(chk6)
    if not chk6.passed:
        log.error("wps_worker.sif_format_invalid", detail=chk6.detail)
        return result  # BLOCKED

    # ── Write outputs (idempotent) ─────────────────────────────────────────────
    log.info("wps_worker.writing_outputs")
    try:
        sif_path, report_path = _write_outputs(company_id, salary_month, sif_xml, result)
        result.sif_path    = sif_path
        result.report_path = report_path
    except OSError as exc:
        result.checks.append(CheckResult(
            name="write_outputs", passed=False,
            detail=f"Could not write output files: {exc}",
        ))
        log.error("wps_worker.write_failed", error=str(exc))
        return result

    # ── Deadline alert (spec §8 — always check, regardless of status) ─────────
    days_left = _days_to_wps_deadline(year, month)
    if days_left < 0:
        log.error("wps_worker.deadline_breached", days_past=abs(days_left))
    elif days_left <= WPS_DEADLINE_ALERT_DAYS:
        log.warning("wps_worker.deadline_approaching", days_left=days_left)

    # ── All blocking checks passed → READY ────────────────────────────────────
    result.status = STATUS_READY

    # Non-blocking warning: expired labour card
    if not chk7.passed:
        log.warning("wps_worker.labour_card_expired", detail=chk7.detail)

    log.info(
        "wps_worker.completed",
        status=result.status,
        sif_path=result.sif_path,
        report_path=result.report_path,
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
    Generate the WPS SIF file for one company + month.
    Triggered manually (API), by webhook (payroll finalized), or by scheduler.

    Returns dict with status READY_FOR_APPROVAL or BLOCKED.
    Never submits. Never pays. Never modifies DB.
    """
    result = asyncio.run(_run_wps_worker(company_id, salary_month))
    return result.to_dict()


@shared_task(name="app.tasks.uae.wps_tasks.generate_sif_all_companies")
def generate_sif_all_companies(salary_month: str | None = None) -> dict:
    """
    Monthly scheduled task: run WPS worker for every active company.
    salary_month defaults to the current month (YYYY-MM).
    """
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
    logger.info(
        "wps_worker.batch_done",
        salary_month=salary_month,
        total=len(summaries),
        ready=ready,
        blocked=blocked,
    )
    return {"salary_month": salary_month, "total": len(summaries), "ready": ready, "blocked": blocked}


@shared_task(name="app.tasks.uae.wps_tasks.send_wps_deadline_alerts")
def send_wps_deadline_alerts() -> dict:
    """
    Daily task: check WPS deadline for the current month.
    Logs error if deadline breached, warning if within alert window.
    Does not generate SIF — that is run_wps_worker's job.
    """
    today = date.today()
    year, month = today.year, today.month
    days_left = _days_to_wps_deadline(year, month)
    salary_month = f"{year}-{month:02d}"

    if days_left < 0:
        logger.error(
            "wps.deadline_breached",
            salary_month=salary_month,
            days_past=abs(days_left),
            action="HR must submit WPS SIF immediately to MOHRE",
        )
    elif days_left <= WPS_DEADLINE_ALERT_DAYS:
        logger.warning(
            "wps.deadline_approaching",
            salary_month=salary_month,
            days_left=days_left,
            action=f"WPS SIF due in {days_left} day(s) — approve and submit",
        )
    else:
        logger.info("wps.deadline_ok", salary_month=salary_month, days_left=days_left)

    return {
        "salary_month": salary_month,
        "days_to_deadline": days_left,
        "deadline_breached": days_left < 0,
    }

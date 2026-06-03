---
name: uae-wps-compliance
description: >
  Use this skill when generating or validating a UAE Wage Protection System
  (WPS) SIF file for monthly payroll. Covers MOHRE SIF format, UAE Labour Law
  wage rules (Federal Decree-Law No. 33 of 2021), WPS deadlines and penalties,
  IBAN/Emirates ID validation, and the exact checks a SIF must pass before a
  human approves it. Trigger for any task mentioning WPS, SIF, salary file,
  MOHRE wage submission, or UAE payroll compliance.
version: 2.0
---

# UAE WPS Compliance Skill

Portable domain expertise for any worker handling UAE Wage Protection System tasks.
Physical SIF format details are in `sif_format_reference.md` (same directory).

## What WPS is

The **Wage Protection System (WPS)** is the UAE electronic salary transfer system mandated by MOHRE (Ministry of Human Resources & Emiratisation). Employers must pay registered employees through WPS-approved banks/exchanges and submit a **SIF (Salary Information File)** each month. Non-compliance triggers fines and can freeze new work-permit issuance.

## SIF file structure (v2 — corrected)

A SIF is **comma-delimited plain text** with two record types. No XML.

**SCR — Salary Control Record** (one per file, employer-level):
```
SCR, employerID(13,zero-pad), agentRouting(9), creationDate(YYYY-MM-DD),
     creationTime(HH:MM:SS), salaryMonth(MMYYYY), recordCount,
     totalSalary(2dp), AED, employerName(≤35)
```

**EDR — Employee Detail Record** (one per employee):
```
EDR, personID(14,zero-pad), agentRouting(9), IBAN(23),
     payStart(YYYY-MM-DD), payEnd(YYYY-MM-DD), daysWorked,
     fixed(2dp), variable(2dp), leaveDays
```

**Totals rule:** `SCR.totalSalary = Σ EDR(fixed + variable)` — exact, no rounding drift.

**Money format:** 2 decimal places, dot separator, no thousands comma. (`4000.00` not `4,000.00`).

**Record order:** configurable via `SIF_RECORD_ORDER` env var (`scr_first` | `scr_last`). Never hard-coded — different banks require different orderings.

**Filename:** `{employerID:0>13}{YYMMDD}{HHMMSS}.SIF` — 25 chars before extension. Date/time must match the SCR fields exactly.

See `sif_format_reference.md` for field widths and examples.

## UAE Labour Law rules the worker must respect

- Governing law: **Federal Decree-Law No. 33 of 2021** (+ 2024 amendments).
- All contracts are fixed-term (unlimited contracts abolished 2022).
- Wages must be paid within the period set by the contract; WPS submission is due within the MOHRE window after the wage due date. Late = penalty exposure.
- Salary currency is **AED**.
- Ramadan: working hours reduced by 2 hours/day (affects attendance-linked variable pay, not SIF format).

## Validation checklist (8 blocking checks + 1 warning)

Run ALL. File is BLOCKED if any blocking check fails.

| # | Check | Blocking |
|---|-------|---------|
| 1 | Employee count in SIF == active payroll count for the month | Yes |
| 2 | Each IBAN: 23 chars, `AE` prefix, passes mod-97 check | Yes |
| 3 | Each employee has Emirates ID or labour card number | Yes |
| 4 | SCR totalSalary == Σ EDR (fixed+variable), exact to the fil | Yes |
| 5 | Establishment ID present; salary month/year correct | Yes |
| 6 | No negative or zero net for any active full-month employee | Yes |
| 7 | Employer name ≤ 35 chars | Yes |
| 8 | SCR salary month (MMYYYY) matches payroll_month of every row | Yes |
| — | Expired labour card: flag in report + notify, but do not BLOCK | Warning |

After all 8 pass: structural check — exactly 1 SCR + N EDR lines, all fields present.

## Hard rules (non-negotiable)

- **Read-only** on employee/payroll data. The SIF is an output, never an edit.
- **Never submit, pay, or transfer.** Produce the file; a human approves and submits.
- **Never invent data.** Missing IBAN/EID → STOP and escalate with the exact employee list.
- **Never auto-correct a total mismatch.** A mismatch means upstream data is wrong — that is a human's call.

## Escalation phrasing

Specific and actionable:
> "WPS SIF for {Company} {Month} is BLOCKED: {n} employee(s) {issue} — [{IDs}]. {Action}. WPS deadline in {N} days."

Example:
> "WPS SIF for co-001 2026-04 is BLOCKED: 2 employees missing IBAN — [emp-104, emp-119]. Add IBANs in employees_uae_profile.bank_iban and re-run. WPS deadline in 4 days."

## Quick reference

| Item | Value |
|---|---|
| Authority | MOHRE |
| File format | Comma-delimited text (.SIF) — not XML |
| Records | SCR (employer) + EDR (employee) — no SDR |
| Currency | AED, 2dp, dot separator |
| Law | Federal Decree-Law No. 33/2021 (+2024) |
| IBAN | 23 chars, `AE` prefix, mod-97 valid |
| Worker authority | Generate + validate ONLY — no submit, no pay |
| Record order | `SIF_RECORD_ORDER` env var (scr_first \| scr_last) |

> **Note:** Exact MOHRE SIF field widths and deadline windows change over time.
> Always confirm the current MOHRE SIF specification before a live submission.
> `sif_format_reference.md` is the structural guide, not the authoritative spec.

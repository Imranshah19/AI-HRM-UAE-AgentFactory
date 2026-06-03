---
name: uae-wps-compliance
description: >
  Use this skill when generating or validating a UAE Wage Protection System
  (WPS) SIF file for monthly payroll. Covers MOHRE SIF format, UAE Labour Law
  wage rules (Federal Decree-Law No. 33 of 2021), WPS deadlines and penalties,
  IBAN/Emirates ID validation, and the exact checks a SIF must pass before a
  human approves it. Trigger for any task mentioning WPS, SIF, salary file,
  MOHRE wage submission, or UAE payroll compliance.
version: 1.0
---

# UAE WPS Compliance Skill

This file is the worker's **expertise** — the HR/legal knowledge it needs to do the job well. It is portable: any worker can load it. (This is what was hard-coded inside Python before — now it lives here, reusable and updatable.)

## What WPS is

The **Wage Protection System (WPS)** is the UAE electronic salary transfer system mandated by MOHRE (Ministry of Human Resources & Emiratisation). Employers must pay registered employees through WPS-approved banks/exchanges and submit a **SIF (Salary Information File)** each month. Non-compliance triggers fines and can freeze new work-permit issuance.

## When to use this skill

- Building the monthly SIF file
- Validating a SIF before submission
- Checking WPS deadline / penalty risk
- Answering "is this payroll WPS-compliant?"

## The SIF file — what it must contain

A SIF has two logical record types:
1. **Employer Detail Record (EDR)** — establishment ID, bank/agent routing, total salaries, total records, salary month/year.
2. **Salary Detail Records (SDR)** — one per employee: labour card / Emirates ID, IBAN, fixed component, variable component, days worked, leave days, net pay.

**Totals rule:** sum of all SDR net amounts MUST equal the EDR total. Mismatch = invalid file. Never reconcile by adjusting an employee figure — escalate.

## UAE Labour Law rules the worker must respect

- Governing law: **Federal Decree-Law No. 33 of 2021** (+ 2024 amendments).
- All contracts are fixed-term (unlimited contracts abolished 2022).
- Wages must be paid within the period set by the contract; **WPS submission is due within the MOHRE window after the wage due date.** Late = penalty exposure.
- Salary currency is **AED**.
- Ramadan: working hours reduced by 2 hours/day (affects attendance-linked variable pay, not the SIF format itself).

## Validation checklist (run ALL — file is invalid if any fails)

1. Employee count in SIF == active payroll count for the month.
2. Each IBAN is a valid 23-character UAE IBAN (starts `AE`, passes mod-97 check).
3. Each employee has a valid Emirates ID / labour card number.
4. SIF grand total == finalized net payroll total, exact to the fil (no rounding drift).
5. Establishment ID and salary month/year correct.
6. No negative or zero net for an active full-month employee (flag if found).
7. No employee with an **expired labour card** silently included — flag it.

## Hard rules (non-negotiable)

- **Read-only** on employee/payroll data. The SIF is an output, never an edit.
- **Never submit, pay, or transfer.** Produce the file; a human approves and submits.
- **Never invent data.** Missing IBAN/EID → STOP and escalate with the exact employee list.
- **Never auto-correct a total mismatch.** A mismatch means upstream data is wrong — that is a human's call.

## Escalation phrasing (what to tell the human)

Be specific and actionable, e.g.:
> "WPS SIF for {Company} {Month} is BLOCKED: 2 employees missing IBAN — [E-104 Ahmed, E-119 Bilal]. Please add IBANs in the system, then re-run. WPS deadline in 4 days."

## Quick reference

| Item | Value |
|---|---|
| Authority | MOHRE |
| File | SIF (Salary Information File) |
| Currency | AED |
| Law | Federal Decree-Law No. 33/2021 (+2024) |
| IBAN | 23 chars, `AE` prefix, mod-97 valid |
| Worker authority | Generate + validate ONLY — no submit, no pay |

> **Note:** Exact MOHRE SIF field widths/format and current deadline windows change over time. Always confirm the latest MOHRE SIF specification before a production run; treat the layout above as structure, not a substitute for the current official spec.

---
name: uae-wps-compliance
description: >
  Use this skill when generating or validating a UAE Wage Protection System
  (WPS) SIF file for monthly payroll. Covers the SIF delimited-text format
  (SCR/EDR/EVP records), filename convention, UAE Labour Law wage rules
  (Federal Decree-Law No. 33 of 2021), WPS deadlines and penalties
  (Ministerial Resolution 598 of 2022), IBAN/Emirates ID validation, and the
  checks a SIF must pass before a human approves it. Trigger for any task
  mentioning WPS, SIF, salary file, MOHRE wage submission, or UAE payroll
  compliance.
version: 2.0
---

# UAE WPS Compliance Skill

This file is the worker's portable expertise. For the exact field-by-field
layout, see `sif_format_reference.md` in this same folder. **This skill points
to that reference for format details - never re-hard-code the format in Python.**

## What WPS is

The Wage Protection System (WPS) is the UAE's mandatory electronic salary
system (MOHRE + Central Bank of UAE). Each pay cycle the employer submits a
**SIF (Salary Information File)** through a WPS-authorised bank/agent.
Non-compliance leads to fines + possible freeze on new work permits.

## CRITICAL format facts (v2 correction)

- **A SIF is a comma-delimited plain TEXT file with a `.SIF` extension - NOT XML.**
- Record types are **SCR** (employer control record, 1 per file), **EDR**
  (employee detail record, 1 per employee), and optional **EVP** (variable-pay
  breakdown). There is **no "SDR"**.
- The **filename is itself validated**: `[13-digit Employer ID][YYMMDD][HHMMSS].SIF`,
  exactly 25 chars + extension; its date/time must match the SCR record.
- Full field layout + examples -> `sif_format_reference.md`.

## When to use this skill

- Building the monthly SIF file
- Validating a SIF before submission
- Checking WPS deadline / penalty risk
- Answering "is this payroll WPS-compliant?"

## The non-negotiable validation rules

1. SCR total salary == sum of (all EDR fixed + variable), exact to the fils.
2. SCR record count == number of EDR lines.
3. SCR salary month (MMYYYY) matches every EDR's pay period - else the WHOLE file rejects.
4. Each IBAN: valid 23-char UAE IBAN (`AE` prefix, mod-97 passes).
5. Each employee has a valid Emirates ID / labour-card number.
6. Currency is `AED`; employer name <= 35 chars.
7. No negative/zero net for an active full-month employee (data error -> escalate).
8. No employee with an expired labour card silently included -> flag.

> **"Looks right" is not success.** Success = these checks pass AND the output is
> validated against the bank's own SIF validation tool before any live run.

## UAE Labour Law context

- Governing law: Federal Decree-Law No. 33 of 2021 (+2024 amendments).
- All contracts fixed-term (unlimited abolished 2022).
- WPS submission due within the MOHRE window after wage due date (commonly
  cited 15 days; Ministerial Resolution 598/2022). Late = penalty exposure.
- Currency: AED. Ramadan: 2-hour daily reduction (affects attendance-linked
  variable pay, not the SIF format).

## Hard rules (non-negotiable)

- **Read-only** on employee/payroll data; the SIF is an output, never an edit.
- **Never submit, encrypt-for-transport, or pay.** Produce the validated `.SIF`;
  a human uploads via the bank/WPS portal.
- **Never invent data.** Missing IBAN/EID -> STOP and escalate with the exact
  employee list.
- **Never auto-correct a total mismatch** - that means upstream data is wrong;
  it's a human's call.
- **Never hard-code record order** (SCR-first vs SCR-last varies by bank) - keep
  it a config value; see `sif_format_reference.md` section 7.

## Escalation phrasing (specific + actionable)

> "WPS SIF for {Company} {Month} is BLOCKED: 2 employees have invalid IBAN -
> [E-104 Ahmed, E-119 Bilal]. Fix in the system, then re-run. WPS deadline in 4 days."

## Quick reference

| Item | Value |
|---|---|
| Authority | MOHRE + Central Bank of UAE |
| File | SIF - comma-delimited `.SIF` text (NOT XML) |
| Records | SCR (employer) / EDR (employee) / EVP (optional) |
| Filename | 25 chars: EmployerID(13)+YYMMDD+HHMMSS + `.SIF` |
| Currency | AED |
| IBAN | 23 chars, `AE`, mod-97 valid |
| Deadline | per MOHRE window (Min. Res. 598/2022) |
| Worker authority | Generate + validate ONLY - no submit, no pay |

> **Note:** SIF field widths, record order, and deadlines can change by bank/agent
> and over time. `sif_format_reference.md` is a reference, not a substitute for the
> current official MOHRE/bank SIF specification. Always validate via the bank's tool.

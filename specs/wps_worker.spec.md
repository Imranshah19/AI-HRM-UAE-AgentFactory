# WPS Compliance Worker — Specification

> **File:** `specs/wps_worker.spec.md`
> **Project:** AI-HRM-UAE-AgentFactory
> **Owner (Human Principal):** Syed Imran Shah
> **Version:** 1.1
> **Status:** Active

This is the **brief**, not the code. It defines *what* the worker does, *where it stops*, and *what "correct" means* — written BEFORE any agent runs. (This is the "first 10%" that was missing.)

---

## 1. Goal (Intent)

Generate the monthly **WPS SIF file** (Salary Information File) for each company in MOHRE-accepted format, validate it against UAE Labour Law, and route it for human approval before the WPS deadline — without ever submitting or paying autonomously.

## 2. Scope

**In scope (the worker MAY):**
- Read finalized payroll for the target month from the system of record
- Build the SIF file in exact MOHRE format
- Run all validation checks (see §6)
- Flag WPS deadline risk and document expiries affecting payroll
- Produce a SIF file + a validation report for human review

**Out of scope (the worker MUST NOT):**
- Submit the SIF to the bank / MOHRE
- Initiate, authorize, or release any payment
- Modify payroll figures, employee records, or contracts
- Generate SIF for a month where payroll is not yet `finalized`
- Guess or auto-fill missing IBAN / Emirates ID / salary data

## 3. Inputs

| Input | Source | Required |
|---|---|---|
| `company_id` | Trigger (scheduler / API) | Yes |
| `salary_month` (YYYY-MM) | Trigger | Yes |
| Payroll records (status = finalized) | PostgreSQL `payroll_uae` table | Yes |
| Employee bank + ID data | PostgreSQL `employees_uae_profile` table | Yes |
| Company MOHRE establishment ID | PostgreSQL `companies` table | Yes |

## 4. Outputs

| Output | Where |
|---|---|
| SIF file — comma-delimited plain text, .SIF extension (NOT XML) | `outputs/wps/{company_id}/{EmployerID13}{YYMMDD}{HHMMSS}.SIF` |
| Validation report (pass/fail per check) | `outputs/wps/{company_id}/{salary_month}_report.md` |
| Status event (`READY_FOR_APPROVAL` / `BLOCKED`) | logged + notification |

Filename convention: exactly 25 chars before the extension — 13-char zero-padded employer ID + 6-char date (YYMMDD) + 6-char time (HHMMSS). Date/time must equal the SCR record's `creationDate`/`creationTime` fields.

Physical format defined in `skills/uae-wps-compliance/sif_format_reference.md`.

## 5. System of Record

The **PostgreSQL database is the single source of truth.** The worker reads against it; it never relies on its own memory, screen state, or assumptions. If data is not in the system of record, it is treated as **missing**, not guessed. (Invariant 5)

## 6. Validation / Success Criteria

The SIF is only `READY_FOR_APPROVAL` if **all** of these pass:

1. Every active employee for the month is included (count matches payroll)
2. Every employee has a valid 23-char UAE IBAN (AE prefix + mod-97 integrity check)
3. Every employee has a valid Emirates ID / labour card number
4. SCR totalSalary == Σ EDR (fixed + variable) — exact AED match, no rounding drift
5. Establishment ID present and salary month/year correct
6. No negative or zero net salary for any active full-month employee
7. Employer name ≤ 35 chars (SCR field width limit)
8. SCR salary month (MMYYYY) matches the payroll_month/year of every row

Plus one non-blocking flag (does not block READY status):
- **Expired labour card**: produce file but flag in report + notify

After all 8 pass: SIF structure check — exactly 1 SCR + N EDR lines, all fields present.

> **"Looks right" is not success.** Verification = these 8 checks + structure check pass. (Principle 3)

## 7. Constraints & Authority Limits

- **Mode:** read-only on the system of record; write only to `outputs/`
- **Budget cap:** `MAX_BUDGET_USD` per run (from `.env`); stop if exceeded
- **Autonomy:** ends at "file ready"; a human approves before anything leaves the building
- **No payment authority** of any kind (Invariant 1 — human principal owns the outcome)

## 8. Escalation Rules (when to wake a human)

| Situation | Action |
|---|---|
| Missing IBAN / Emirates ID for any employee | STOP → status `BLOCKED` → notify HR with employee list |
| SIF total ≠ payroll total | STOP → `BLOCKED` → notify; never auto-correct |
| Payroll not finalized | STOP → ask HR to finalize first |
| Expired labour card found | Produce file BUT flag in report + notify |
| WPS deadline within `UAE_WPS_DEADLINE_ALERT_DAYS` | Notify HR urgently regardless of status |

## 9. Triggers (how it starts)

- **Scheduled:** Celery Beat, monthly on payroll-close date
- **Manual:** API trigger from HR dashboard
- **Event:** webhook when payroll status flips to `finalized`

## 10. Observability

Every run logs: inputs received, checks passed/failed, output paths, final status, and any escalation raised. A human can reconstruct exactly what the worker did. (Principle 7)

## 11. Known Failure Modes (designed-for)

- Step reliability compounding (validate → build → check) → keep steps small & each verifiable (Principle 4)
- Stale data → always re-read from system of record at run start
- Partial run / crash → run is idempotent; re-running same month overwrites cleanly, never double-submits (it can't submit at all)

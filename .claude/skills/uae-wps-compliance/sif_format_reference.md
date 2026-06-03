# UAE WPS SIF — File Format Reference

> **File:** `skills/uae-wps-compliance/sif_format_reference.md`
> **Purpose:** The single source of truth for *how* a SIF file is physically built.
> **Status:** Reference Implementation detail (the format can change by bank/MOHRE; the spec's rules don't).
> **Verify against:** your bank/agent's official SIF template + the bank's SIF validation tool before any live run.

---

## 0. The one fact that matters most

**A SIF is a plain delimited TEXT file with a `.SIF` extension — NOT XML.**
Each record is one line. Each field is **comma-separated**. No tags, no headers row, no JSON, no XML.

If the previous build emitted `<EDR>` / `<SDR>` XML, that output would be rejected by the bank regardless of how correct the numbers were.

---

## 1. Record types (correct names)

| Code | Name | Count | Holds |
|---|---|---|---|
| **SCR** | Salary Control Record | exactly 1 per file | Employer summary + totals the bank validates against |
| **EDR** | Employee Detail Record | 1 per employee | One employee's salary for the period |
| **EVP** | Employee Variable Pay (optional) | 0 or 1 per employee | Breakdown of the variable component (allowances etc.) |

> **Correction note:** earlier the project used "EDR = employer, SDR = employee". That is wrong. Correct = **SCR = employer**, **EDR = employee**. There is no "SDR".

---

## 2. EDR — Employee Detail Record (one line per employee)

Field order (comma-separated):

| # | Field | Format / Rule |
|---|---|---|
| 1 | Record type | literal `EDR` |
| 2 | Employee / Person ID | 14 digits, **zero-padded** if shorter (from labour card / MOL person ID) |
| 3 | Agent routing ID | 9-digit routing code of the **employee's** bank/exchange (CBUAE-assigned) |
| 4 | IBAN | UAE IBAN, 23 chars, `AE` prefix, mod-97 valid |
| 5 | Pay start date | `YYYY-MM-DD` |
| 6 | Pay end date | `YYYY-MM-DD` |
| 7 | Days in period | integer |
| 8 | Fixed component | decimal, 2 places, no thousands separators (e.g. `4000.00`) |
| 9 | Variable component | decimal, 2 places (e.g. `2500.00`; `0.00` if none) |
| 10 | Leave days (without pay) | integer (e.g. `0`) |

**Official example line (Dubai Islamic Bank reference):**
```
EDR,00915012345663,802420101,AE160240043520123456701,2016-01-01,2016-01-31,31,4000.00,2500.00,0
```

---

## 3. SCR — Salary Control Record (exactly one, employer summary)

| # | Field | Format / Rule |
|---|---|---|
| 1 | Record type | literal `SCR` |
| 2 | Employer ID | 13-digit MOHRE/LRA establishment ID |
| 3 | Agent routing ID | 9-digit head-office routing code of the agent (CBUAE-assigned) |
| 4 | File creation date | `YYYY-MM-DD` |
| 5 | File creation time | `HHMM` *(confirm HHMM vs HHMMSS with your bank — see §6)* |
| 6 | Salary month | `MMYYYY` (the month being paid) |
| 7 | Record count | number of EDR records in the file |
| 8 | Total salary | sum of **all** EDR (fixed + variable), 2 decimals |
| 9 | Currency | always `AED` |
| 10 | Employer name | max **35** characters |

**Official example line:**
```
SCR,0000000123456,802420101,2016-01-26,1130,012016,01,6500.00,AED,abc company
```
(Note: `4000.00 + 2500.00 = 6500.00` → SCR total matches EDR sum. This is the #1 validated rule.)

---

## 4. EVP — Employee Variable Pay (optional)

Used only if you itemize the variable component. Starts with `EVP`, mirrors employee ID + agent ID, then the allowance breakdown. If you are not itemizing allowances, **omit EVP entirely.**

**Official example line:**
```
EVP,00915012345663,802420101,500.00,200.00,300.00,0.00,400.00,1100.00,0.00
```

---

## 5. Hard validation rules (file is rejected if any fail)

1. **Totals:** SCR total salary == Σ (EDR fixed + variable), exact to the fils.
2. **Count:** SCR record count == number of EDR lines.
3. **Month match:** SCR salary month (MMYYYY) must match the pay period in every EDR's start/end dates — mismatch rejects the **entire** file.
4. **IBAN:** valid 23-char UAE IBAN, mod-97 passes.
5. **Currency:** `AED`.
6. **Employer name:** ≤ 35 chars.
7. **Numbers:** no thousands separators, dot as decimal, 2 places on money fields.

---

## 6. Filename convention (the filename is itself validated)

```
[13-digit Employer ID][YYMMDD creation date][HHMMSS creation time].SIF
```
- Total = **exactly 25 characters** + `.SIF` extension.
- Example: employer `1234567890123`, created 2026-03-01 08:30:00 →
  `1234567890123260301083000.SIF`
- The date & time embedded in the filename **must match** the SCR creation date/time fields, or the file is rejected immediately.

> ⚠️ Source ambiguity to confirm with your bank: filename uses **HHMMSS** (6 digits) but the SCR time field in the DIB example is **HHMM** (4 digits, `1130`). Confirm the exact SCR time format your agent expects so the two stay consistent.

---

## 7. Record ordering — CONFIRM with your bank

Sources disagree on order:
- Dubai Islamic Bank guide: **EDR/EVP records first, SCR last.**
- Some agents/software: **SCR first, then EDR rows.**

This is bank/agent-specific. **Do not hard-code one order blindly** — match your actual agent's template. Make the order a single config value so it can be flipped without touching logic.

---

## 8. Encryption & submission

- Some banks require the SIF **encrypted** in the standard format before upload — handled at upload, **not** by this worker.
- The worker's job ends at producing the validated plain `.SIF`. **It never submits, encrypts-for-transport, or pays.** A human uploads via the bank/WPS portal.

---

## 9. Deadline (for the alert task)

- Salaries must flow through WPS within the MOHRE window after the wage due date (commonly cited as 15 days; governed by Ministerial Resolution No. 598 of 2022).
- Late/non-submission → fines + possible freeze on new work permits. Hence the daily deadline-alert task.

---

## 10. What stays the same (already correct in the build)

- IBAN mod-97 check ✅
- BLOCKED on missing IBAN / Emirates ID — never guess ✅
- SCR total == EDR sum check ✅
- Negative/zero net → BLOCKED ✅
- Read-only on system of record, write only to `outputs/` ✅
- No submit / no pay ✅

**Only the physical writer (XML → delimited `.SIF`), the record names (SCR/EDR), and the filename generator need to change. The validation logic is sound.**

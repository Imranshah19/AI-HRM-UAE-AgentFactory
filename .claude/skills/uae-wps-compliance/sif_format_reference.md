# SIF Format Reference — UAE MOHRE WPS

> **Purpose:** structural guide for building and validating SIF files.
> **Not** the authoritative MOHRE spec — confirm current field widths with MOHRE before live submission.

---

## §1. File type

Comma-delimited plain text. UTF-8. `.SIF` extension. No XML, no JSON.

## §2. Record types

| Record | Purpose | Count per file |
|--------|---------|----------------|
| `SCR` | Salary Control Record — employer-level header/footer | Exactly 1 |
| `EDR` | Employee Detail Record — one salary transfer | 1 per employee |

There is no SDR (Salary Detail Record). Earlier versions of this codebase incorrectly used the term — the two record types are SCR and EDR.

## §3. SCR — Salary Control Record

One per file. Contains totals that must reconcile with all EDRs.

| Position | Field | Format | Notes |
|----------|-------|--------|-------|
| 0 | Record type | Literal `SCR` | |
| 1 | EmployerID | 13 chars, zero-padded left | MOHRE establishment ID |
| 2 | AgentRouting | 9 chars | WPS-approved bank/exchange routing code |
| 3 | CreationDate | `YYYY-MM-DD` | Must match filename date |
| 4 | CreationTime | `HH:MM:SS` | Must match filename time |
| 5 | SalaryMonth | `MMYYYY` | e.g. `042026` for April 2026 |
| 6 | RecordCount | Integer | Total number of EDR lines in file |
| 7 | TotalSalary | 2 decimal places, dot separator | Σ EDR(fixed+variable), exact |
| 8 | Currency | Literal `AED` | |
| 9 | EmployerName | ≤ 35 chars | Company name_en, truncated if needed |

**Example SCR line:**
```
SCR,0000000CO00001,000000000,2026-04-27,09:00:00,042026,3,33400.00,AED,Gulf Holdings Company A
```

## §4. EDR — Employee Detail Record

One line per employee. `fixed + variable` = what transfers to the employee's bank account.

| Position | Field | Format | Notes |
|----------|-------|--------|-------|
| 0 | Record type | Literal `EDR` | |
| 1 | PersonID | 14 chars, zero-padded left | MOHRE person ID (`mohre_person_id`) |
| 2 | AgentRouting | 9 chars | Employee's bank routing code |
| 3 | IBAN | 23 chars | UAE format: `AE` + 21 digits |
| 4 | PayStart | `YYYY-MM-DD` | First day of salary month |
| 5 | PayEnd | `YYYY-MM-DD` | Last day of salary month |
| 6 | DaysWorked | Integer | Actual working days in period |
| 7 | Fixed | 2 decimal places, dot separator | Net fixed pay (basic + allowances − fixed deductions) |
| 8 | Variable | 2 decimal places, dot separator | Net variable pay (overtime received) |
| 9 | LeaveDays | Integer | Leave days deducted in this period |

**Example EDR line:**
```
EDR,00000000EMP001,000000000,AE070331234567890123456,2026-04-01,2026-04-30,26,14800.00,700.00,0
```

## §5. Totals rule

```
SCR.TotalSalary = Σ (EDR.Fixed + EDR.Variable) for all EDR lines
```

- `fixed = net_salary − overtime_amount`
- `variable = overtime_amount`
- `fixed + variable = net_salary` (the bank transfer amount)

A mismatch means data error upstream. **Never auto-correct.** Escalate.

## §6. Filename convention

```
{EmployerID:0>13}{YYMMDD}{HHMMSS}.SIF
```

- Total: 25 chars before `.SIF` extension
- `EmployerID`: 13 chars, zero-padded (same as SCR position 1)
- `YYMMDD`: 2-digit year + 2-digit month + 2-digit day (from SCR CreationDate)
- `HHMMSS`: 6-digit time (from SCR CreationTime, colons removed)

**Example:** `0000000CO00001260427090000.SIF`
(Employer `0000000CO00001`, date `260427` = 27 Apr 2026, time `090000`)

The date/time in the filename **must** exactly match the SCR CreationDate + CreationTime fields.

## §7. Record order

Configurable via `SIF_RECORD_ORDER` environment variable:
- `scr_first` (default): SCR line first, then all EDR lines
- `scr_last`: all EDR lines first, then SCR line at the end

Different banks require different orderings. Never hard-code. Set per your bank's WPS technical guide.

## §8. Money formatting

- 2 decimal places
- Dot (`.`) as decimal separator
- No thousands separator (no commas, no spaces)

| Correct | Wrong |
|---------|-------|
| `4000.00` | `4,000.00` |
| `150.50` | `150.5` |
| `9999.99` | `9,999.99` |

## §9. IBAN validation

1. Must start with `AE`
2. Must be exactly 23 characters
3. Must pass mod-97 integrity check (ISO 13616):
   - Rearrange: move first 4 chars to end
   - Replace letters: A=10, B=11, ... Z=35
   - Check: `int(numeric_string) % 97 == 1`

## §10. What to do with the file after generation

1. Human reviews validation report (`{salary_month}_report.md`)
2. Human reviews SIF content
3. Human runs SIF through their **bank's own SIF validation tool**
4. Human submits to bank / MOHRE portal

The worker never reaches step 3 or 4. Its authority ends at step 1.

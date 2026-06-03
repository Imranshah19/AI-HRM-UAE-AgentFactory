---
name: uae-gratuity
description: >
  Use this skill when calculating UAE end-of-service gratuity (EOSB).
  Covers Federal Decree-Law No. 33/2021 Article 51, the 21/30-day rates,
  the 2-year salary cap, unpaid-leave service reduction, Art. 44 misconduct
  escalation, UAE national (GPSSA) flagging, and the correct output format
  for human approval before any settlement payment. Trigger for any task
  mentioning gratuity, EOSB, end-of-service, final settlement, Art. 51.
version: 1.0
---

# UAE End-of-Service Gratuity Skill

Portable expertise for any worker computing UAE gratuity.

## Governing law

**Federal Decree-Law No. 33 of 2021** (replaces Federal Law No. 8 of 1980).
The 2024 amendments did not change the Article 51 gratuity formula.

## The formula (Article 51)

```
daily_rate  = last_basic_salary / 30

years 1–5:    gratuity_days = years_of_service × 21
years > 5:    gratuity_days = (5 × 21) + ((years_of_service − 5) × 30)

gratuity = daily_rate × gratuity_days

cap: min(gratuity, 24 × last_basic_salary)     ← 2 years basic salary
```

**Currency:** AED. **Rounding:** final step only, 2 decimal places, ROUND_HALF_UP.

## What changed in 2021 (critical)

**The old-law resignation reductions (1/3, 2/3) are ABOLISHED.**

Under the old Federal Law No. 8/1980:
- Resignation < 1 yr: nil
- Resignation 1–3 yr: 1/3 of full
- Resignation 3–5 yr: 2/3 of full
- Resignation > 5 yr: full

Under **Federal Decree-Law No. 33/2021**:
- < 1 yr: nil (still applies)
- ≥ 1 yr: **full gratuity regardless of whether resigned or terminated**

Any code applying the 1/3 or 2/3 reductions for resignation is using the old law and will underpay employees.

## Unpaid leave (Article 29)

Periods of **unpaid leave** do not count toward service years.
Deduct unpaid leave calendar days from the total service days before dividing by the year length.

```python
service_days = (exit_date - join_date).days - unpaid_leave_days
service_years = service_days / 365.25   # confirm year-length method with legal
```

## Hard rules (non-negotiable)

- **Read-only** on employee/payroll data; the calculation output is never an edit.
- **Never pay.** Produce the calculation + breakdown; a human authorises the transfer.
- **Never guess missing basic_salary.** If null → BLOCK, list the field, stop.
- **Misconduct (Art. 44):** do not auto-forfeit. BLOCK and route to HR/legal.
- **UAE nationals:** covered by GPSSA (pension scheme) — do not compute MOHRE gratuity. Flag and route to HR.
- **Free-zone employees:** may have different schemes. Flag and route to zone authority.
- **No LLM in the arithmetic.** Claude may review capped/anomalous results, but the numbers come from the formula, not from Claude's output.

## Escalation cases → BLOCKED

| Situation | Action |
|-----------|--------|
| basic_salary null / zero | BLOCK — missing data, do not default |
| exit_reason = misconduct | BLOCK — Art. 44 forfeiture is a legal, not arithmetic, decision |
| is_emirati = true | BLOCK/FLAG — route to GPSSA, not MOHRE gratuity |
| free_zone_employee = true | BLOCK/FLAG — apply zone rules, not MOHRE formula |
| service years < 1 | READY with gratuity = 0.00 (valid zero, not an error) |

## Expected output fields

```json
{
  "employee_id": "...",
  "years_of_service": 6.0,
  "gratuity_days": 135.0,
  "daily_rate": "333.33",
  "gratuity_amount": "45000.00",
  "capped": false,
  "total_settlement": "45000.00",
  "currency": "AED",
  "notes": "Full entitlement — Federal Decree-Law 33/2021 Art. 51"
}
```

## Known amounts for validation

| Years | Basic | Scenario | Expected gratuity |
|-------|-------|----------|-------------------|
| 6 | 10000 | resignation | 45000.00 |
| 5 | 10000 | any | 35000.00 |
| < 1 | any | any | 0.00 (NIL) |
| 30 | 10000 | any | 240000.00 (capped) |
| 4 | 10000 | resignation OR termination | 28000.00 (same — no reduction) |

> **Legal sign-off required.** No gratuity settlement should be paid on the basis of
> this calculation alone. The output must go through HR and legal review, and the
> actual bank transfer must be authorised by the human principal.

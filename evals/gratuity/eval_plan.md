# Gratuity Worker — Eval Plan & Checklist

> **Folder:** `evals/gratuity/`
> Prove the worker reproduces KNOWN-correct gratuity figures — not "looks right".

## 1. Ground-truth advantage

Gratuity is deterministic and has published worked examples → real ground truth
exists WITHOUT a vendor sample. Use the law's own examples, not just self-output.

## 2. Test cases — `evals/gratuity/test_cases/*.json`

| case_id | input | expected | law basis |
|---|---|---|---|
| `emp_6yr_happy` | basic 10000, 6 yrs, resignation | READY, total **45000.00** | Art. 51 worked example |
| `emp_5yr_exact` | basic 10000, exactly 5 yrs | READY, total **35000.00** | Art. 51 boundary |
| `emp_under_1yr` | basic 8000, 8 months | **NIL** (not an error — valid zero) | Art. 51 §1 |
| `emp_cap_hit` | basic 10000, 30 yrs | READY, capped at **240000.00** | Art. 51 §3 |
| `emp_unpaid_leave` | basic 9000, 3 yrs + 60 unpaid days | READY, service reduced | Art. 29 |
| `emp_misconduct` | any, exit=misconduct | **BLOCKED** → human (Art. 44), not auto-forfeit | Art. 44 |
| `emp_uae_national` | UAE national | **flag** pension route (GPSSA), do not compute | GPSSA Law |
| `emp_missing_basic` | basic null | **BLOCKED**, field listed, DB untouched | invariant |
| `emp_resign_eq_terminate` | same data, resign vs terminate | **identical total** (no reduction) | Art. 51 (2021) |
| `emp_idempotency` | run twice | identical breakdown, no duplicate output | invariant |

## 3. Known code gap (as of 2026-04)

`backend/app/agents/uae/gratuity.py` lines 102–106 apply resignation reductions
(1/3 for <3yr, 2/3 for 3–5yr) from the **old Federal Law No. 8/1980**.

**Federal Decree-Law No. 33/2021 Article 51 abolished these reductions.**
Under the new law, resignation and termination produce identical gratuity.

- `emp_resign_eq_terminate` will **FAIL** against the current code until those lines are removed.
- All other cases are correct in the current code except misconduct, UAE national, and missing-basic handling (those are unimplemented guard clauses).

**Do not fix this during the eval — the eval's job is to surface the gap, not hide it.**

## 4. Coverage checklist

- [x] Happy path (known total) — `emp_6yr_happy`
- [x] Exactly 5 years boundary — `emp_5yr_exact`
- [x] Under 1 year → NIL — `emp_under_1yr`
- [x] Cap hit (2-year limit) — `emp_cap_hit`
- [x] Unpaid leave reduces service — `emp_unpaid_leave`
- [x] Misconduct → human — `emp_misconduct`
- [x] UAE national → flag — `emp_uae_national`
- [x] Missing data → BLOCKED — `emp_missing_basic`
- [x] Resign == terminate (no reduction) — `emp_resign_eq_terminate`
- [x] Idempotency — `emp_idempotency`

## 5. Open assumptions (track)

| Assumption | Default used | Confirm with | Status |
|---|---|---|---|
| Year length for service calc | 365.25 (current code) | MOHRE / legal | ⬜ confirm |
| Partial-year pro-rata method | actual days / 365.25 | MOHRE / legal | ⬜ confirm |
| Rounding: at final step only, 2 dp | final-step ROUND_HALF_UP | legal/policy | ⬜ confirm |
| Cap basis = 24 × basic (not gross) | 24 × basic | Art. 51 literal | ⬜ confirm wording |
| Unpaid leave: deduct from service days | subtract calendar days | HR/legal | ⬜ confirm |
| Misconduct (Art. 44): forfeit gratuity? | BLOCKED → human | legal | ⬜ legal sign-off |
| UAE nationals: no MOHRE gratuity | flag GPSSA, do not compute | HR/GPSSA | ⬜ confirm |
| Free-zone employees | flag, apply zone rules | zone authority | ⬜ confirm |

## 6. Definition of Done

- [ ] spec written & matches code
- [ ] SKILL.md in `.claude/skills/uae-gratuity/`
- [x] code deterministic (no LLM in the maths) — ✅ Claude only called on cap edge cases
- [ ] all §2 cases pass (including `emp_resign_eq_terminate` after code fix)
- [x] ≥1 case grounded on the law's worked example — ✅ emp_6yr_happy = Art. 51 example
- [ ] open assumptions in §5 confirmed — ⬜ PENDING legal/HR review
- [ ] ⬜ legal/HR sign-off documented in the run report before any live settlement

## 7. How to run

```bash
# Unit tests (pure functions, no DB, no async)
pytest evals/test_cases/test_gratuity_worker.py -v

# Expected failures until code fix:
# XFAIL: test_resign_no_reduction_new_law (resignation reduction still in code)
# XFAIL: test_misconduct_blocked (unimplemented guard)
# XFAIL: test_missing_basic_blocked (defaults to "0" instead of BLOCKED)
```

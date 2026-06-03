# WPS Compliance Worker — Eval Plan & Checklist

> **Folder:** `evals/wps/`
> Purpose: prove the worker produces KNOWN-correct output — not "looks right".
> Build this AFTER the worker runs, BEFORE you trust it.

## 1. Test case files — `evals/wps/test_cases/*.json`

| File | What it proves | Ground truth |
|------|---------------|--------------|
| `co001_2026-04_happy.json` | Clean data → READY, SCR total = 33400.00 | self |
| `co001_2026-04_blocked_iban.json` | Bad IBAN → BLOCKED, only that employee listed | self |
| `co001_2026-04_blocked_mismatch.json` | SCR total ≠ EDR sum → BLOCKED, never auto-corrected | self |
| `co001_2026-04_blocked_not_finalized.json` | Payroll not finalized → STOP, ask HR | self |
| `co001_2026-04_edge_deadline.json` | WPS deadline within 3 days → status READY + deadline warning | self |
| `co001_2026-04_edge_expired_lc.json` | Expired labour card → READY (not BLOCKED) + warning flag | self |
| `co001_2026-04_idempotency.json` | Run twice → identical SIF filename, same total, no duplication | self |
| `official_dib_sample.json` | ⬜ Ground against DIB's own sample SIF — **PENDING** | official_sample |

## 2. Coverage checklist

- [x] **Happy path** — `co001_2026-04_happy.json` — clean data → READY, total = 33400.00
- [x] **Missing data** — `co001_2026-04_blocked_iban.json` — emp-BAD missing IBAN → BLOCKED
- [x] **Mismatch** — `co001_2026-04_blocked_mismatch.json` — SCR total ≠ Σ EDR → BLOCKED
- [x] **Precondition unmet** — `co001_2026-04_blocked_not_finalized.json` — no finalized rows → STOP
- [x] **Edge: deadline** — `co001_2026-04_edge_deadline.json` → READY + deadline log.warning
- [x] **Edge: expired labour card** — `co001_2026-04_edge_expired_lc.json` → READY + non-blocking flag
- [x] **Idempotency** — `co001_2026-04_idempotency.json` → same filename, same content on re-run
- [ ] **Official sample** — `official_dib_sample.json` → ⬜ PENDING (requires bank SIF sample)

## 3. Ground-truth warning

The `evals/test_cases/test_wps_worker.py` suite (39 tests) proves **self-consistency**:
the worker produces the same output it was designed to produce. This is necessary but not sufficient.

For a format-bound file like SIF:
- At least one case must be grounded against the **bank's own sample file** or the
  bank's SIF validation tool accepting the output.
- Until `official_dib_sample.json` is filled and passes, mark all live runs as
  **PROVISIONAL** in the run report.
- Mark cases: `"ground_truth": "official_sample"` vs `"self"`.

## 4. Open assumptions (track, don't forget)

| Assumption | Default used | Confirm with | Status |
|---|---|---|---|
| SCR time format | `HHMM` (env: `SIF_SCR_TIME_FORMAT=HHMM`) | Your WPS bank/agent | ⬜ PENDING |
| Record order | `scr_first` (env: `SIF_RECORD_ORDER=scr_first`) | Your WPS bank/agent | ⬜ PENDING |
| Agent routing ID format | 9-digit numeric (placeholder `000000000`) | Your WPS bank/agent | ⬜ PENDING |
| WPS submission deadline | 15 days (Min. Res. 598/2022) | MOHRE / your bank | ⬜ PENDING |
| SIF encryption required | No (worker produces plain `.SIF`) | Your bank portal | ⬜ PENDING |
| `UAE_WPS_DEADLINE_ALERT_DAYS` | `3` days | HR preference | ⬜ PENDING |

## 5. Definition of Done

- [x] spec written — `specs/wps_worker.spec.md` v1.1
- [x] SKILL.md v2 in `.claude/skills/uae-wps-compliance/`
- [x] `sif_format_reference.md` in `.claude/skills/uae-wps-compliance/`
- [x] code matches spec (delimited text, SCR/EDR, no submit/pay)
- [x] `evals/test_cases/test_wps_worker.py` — 39/39 pass (self-consistency)
- [x] all test case JSON files written (§1)
- [ ] ≥1 case grounded against official bank SIF sample — ⬜ PENDING
- [ ] open assumptions in §4 confirmed and checked off — ⬜ PENDING
- [x] human validation step documented in run report (`_report.md`)

## 6. How to run

```bash
# Unit + integration evals (pure functions, no DB)
pytest evals/test_cases/test_wps_worker.py -v

# Run the worker against a live DB (Docker must be up)
from app.tasks.uae.wps_tasks import run_wps_worker
run_wps_worker.delay("co-001", "2026-04")
# Check: outputs/wps/co-001/{filename}.SIF
#        outputs/wps/co-001/2026-04_report.md

# Bank validation (human step — not automated)
# Upload outputs/wps/co-001/{filename}.SIF to your bank's SIF validator tool.
```

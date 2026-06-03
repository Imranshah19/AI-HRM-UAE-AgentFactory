# {{WORKER_NAME}} — Eval Plan & Checklist

> **Folder:** `evals/{{worker_slug}}/`
> Prove the worker produces KNOWN-correct output — not "looks right".
> Build this AFTER the worker runs, BEFORE you trust it.

## 1. Test case files — `evals/{{worker_slug}}/test_cases/*.json`

| File | What it proves | Ground truth |
|------|---------------|--------------|
| `happy.json` | Clean data → READY, known {{metric}} | {{official_worked_example \| self}} |
| `blocked_missing_data.json` | Missing {{key field}} → BLOCKED, entity listed | self |
| `blocked_mismatch.json` | {{Totals/consistency broken}} → BLOCKED | self |
| `precondition_unmet.json` | Source not {{finalized/approved}} → STOP | self |
| `edge_{{name}}.json` | {{deadline / expiry / zero-value}} → correct flag | self |
| `idempotency.json` | Run twice → identical output | self |

## 2. Coverage checklist

- [ ] Happy path (known {{metric}})
- [ ] Missing data → BLOCKED with entity list
- [ ] {{Totals/consistency}} mismatch → BLOCKED, never auto-corrected
- [ ] Precondition unmet → STOP
- [ ] Edge: {{describe edge case}}
- [ ] Idempotency: run twice → same output

## 3. Ground-truth note

- Type A: ground ≥1 case against the law's own worked example (not self-output).
- Type B: ground ≥1 case against a real vendor/gov sample file.
- Mark cases: `"ground_truth": "official_worked_example"` vs `"self"`.

## 4. Open assumptions (track)

| Assumption | Default | Confirm with | Status |
|---|---|---|---|
| {{e.g. rounding method}} | {{2dp ROUND_HALF_UP}} | {{legal / policy}} | ⬜ PENDING |
| {{assumption 2}} | {{default}} | {{source}} | ⬜ PENDING |

## 5. Definition of Done

- [ ] spec written — `specs/{{worker_slug}}_worker.spec.md`
- [ ] SKILL.md in `.claude/skills/uae-{{worker_slug}}/`
- [ ] code deterministic (no LLM in the {{maths/logic}})
- [ ] all §2 test cases pass
- [ ] ≥1 case grounded against {{official source}}
- [ ] open assumptions in §4 tracked
- [ ] ⬜ {{sign-off}} documented in run report before any live run

## 6. How to run

```bash
pytest evals/test_cases/test_{{worker_slug}}_worker.py -v
```

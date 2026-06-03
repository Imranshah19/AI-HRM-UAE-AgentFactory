# UAE Agent Factory Kit

Templates + checklist to start a new agent without forgetting anything.

## Usage (Type A — Deterministic)

```bash
SLUG=document_expiry        # snake_case
NAME="Document Expiry"      # human name

# 1. Copy templates
cp templates/spec.md        specs/${SLUG}_worker.spec.md
cp templates/SKILL.md       .claude/skills/uae-${SLUG}/SKILL.md
cp templates/eval_plan.md   evals/${SLUG}/eval_plan.md
cp templates/test_case.json evals/${SLUG}/test_cases/happy.json
cp templates/test_worker.py evals/test_cases/test_${SLUG}_worker.py

# 2. Fill every {{PLACEHOLDER}} in each file
# 3. Write code, run eval, iterate
```

## Kit files

| File | Fill in | Done when |
|------|---------|-----------|
| `templates/spec.md` | goal, scope, inputs, outputs, 7–8 checks | No {{}} remain |
| `templates/SKILL.md` | legal rules, formula, hard rules, escalation | No {{}} remain |
| `templates/eval_plan.md` | test cases table, open assumptions | No {{}} remain |
| `templates/test_case.json` | known-correct input + expected output | ground_truth ≠ "self" for ≥1 case |
| `templates/test_worker.py` | imports, fixtures, all checks tested | All tests pass, 0 xfail |

## What ground truth to use

| Type | Source |
|------|--------|
| A — Deterministic | Law text + worked examples (no vendor needed) |
| B — Format-bound | Real sample from bank / MOHRE / insurer |
| C — Judgment | Curated Q&A set with expected-answer rubrics |

## Per-wave dependencies

```
Wave 1 (Document expiry, Attendance, Leave, Payroll)  — no deps, start now
Wave 2 (Air ticket, Emiratisation)                     — no deps
Wave 3 (Offboarding, Onboarding)                       — needs Wave 1 done
Wave 4 (Contract, Insurance)                           — needs sample files
Wave 5 (Chatbot)                                       — different method
```

See `docs/agents_roadmap.md` for full classification.

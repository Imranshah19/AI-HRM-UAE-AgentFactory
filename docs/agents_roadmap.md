# AI-HRM-UAE-AgentFactory — Remaining Agents Roadmap

> Build order + type classification for the 11 agents left.
> Done: ✅ WPS, ✅ Gratuity. Use the kit (`agent-factory-kit/`) for each.

## Three worker types (decides difficulty + what you need)

| Type | Like | Eval ground truth | Needs external confirm? |
|---|---|---|---|
| **A — Deterministic** | Gratuity | Law/policy worked examples — available now | No (just legal rule check) |
| **B — Format / external-bound** | WPS | A real vendor/gov sample file | Yes — bank/insurer/MOHRE |
| **C — LLM / judgment** | (chatbot) | Not numeric — needs a Q&A test set | Different method entirely |

## Classification of the 11

| Agent | Type | Why | Build difficulty |
|---|---|---|---|
| **Document expiry** | A | Date logic + alerts (visa, labour card, EID, passport). Pure deterministic. | 🟢 Easy — quick win |
| **Attendance** | A | Clock-in/out, late, absence, overtime hours. Deterministic; depends on data source. | 🟢 Easy |
| **Leave** | A | 9 UAE leave types, accrual, LWP tracking. Deterministic with legal rules. | 🟡 Medium |
| **Payroll** | A | Basic + allowances + overtime − deductions (ILOE etc.). Deterministic engine. | 🟡 Medium — foundational |
| **Air ticket** | A | Biennial home-flight entitlement/allowance. Policy-based calc. | 🟢 Easy |
| **Emiratisation** | A/B | Quota + AED 7,000/mo fine = deterministic; Nafis/MOHRE reporting = format-bound. | 🟡 Medium |
| **Offboarding** | A (orchestrator) | Composes Gratuity + leave encashment + notice + dues. No new maths — it calls done workers. | 🟡 Medium — gated by deps |
| **Onboarding** | A (orchestrator) | Checklist + doc collection + contract trigger. Workflow, not calc. | 🟡 Medium |
| **Contract** | B | MOHRE offer-letter / fixed-term contract format + renewal tracking. Format-bound. | 🟠 Needs MOHRE template |
| **Insurance** | B | Mandatory health + ILOE compliance; enrolment files vary by provider. | 🟠 Needs provider format |
| **Chatbot** | C | Bilingual HR Q&A. LLM/RAG — eval = curated Q&A set, not numbers. | 🔴 Last, own method |

## Recommended build order (respects dependencies)

```
WAVE 1 — deterministic, foundational, self-verifiable (no external wait)
  1. Document expiry   ← quick win, builds momentum
  2. Attendance        ← feeds payroll variable/overtime
  3. Leave             ← feeds payroll (LWP) + gratuity (unpaid leave)
  4. Payroll           ← the engine WPS + Gratuity already read from

WAVE 2 — deterministic, policy-bound
  5. Air ticket
  6. Emiratisation     (calc now; park the MOHRE-report format as ⬜)

WAVE 3 — orchestrators (need Wave 1 done first)
  7. Offboarding       (calls Gratuity + Leave + Payroll)
  8. Onboarding

WAVE 4 — format/external-bound (start the confirm request EARLY, build in parallel)
  9. Contract          (MOHRE template)
  10. Insurance        (provider/ILOE format)

WAVE 5 — different methodology
  11. Chatbot          (RAG + Q&A eval set)
```

## Rules of thumb (so you can run solo)

- **Type A:** you can finish end-to-end yourself. Verify the legal rule (one web check
  like we did for gratuity), fill the kit, build, eval against the worked example. Done.
- **Type B:** fill spec + SKILL now, but the **format reference stays ⬜ until you have
  the real sample**. Send the confirm request on day 1, build the logic in parallel,
  drop the sample in when it arrives. (Exactly the WPS pattern.)
- **Type C:** don't force numeric eval. Build a fixed Q&A set with expected-answer
  rubrics; eval = "does it answer correctly + stay in scope + escalate when unsure".

## When to come back for help

Only when a worker hits **external truth you can't self-verify** (a gov/bank/provider
format, or a genuinely ambiguous legal point). Type A workers shouldn't need that.

## Start-of-day-1 parallel action (don't block on it)

- Send the **WPS bank confirm** (5 questions) — unblocks WPS go-live.
- Request the **MOHRE contract template** + **insurance/ILOE file format** — unblocks Wave 4.
- Park the **4 gratuity legal items** (pro-rata, rounding, cap-wording, free-zone) for one HR/legal review.

## Current status

| Agent | Status | Eval | Pending |
|-------|--------|------|---------|
| WPS | ✅ Code done | 39/39 pass | Bank confirm (SCR time, record order, routing codes) |
| Gratuity | ✅ Code done | 32/32 pass | Legal confirm (pro-rata, rounding, cap, free-zone) |
| Document expiry | ⬜ Wave 1 next | — | — |
| Attendance | ⬜ Wave 1 | — | — |
| Leave | ⬜ Wave 1 | — | — |
| Payroll | ⬜ Wave 1 | — | — |
| Air ticket | ⬜ Wave 2 | — | — |
| Emiratisation | ⬜ Wave 2 | — | MOHRE report format |
| Offboarding | ⬜ Wave 3 | — | Needs Wave 1 |
| Onboarding | ⬜ Wave 3 | — | Needs Wave 1 |
| Contract | ⬜ Wave 4 | — | MOHRE contract template |
| Insurance | ⬜ Wave 4 | — | Provider/ILOE enrolment format |
| Chatbot | ⬜ Wave 5 | — | Q&A test set |

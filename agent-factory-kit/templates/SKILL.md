---
name: uae-{{worker_slug}}
description: >
  Use this skill when {{one sentence: what triggers this skill, what domain it covers}}.
  Covers {{key topics: law articles, formats, thresholds}}. Trigger for any task
  mentioning {{keyword list}}.
version: 1.0
---

# UAE {{WORKER_NAME}} Skill

Portable domain expertise for any worker handling {{domain}} tasks.

## Governing law / policy

**{{Law name and number}}** ({{year}}, amended {{year if applicable}}).
{{One sentence on what it establishes.}}

## The formula / logic

```
{{If deterministic: write the formula in plain maths/pseudocode}}
{{Example:}}
daily_rate = basic_salary / 30
entitlement = years × daily_rate × days_per_year
```

**Key thresholds:**
- {{Threshold 1: e.g. service < 1 yr → nil}}
- {{Threshold 2}}
- {{Cap / limit if any}}

**Currency:** AED. **Rounding:** {{describe policy}}.

## Hard rules (non-negotiable)

- **Read-only** on employee/payroll data; the output is never an edit.
- **Never pay / submit / transfer.** Produce the output; a human authorises.
- **Never guess missing {{key field}}.** If null → BLOCK, list the field, stop.
- **{{Domain-specific hard rule — e.g. misconduct → human}}.**

## Escalation cases → BLOCKED

| Situation | Action |
|-----------|--------|
| {{key field}} null / zero | BLOCK — missing data, do not default |
| {{legal edge case}} | BLOCK/FLAG — route to {{HR/legal/zone authority}} |

## Expected output fields

```json
{
  "employee_id": "...",
  "{{key_metric}}": "{{value}}",
  "status": "READY_FOR_APPROVAL | BLOCKED",
  "currency": "AED",
  "notes": "{{what goes here}}"
}
```

## Known values for validation

| Input | Expected output | Law basis |
|-------|----------------|-----------|
| {{param}} | {{value}} | {{Article / section}} |

> **{{Relevant sign-off note — e.g.}} Legal/HR sign-off required before any live settlement.**

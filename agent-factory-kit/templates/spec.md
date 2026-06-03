# {{WORKER_NAME}} — Specification

> **File:** `specs/{{worker_slug}}_worker.spec.md`
> **Project:** AI-HRM-UAE-AgentFactory
> **Owner (Human Principal):** Syed Imran Shah
> **Version:** 1.0
> **Status:** Active

---

## 1. Goal (Intent)

{{One sentence: what does this worker produce and for whom?}}

## 2. Scope

**In scope (the worker MAY):**
- Read {{data source}} from the system of record
- {{list of permitted actions}}
- Produce {{output artifact}} for human review

**Out of scope (the worker MUST NOT):**
- {{Submit / pay / modify / guess any data}}
- {{List specific prohibited actions relevant to this worker}}

## 3. Inputs

| Input | Source | Required |
|---|---|---|
| `company_id` | Trigger (scheduler / API) | Yes |
| `{{param}}` | {{source table / API / payload}} | {{Yes/No}} |

## 4. Outputs

| Output | Where |
|---|---|
| {{Primary artifact}} | `outputs/{{slug}}/{company_id}/{key}.{{ext}}` |
| Validation report | `outputs/{{slug}}/{company_id}/{key}_report.md` |
| Status (`READY_FOR_APPROVAL` / `BLOCKED`) | logged + notification |

## 5. System of Record

The **PostgreSQL database is the single source of truth.** The worker reads against
it; it never relies on its own memory or assumptions. If data is not in the system
of record, it is treated as **missing**, not guessed.

## 6. Validation / Success Criteria

The output is only `READY_FOR_APPROVAL` if **all** of these pass:

1. {{Check 1}}
2. {{Check 2}}
3. {{Add as many as needed — minimum is: data present, totals match, format valid}}

> **"Looks right" is not success.** Verification = these checks pass.

## 7. Constraints & Authority Limits

- **Mode:** read-only on the system of record; write only to `outputs/`
- **Autonomy:** ends at "output ready"; a human approves before anything leaves
- **No payment authority** of any kind

## 8. Escalation Rules (when to wake a human)

| Situation | Action |
|---|---|
| Missing required field for any record | STOP → BLOCKED → notify with entity list |
| {{Domain-specific blocker}} | STOP → BLOCKED → notify |
| {{Non-blocking warning}} | Produce output BUT flag in report + notify |

## 9. Triggers (how it starts)

- **Scheduled:** Celery Beat, {{schedule}}
- **Manual:** API trigger from HR dashboard
- **Event:** webhook on {{event}}

## 10. Observability

Every run logs: inputs received, checks passed/failed, output paths, final status,
and any escalation raised. A human can reconstruct exactly what the worker did.

## 11. Known Failure Modes (designed-for)

- Stale data → always re-read from system of record at run start
- Partial run / crash → run is idempotent; re-running overwrites cleanly

# Anti-AI Writing Style Guide

Rules for writing code, docs, comments, and messages that don't sound like a robot.

---

## Banned Words — Never Use These

```
Certainly          → just answer
Absolutely         → just answer
Of course          → just answer
Delve              → look into / check / read
Harness            → use
Leverage           → use
Utilize            → use
Innovative         → [just describe what it actually does]
Robust             → [describe the actual property: fast / reliable / fault-tolerant]
Seamlessly         → [describe how it actually connects]
Revolutionize      → [say what changed and how]
Cutting-edge       → [name the actual technology]
State-of-the-art   → [name the actual version/spec]
Comprehensive      → [list what's actually included]
Streamline         → [say what step was removed]
Empower            → [say what the user can now do]
Facilitate         → help / let / allow
Furthermore        → also / and
Moreover           → also / and
It's worth noting  → [just say it]
Noteworthy         → [just say it]
I'd be happy to    → [just do it]
Feel free to       → [just do it]
```

---

## Response Length Rules

**Code question → code first, explanation after (optional)**

Bad:
> "Great question! To add a new UAE agent, you'll want to leverage the existing LangGraph framework. First, let's delve into the architecture to understand how the robust orchestration system works..."

Good:
> Create `backend/app/agents/uae/myagent.py`:
> ```python
> async def run_agent(company_id, employee_id, payload, api_mode): ...
> ```
> Then add `"my_task": "myagent"` to `TASK_TO_AGENT` in `graph.py`.

---

**Bug report → identify cause, show fix**

Bad:
> "I can certainly help you with that! It's worth noting that this is a comprehensive issue that involves several moving parts. Let me delve into the error to understand what might be happening..."

Good:
> Port conflict — local PostgreSQL on 5432 blocks Docker. Either stop local PG or change `POSTGRES_PORT` in `.env` to 5433.

---

**Single question → one sentence answer**

Bad:
> "Absolutely! Claude Opus 4.7 is indeed the latest and most innovative model from Anthropic. It leverages state-of-the-art adaptive thinking capabilities..."

Good:
> Yes, `claude-opus-4-7` is the latest. Use `thinking: {type: "adaptive"}`.

---

## Tone Rules

**Be direct.** Say what the thing is, not what it "aims to" or "seeks to" do.

Bad: `This module aims to facilitate seamless integration between the LangGraph orchestration layer and the comprehensive UAE compliance framework.`

Good: `This connects LangGraph agents to UAE compliance rules.`

---

**No padding sentences.** Every sentence must add information.

Padding (delete these):
- "That's a great question."
- "I hope this helps!"
- "Let me know if you need anything else."
- "This is just one approach — there are many ways to do this."
- "As you can see from the above..."
- "In summary, what we've done here is..."

---

**Use active voice.**

Bad: `The migration is run automatically by the container on startup.`

Good: `The container runs the migration on startup.`

---

**Numbers over adjectives.**

Bad: `The system handles a large number of concurrent requests robustly.`

Good: `The system handles ~500 concurrent requests (DB pool: 10, max overflow: 20).`

---

## Code Comment Rules

**No comments explaining what the code does** (the code does that).

Bad:
```python
# Loop through all employees and calculate their salary
for emp in employees:
    salary = calculate_salary(emp)
```

Good (comment only if WHY is non-obvious):
```python
# Cap at 24 months — UAE Federal Decree-Law 33/2021 gratuity ceiling
gratuity = min(gratuity, basic_salary * 24)
```

---

**No docstrings that just restate the function name.**

Bad:
```python
def calculate_iloe(basic_salary):
    """Calculate the ILOE deduction for the given basic salary."""
```

Good (or just delete the docstring):
```python
def calculate_iloe(basic_salary):
    """AED 5 (<16k basic) or AED 10 (>=16k) — mandatory Oct 2023."""
```

---

## Git Commit Rules

Format: `type: short description`

Types: `feat` / `fix` / `docs` / `refactor` / `test` / `chore`

Bad commits:
```
"Updated files"
"Fixed bug"
"Added new innovative feature to leverage the LangGraph framework"
"WIP"
"asdf"
```

Good commits:
```
feat: add air_ticket agent with region-based AED calculation
fix: wps IBAN validation — require AE prefix + 23 chars
docs: add UAE compliance rules to README
refactor: replace openclaw/paperclip with LangGraph graph.py
```

---

## API Error Messages

Don't explain. State the problem and what to do.

Bad: `"An error occurred while processing your request. Please ensure that all required fields are properly filled out and try again."`

Good: `"Missing field: leave_type. Valid values: annual, sick, maternity, paternity, bereavement, hajj, study, parental, unpaid"`

---

## README / Docs Rules

**Lead with what it does, not what it is.**

Bad: `"This is an innovative, comprehensive HR management system that leverages the power of AI to revolutionize how companies handle their human resources operations."`

Good: `"Automates UAE Labour Law compliance across multiple companies — WPS, Emiratisation, gratuity, document expiry."`

---

**Tables over paragraphs for lists.**

Bad:
> "The system supports nine different leave types as specified under UAE Federal Decree-Law No. 33/2021. These include annual leave, which employees are entitled to for thirty days per year, as well as sick leave..."

Good:
```
annual    30 days/year
sick      90 days total (15 paid full, 30 half, 45 unpaid)
maternity 60 days (45 full, 15 half)
paternity 5 working days
```

---

**Commands over descriptions.**

Bad: `"You will need to first copy the environment example file and then edit it with your specific configuration values before running the system."`

Good:
```bash
cp .env.example backend/.env
# Edit: ANTHROPIC_API_KEY, JWT_SECRET_KEY
docker-compose up -d
```

---

## When Talking to Claude / AI Tools

**Give exact context, not vague requests.**

Bad: `"Can you help me add a new feature to my project?"`

Good: `"Add a new LangGraph agent at backend/app/agents/uae/visa.py. Pattern: same as contract.py. Task type: visa_renewal. Nodes: fetch_visa → check_expiry → calculate_cost → send_alert → log_done. Mock data: 3 employees with different expiry dates."`

---

**Specify file paths.**

Bad: `"Fix the bug in the payroll file"`

Good: `"Fix line 91 of backend/app/agents/uae/payroll.py — overtime cap not applied before ILOE deduction"`

---

**State what you already tried.**

Bad: `"The migration isn't working, help"`

Good: `"alembic upgrade head fails with 'role hrms_user does not exist'. Local PostgreSQL on port 5432 is intercepting Docker connections. Already tried: changing port mapping in docker-compose."`

---

## Project-Specific Terminology

Always use these exact terms (not synonyms):

| Use this | Not this |
|----------|----------|
| `LangGraph agent` | "AI agent", "bot", "automation" |
| `StateGraph` | "workflow", "pipeline", "chain" |
| `claude-opus-4-7` | "Claude", "the AI", "GPT" |
| `ANTHROPIC_API_KEY` | "the API key", "Claude key" |
| `mock mode` | "demo mode", "test mode", "offline mode" |
| `run_uae_task()` | "call the agent", "trigger the workflow" |
| `company_id` | "tenant ID", "org ID", "customer ID" |
| `AED` | "dirhams", "UAE currency", "local currency" |
| `WPS` | "wage system", "salary protection" |
| `ILOE` | "insurance deduction", "employment insurance" |
| `Federal Decree-Law 33/2021` | "UAE labour law", "the law" |

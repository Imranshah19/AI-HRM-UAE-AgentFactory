# Section 5: AI Features Implementation

## AI Feature 1: CV Shortlisting Engine

### Overview
Automatically score CVs against job descriptions using semantic similarity, extract structured information via NLP, and provide explainable scoring with bias detection.

### Data Sources & Feature Engineering

**Input Data:**
- Raw CV text (extracted via Apache Tika from PDF/DOCX)
- Job Description (JD) text from `job_postings.description`
- Structured parsing: skills, years of experience, education, certifications

**Feature Engineering Pipeline:**
```
CV Text → Apache Tika → Cleaned Text
                       ↓
                  NLP Parser (spaCy + custom NER)
                       ↓
            ┌──────────────────────────────┐
            │  Extracted Fields:           │
            │  - Skills: ["Python","AWS"]  │
            │  - Experience: 5.5 years     │
            │  - Education: [{"degree":    │
            │    "BS CS", "institution":   │
            │    "FAST NUCES"}]            │
            │  - Certifications: ["AWS SA"]│
            │  - Current title             │
            └──────────────────────────────┘
                       ↓
            Sentence-BERT Embedding (1536-dim)
            model: text-embedding-3-small (OpenAI)
            or all-mpnet-base-v2 (local BERT)
```

### Model Architecture

```
Scoring Components (weighted average):

1. Semantic Similarity (40% weight)
   - CV embedding ⊙ JD embedding → cosine similarity
   - Range: 0.0 to 1.0 → normalized to 0-100

2. Skills Match (30% weight)
   - JD required_skills vs CV parsed_skills
   - Match score = matched / total_required * 100
   - Bonus for nice-to-have skills (+5 per match, capped)

3. Experience Match (20% weight)
   - JD min_experience vs CV experience_years
   - 100 if ≥ min, proportional reduction if below
   - Cap at 100 even if overqualified

4. Education Match (10% weight)
   - Degree level: PhD>Masters>BS>Diploma>Other
   - Institution ranking (optional: ranked university bonus)

Final Score = 0.40*S + 0.30*Skills + 0.20*Exp + 0.10*Edu
```

### Inference Pipeline

```
Request: POST /api/v1/ai/cv-score { application_id }
    ↓
Celery Task: score_cv_task.delay(application_id)
    ↓
Fetch CV text from Elasticsearch / S3
    ↓
NLP Pipeline (spaCy):
  - Named Entity Recognition (custom NER model)
  - Skills extraction against skills ontology (50,000+ skills)
  - Experience date parsing
  - Education extraction
    ↓
Generate embeddings (BERT model or OpenAI API)
    ↓
Compute weighted score
    ↓
SHAP Explainability:
  - TreeExplainer for XGBoost component
  - Custom explanation for embedding similarity
    ↓
Bias Detection:
  - Anonymize CV (remove name, gender pronouns, age indicators)
  - Re-score anonymized CV
  - Flag if score changes > 5 points
    ↓
Store result in job_applications:
  ai_score, ai_score_breakdown, ai_scored_at
    ↓
WebSocket/SSE push to recruiter dashboard
```

### Explainability Output
```json
{
  "score": 84,
  "breakdown": {
    "semantic_similarity": { "score": 87, "weight": 0.40, "contribution": 34.8 },
    "skills_match": { "score": 90, "weight": 0.30, "contribution": 27.0,
                      "matched": ["Python","FastAPI","PostgreSQL","Docker"],
                      "missing": ["AWS","Kubernetes"],
                      "bonus": ["React"] },
    "experience_match": { "score": 100, "weight": 0.20, "contribution": 20.0,
                          "required": 4, "candidate": 6.5 },
    "education_match": { "score": 75, "weight": 0.10, "contribution": 7.5,
                         "required": "BS CS", "candidate": "BS Software Engineering" }
  },
  "explanation": "Score 84/100 — Strong semantic match to JD. Python, FastAPI, PostgreSQL, Docker all matched. Missing AWS and Kubernetes (required). 6.5 years experience exceeds 4yr requirement. BS Software Engineering accepted for CS requirement.",
  "bias_flags": [],
  "anonymized_score": 83,
  "bias_delta": 1
}
```

### Monitoring & Retraining
- **Feedback loop:** Every HR accept/reject recorded in `cv_score_feedback` table
- **Retraining trigger:** Quarterly, or when feedback volume reaches 500 new labels
- **Model versioning:** MLflow tracks model versions, auto-rollback if accuracy drops >5%
- **Accuracy target:** >75% alignment with final HR hiring decisions

### Bias Mitigation
- Protected attributes (gender, age, nationality, religion markers) removed before scoring
- Fairness report generated monthly: approval rates across demographic groups
- Threshold: if any group has >10% lower approval rate than highest group → alert

---

## AI Feature 2: HR Chatbot

### Architecture
```
User Message
     ↓
FastAPI Endpoint: POST /api/v1/ai/chatbot/query
     ↓
Intent Classification (LLM):
  - INFO_QUERY: "How many leaves do I have?"
  - SELF_SERVICE_ACTION: "Apply for leave tomorrow"
  - POLICY_QUERY: "What is the maternity policy?"
  - ESCALATE: "I want to raise a grievance"
     ↓
RAG Pipeline (LangChain):
  1. Embed user query → text-embedding-3-small
  2. Similarity search in pgvector/Pinecone
     (corpus: HR policy PDFs, FAQs, procedure docs)
  3. Retrieve top-5 relevant chunks
  4. Construct prompt: context + user history + query
  5. LLM call (GPT-4o or Claude claude-sonnet-4-6)
     ↓
Self-Service Handler (if action intent):
  - Leave apply: call POST /api/v1/leave/requests
  - Balance check: call GET /api/v1/leave/balances
  - Payslip request: call GET /api/v1/self-service/payslips
     ↓
Response with action confirmations
     ↓
Store conversation: chat_sessions, chat_messages tables
```

### RAG Document Corpus
- HR Policy Manual (PDF → chunked, embedded)
- Employee Handbook
- Leave Policy Document
- Payroll Calendar
- Onboarding Guide
- Benefits Summary
- FAQ Database (HR-maintained Q&A pairs)

**Chunking strategy:** Recursive text splitter, 512 tokens per chunk, 50 token overlap

### System Prompt
```
You are an HR Assistant for {company_name}. You help employees with:
1. HR policy questions (use provided context only — never hallucinate)
2. Leave and attendance queries (fetch real data via tools)
3. Payslip and compensation questions (fetch real data via tools)
4. Raising internal requests

Rules:
- Always respond in the employee's preferred language ({locale})
- For sensitive topics (grievances, harassment, salary disputes), always escalate to human HR
- Never reveal other employees' data
- If uncertain, say "I'm not sure — let me connect you with HR"
- For compliance/legal advice, always direct to HR Manager

Employee context: {employee_name}, {department}, {role}
Current date: {date}
```

### Escalation Rules
| Trigger | Action |
|---------|--------|
| Intent: grievance, harassment, discrimination | Auto-escalate to HR Manager |
| Query not answered after 2 rephrases | Offer human HR chat |
| Employee explicitly requests human | Immediate transfer with transcript |
| Policy not found in knowledge base | Escalate + create FAQ gap ticket |

### Channels
- **Web widget:** Embedded in all pages (bottom-right floating button)
- **WhatsApp:** Meta Business API webhook → same LangChain pipeline
- **Slack Bot:** Slack Events API → slash command `/hr ask ...`

---

## AI Feature 3: Performance Prediction Model

### Input Features (Feature Engineering)
```python
features = {
    # Historical performance
    "avg_kpi_score_last_2_cycles": float,      # 0-5
    "avg_manager_rating_last_2": float,
    "avg_peer_rating_last_cycle": float,
    "goals_achievement_pct": float,             # 0-100

    # Behavioral signals
    "attendance_rate_ytd": float,               # 0-1
    "late_arrival_count_ytd": int,
    "leave_utilization_rate": float,            # taken/entitled
    "training_completion_rate": float,          # 0-1

    # Career trajectory
    "tenure_months": int,
    "months_in_current_role": int,
    "promotion_count": int,
    "lateral_moves": int,
    "pip_history": int,                         # 0/1 flag

    # Engagement proxies
    "self_service_request_count": int,          # High = more engaged
    "training_voluntary_count": int,            # Self-initiated training
}
```

### Model Training
```python
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# Labels: historical performance band (High/Medium/Low)
# Derived from past review cycles where next cycle outcome is known

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('model', GradientBoostingClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        random_state=42
    ))
])

# Training data: employees with ≥2 review cycles (labeled)
# Minimum 200 samples required before deploying
# Class balancing: SMOTE for imbalanced High/Low classes
```

### Inference Output
```json
{
  "employee_id": "uuid",
  "predicted_band": "High",
  "confidence": 0.78,
  "feature_importance": [
    { "feature": "avg_kpi_score_last_2_cycles", "value": 4.2, "importance": 0.35 },
    { "feature": "attendance_rate_ytd", "value": 0.97, "importance": 0.18 },
    { "feature": "training_completion_rate", "value": 0.90, "importance": 0.15 }
  ],
  "model_version": "v3.2",
  "computed_at": "2024-01-15T10:00:00Z"
}
```

### Retraining Schedule
- Triggered quarterly after each review cycle completes
- New actuals vs predictions logged in `model_performance_log` table
- Auto-retrain if: F1 score drops below 0.70 on validation set

---

## AI Feature 4: Attrition Prediction Model

### Feature Engineering
```python
attrition_features = {
    # Compensation risk
    "salary_vs_market_pct": float,      # internal salary / market median * 100
    "last_increment_months_ago": int,
    "increment_pct_last": float,

    # Engagement indicators
    "performance_band_trend": int,      # -1 declining, 0 stable, +1 improving
    "manager_nps_score": float,         # From 360 review
    "peer_satisfaction_score": float,

    # Behavioral patterns
    "unplanned_leave_count_90d": int,
    "late_count_trend_30d": int,        # Increase = risk signal
    "login_frequency_trend": float,     # Drop = disengagement

    # Career signals
    "tenure_months": int,
    "months_since_last_promotion": int,
    "role_change_count": int,
    "peer_departure_rate_team": float,  # If team is leaving, risk increases

    # External signals (optional)
    "linkedin_activity_spike": bool,    # Via social listening API (optional)
}
```

### Model Architecture
```python
from sklearn.ensemble import RandomForestClassifier
import shap

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=8,
    min_samples_leaf=10,
    class_weight='balanced',    # Handle imbalanced attrition (typically 10-20%)
    random_state=42
)

# SHAP for explainability
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_employee)
```

### Risk Scoring Output
```json
{
  "employee_id": "uuid",
  "risk_score": 73.5,
  "risk_tier": "high",
  "top_factors": [
    {
      "factor": "salary_vs_market_pct",
      "description": "Salary is 18% below market median for this role/level",
      "contribution": 0.35,
      "current_value": -18,
      "action": "salary_review"
    },
    {
      "factor": "months_since_last_promotion",
      "description": "36 months without promotion — exceeds 24mo average for this grade",
      "contribution": 0.28,
      "current_value": 36,
      "action": "career_discussion"
    },
    {
      "factor": "unplanned_leave_count_90d",
      "description": "4 unplanned leave instances in 90 days — elevated absenteeism",
      "contribution": 0.15,
      "current_value": 4,
      "action": "wellness_checkin"
    }
  ],
  "recommendations": [
    { "action": "schedule_career_conversation", "priority": "critical", "by": "2024-02-01" },
    { "action": "initiate_salary_review", "priority": "high", "by": "2024-01-31" },
    { "action": "wellness_check_in", "priority": "medium", "by": "2024-01-25" }
  ],
  "model_version": "v2.1",
  "confidence": 0.81
}
```

### Alert Workflow
```
Daily Celery task: compute_attrition_scores()
    ↓
For each active employee:
  - Extract features from DB
  - Run model inference
  - Store in attrition_risk_scores
    ↓
Check for score crossing thresholds:
  - score > 70 → HIGH alert to HR Manager
  - score > 85 → CRITICAL alert to HR Manager + CHRO
    ↓
Send notification via email + in-app
Include: employee name, score, top 3 factors, recommended actions
    ↓
HR reviews and takes action (recorded for model feedback)
```

---

## AI Feature 5: Smart Analytics Dashboard

### Natural Language Query (NLQ) Engine
```python
# NLQ → SQL pipeline

async def process_nlq(query: str, tenant_id: str, user_role: str) -> dict:
    """
    Example: "Show me attrition in Q3 2024 by department"
    """
    # Step 1: LLM generates SQL with schema context
    schema_context = get_tenant_schema_summary(tenant_id)

    prompt = f"""
    You are an SQL generator for an HRMS. Convert the user's question to SQL.

    Available tables and columns:
    {schema_context}

    Rules:
    - Only use SELECT statements
    - Filter by tenant_id = '{tenant_id}' always
    - Apply RBAC: role={user_role}, only show permitted fields
    - Return: sql, chart_type, x_axis, y_axis, explanation

    Question: {query}
    """

    response = await llm.agenerate(prompt)
    sql, chart_config = parse_llm_sql_response(response)

    # Step 2: Validate SQL (safety: no drops, no updates, whitelist tables)
    validated_sql = validate_readonly_sql(sql)

    # Step 3: Execute against read replica
    results = await db_readonly.fetch(validated_sql)

    return {
        "data": results,
        "chart_type": chart_config.chart_type,
        "explanation": chart_config.explanation,
        "sql_generated": validated_sql  # Shown to admin for transparency
    }
```

### Anomaly Detection
```python
# Daily Celery task
def detect_hr_anomalies(tenant_id: str):
    anomalies = []

    # 1. Sudden attendance drop (department-level)
    dept_attendance = get_weekly_attendance_rate_by_dept(tenant_id)
    for dept, rates in dept_attendance.items():
        change = rates[-1] - rates[-2]  # Week-over-week
        if change < -0.15:  # >15% drop
            anomalies.append({
                "type": "attendance_drop",
                "dept": dept,
                "severity": "high",
                "detail": f"Attendance dropped {abs(change)*100:.0f}% in {dept}"
            })

    # 2. Overtime spike
    overtime = get_overtime_trend(tenant_id)
    if overtime.current > overtime.avg_3month * 1.5:
        anomalies.append({"type": "overtime_spike", ...})

    # 3. Bulk leave requests (possible mass exodus signal)
    bulk_leave = detect_bulk_leave_pattern(tenant_id)

    # Store and alert
    store_anomalies(anomalies)
    if anomalies:
        notify_hr_manager(tenant_id, anomalies)
```

---

## AI Feature 6: AI Explainability & Fairness Layer

### Audit Entry for Every AI Decision
```python
async def store_ai_decision(
    tenant_id: str,
    employee_id: str,
    model_type: str,          # cv_scorer, attrition, performance
    decision: str,            # The output / recommendation
    confidence: float,
    shap_values: dict,        # Raw SHAP values
    natural_language_explanation: str,
    human_override: bool = False,
    override_reason: str = None
):
    await db.execute("""
        INSERT INTO audit_logs (
            tenant_id, resource_type, resource_id, action,
            ai_decision, human_override, override_reason
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
    """, tenant_id, "ai_decision", employee_id, f"AI_{model_type.upper()}",
         json.dumps({
             "decision": decision,
             "confidence": confidence,
             "shap_values": shap_values,
             "explanation": natural_language_explanation
         }),
         human_override, override_reason
    )
```

### Monthly Fairness Report Structure
```sql
-- Fairness report query
SELECT
    demographic_group,      -- gender, age_band, nationality
    COUNT(*) as total_evaluated,
    AVG(ai_score) as avg_ai_score,
    COUNT(*) FILTER (WHERE outcome = 'hired') as hired_count,
    COUNT(*) FILTER (WHERE outcome = 'hired')::float / COUNT(*) as hire_rate,
    COUNT(*) FILTER (WHERE human_override = true) as override_count
FROM ai_decisions_view
WHERE model_type = 'cv_scorer'
  AND period = '2024-Q1'
GROUP BY demographic_group;
```

### HR Override UI
- Every AI recommendation has an "Override" button (visible to authorized roles)
- Override requires: reason selection + free text explanation
- Override tracked in audit log with both AI decision and human decision
- Monthly report: AI vs Human decision divergence rate by model

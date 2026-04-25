# SECTION 5 — AI FEATURES IMPLEMENTATION

## AI Feature 1: CV Shortlisting Engine

### Data Sources & Feature Engineering
- Input A: Job Description (title, requirements text, skills array, experience range)
- Input B: Candidate CV (raw text extracted from PDF/DOCX via pdfplumber / python-docx)
- NLP extraction pipeline: SpaCy NER → extract {skills, years_experience, education_level,
  certifications, companies, job_titles}
- Feature vector: sentence-transformer embedding of JD + CV

### Model Selection
- Model: `all-MiniLM-L6-v2` (sentence-transformers) — 384-dim embeddings
- Similarity: cosine similarity between JD embedding and CV embedding
- Augmented with rule-based scoring for hard requirements (years_exp_match,
  education_match, required_skills_matched)

### Working Python Code

```python
# ai/cv_scorer.py
from sentence_transformers import SentenceTransformer
import numpy as np
import spacy
import shap
from typing import Optional
import re

# Load once at startup, reuse across requests
_model = SentenceTransformer("all-MiniLM-L6-v2")
_nlp = spacy.load("en_core_web_sm")

TECH_SKILLS = {
    "python", "javascript", "typescript", "react", "nextjs", "fastapi",
    "django", "postgresql", "redis", "docker", "kubernetes", "aws",
    "machine learning", "deep learning", "sql", "mongodb", "elasticsearch",
    "java", "golang", "rust", "flutter", "react native",
}

def extract_features_from_text(text: str) -> dict:
    """Extract structured features from CV or JD text using SpaCy + regex."""
    doc = _nlp(text.lower())

    # Extract skills (intersection with known skill list)
    words_and_bigrams = set()
    tokens = [t.text for t in doc if not t.is_stop]
    words_and_bigrams.update(tokens)
    words_and_bigrams.update(
        f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)
    )
    extracted_skills = words_and_bigrams.intersection(TECH_SKILLS)

    # Extract years of experience
    experience_patterns = [
        r'(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)',
        r'(\d+)\s*-\s*\d+\s*years?',
    ]
    experience_years = 0
    for pattern in experience_patterns:
        matches = re.findall(pattern, text.lower())
        if matches:
            experience_years = max(int(m) for m in matches)
            break

    # Extract education level
    education_keywords = {
        "phd": 5, "doctorate": 5,
        "master": 4, "msc": 4, "mba": 4, "ms ": 4,
        "bachelor": 3, "bsc": 3, "be ": 3, "bs ": 3,
        "diploma": 2, "intermediate": 1, "matric": 1,
    }
    education_level = 0
    education_label = "Not detected"
    for keyword, level in education_keywords.items():
        if keyword in text.lower() and level > education_level:
            education_level = level
            education_label = keyword.strip().title()

    return {
        "skills": list(extracted_skills),
        "experience_years": experience_years,
        "education_level": education_level,
        "education_label": education_label,
        "full_text": text,
    }


def score_cv_against_jd(
    jd_text: str,
    cv_text: str,
    required_skills: list[str],
    min_experience_years: float,
    required_education_level: int = 3,
) -> dict:
    """
    Score a CV against a Job Description.
    Returns score 0-100 with breakdown and natural language explanation.
    """
    # 1. Semantic similarity (embedding cosine)
    embeddings = _model.encode([jd_text, cv_text], convert_to_numpy=True)
    semantic_score = float(np.dot(embeddings[0], embeddings[1]) / (
        np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1])
    ))
    semantic_score = max(0.0, min(1.0, semantic_score)) * 100

    # 2. Feature extraction
    jd_features = extract_features_from_text(jd_text)
    cv_features = extract_features_from_text(cv_text)

    # 3. Skills match score
    required_set = {s.lower() for s in required_skills}
    cv_skills_set = {s.lower() for s in cv_features["skills"]}
    matched_skills = required_set.intersection(cv_skills_set)
    missing_skills = required_set - cv_skills_set
    skills_score = (len(matched_skills) / max(len(required_set), 1)) * 100

    # 4. Experience score
    exp_score = 0.0
    exp_note = ""
    if cv_features["experience_years"] >= min_experience_years:
        exp_score = 100.0
        exp_note = f"{cv_features['experience_years']}yr exp matched"
    else:
        if min_experience_years > 0:
            exp_score = (cv_features["experience_years"] / min_experience_years) * 100
        exp_note = (
            f"{cv_features['experience_years']}yr exp detected, "
            f"{min_experience_years}yr required"
        )

    # 5. Education score
    edu_score = 100.0 if cv_features["education_level"] >= required_education_level else 50.0
    edu_note = cv_features["education_label"]

    # 6. Weighted composite score
    weights = {
        "semantic": 0.30,
        "skills": 0.35,
        "experience": 0.25,
        "education": 0.10,
    }
    final_score = (
        semantic_score * weights["semantic"]
        + skills_score * weights["skills"]
        + exp_score * weights["experience"]
        + edu_score * weights["education"]
    )
    final_score = round(min(100.0, max(0.0, final_score)), 1)

    # 7. Natural language explanation
    explanation_parts = []
    if matched_skills:
        explanation_parts.append(f"Skills matched: {', '.join(matched_skills)}")
    if missing_skills:
        explanation_parts.append(f"Skills missing: {', '.join(missing_skills)}")
    explanation_parts.append(exp_note)
    explanation_parts.append(f"Education: {edu_note}")

    explanation = (
        f"Score {final_score}/100 — "
        + " | ".join(explanation_parts)
    )

    return {
        "overall_score": final_score,
        "breakdown": {
            "semantic_similarity": round(semantic_score, 1),
            "skills_match": round(skills_score, 1),
            "experience_match": round(exp_score, 1),
            "education_match": round(edu_score, 1),
        },
        "matched_skills": list(matched_skills),
        "missing_skills": list(missing_skills),
        "candidate_experience_years": cv_features["experience_years"],
        "candidate_education": cv_features["education_label"],
        "explanation": explanation,
        "bias_flags": detect_bias_flags(cv_text),
    }


def detect_bias_flags(cv_text: str) -> dict:
    """
    Detect potential bias indicators in CV text.
    Flags these for human review — does NOT affect score.
    """
    text_lower = cv_text.lower()
    flags = {}

    # Gender indicators
    gender_words = ["he/him", "she/her", "mr.", "mrs.", "ms.", "father", "mother"]
    if any(w in text_lower for w in gender_words):
        flags["potential_gender_indicator"] = True

    # Age/year of birth indicators
    yob_pattern = r'\b(19[6-9]\d|20[0-1]\d)\b'
    if re.search(yob_pattern, cv_text):
        flags["potential_age_indicator"] = True

    # Nationality/religion indicators
    national_words = ["nationality:", "religion:", "race:", "caste:"]
    if any(w in text_lower for w in national_words):
        flags["personal_demographic_data"] = True

    return flags
```

### Inference Pipeline
```
POST /api/v1/ai/cv-score
  → FastAPI handler dispatches Celery task score_cv_task(application_id, job_id)
  → Celery worker:
      1. Fetch job_postings row → extract JD text + required_skills + min_exp
      2. Fetch job_applications row → get cv_url
      3. Download CV from S3 → extract text (pdfplumber for PDF, python-docx for DOCX)
      4. Call score_cv_against_jd()
      5. Store result in job_applications: ai_score, ai_score_breakdown,
         ai_explanation, ai_bias_flags, ai_scored_at
      6. Insert into ai_decisions table (audit)
      7. Notify recruiter via WebSocket / notification
  → GET /api/v1/ai/cv-score/{job_id} returns stored result
```

### Monitoring & Retraining
- Track: HR accept/reject decisions per scored candidate → store in ai_feedback table
- Quarterly retraining trigger: if n_feedback_samples > 500 AND model_age > 90 days
- Retrain by fine-tuning embeddings on domain-specific HR data pairs
- A/B test new model vs current with 10% traffic split (feature flag: `new_cv_model_v2`)

---

## AI Feature 2: HR Chatbot (RAG)

### Architecture: LangChain + pgvector RAG

```python
# ai/hr_chatbot.py
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import PGVector
from langchain.chains import ConversationalRetrievalChain
from langchain.schema import HumanMessage, SystemMessage
from langchain.memory import ConversationBufferWindowMemory
import os

CONNECTION_STRING = os.environ["DATABASE_URL"]
COLLECTION_NAME = "hr_policy_documents"

def get_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return PGVector(
        collection_name=COLLECTION_NAME,
        connection_string=CONNECTION_STRING,
        embedding_function=embeddings,
    )


def build_rag_chain(session_id: str):
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    vectorstore = get_vector_store()
    retriever = vectorstore.as_retriever(
        search_type="mmr",          # Maximal Marginal Relevance — reduces redundancy
        search_kwargs={"k": 5, "fetch_k": 20},
    )
    memory = ConversationBufferWindowMemory(
        k=5,
        memory_key="chat_history",
        return_messages=True,
        output_key="answer",
    )
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        return_source_documents=True,
        verbose=False,
        combine_docs_chain_kwargs={
            "prompt": HR_SYSTEM_PROMPT,
        }
    )
    return chain


HR_SYSTEM_PROMPT_TEMPLATE = """You are an HR assistant for {company_name}.
Answer questions based ONLY on the provided HR policy documents.
If the answer is not in the documents, say "I don't have that information in
the current HR policies. Please contact HR directly at hr@company.com."

Rules:
- Never make up policy information
- Always cite the source document and section
- For leave balance queries, instruct user to check the portal
- For sensitive requests (salary changes, complaints), escalate to human HR
- Be concise and professional

Context from HR documents:
{context}

Chat history:
{chat_history}

Question: {question}
Answer:"""


async def query_chatbot(
    query: str,
    session_id: str,
    employee_id: str,
    tenant_id: str,
) -> dict:
    """Process HR chatbot query with RAG."""

    # Check if this needs escalation before even calling LLM
    escalation_keywords = [
        "harassment", "complaint", "discrimination", "grievance",
        "legal action", "salary increase", "promotion request",
    ]
    needs_escalation = any(kw in query.lower() for kw in escalation_keywords)

    if needs_escalation:
        return {
            "answer": (
                "This topic requires direct HR attention. "
                "I'm connecting you with an HR representative. "
                "You can also email hr@company.com or call extension 100."
            ),
            "sources": [],
            "session_id": session_id,
            "escalated": True,
            "escalation_reason": "sensitive_topic",
        }

    # Load session chain (in practice, store chain state in Redis)
    chain = build_rag_chain(session_id)

    result = chain.invoke({"question": query})

    # Extract source citations
    sources = []
    for doc in result.get("source_documents", []):
        sources.append({
            "document": doc.metadata.get("source", "HR Policy"),
            "page": doc.metadata.get("page", 1),
            "excerpt": doc.page_content[:200] + "...",
        })

    # Log to audit
    await log_chatbot_interaction(
        employee_id=employee_id,
        tenant_id=tenant_id,
        query=query,
        answer=result["answer"],
        sources=sources,
        session_id=session_id,
    )

    return {
        "answer": result["answer"],
        "sources": sources,
        "session_id": session_id,
        "escalated": False,
    }


def ingest_policy_document(file_path: str, metadata: dict, tenant_id: str):
    """Ingest HR policy PDF into vector store."""
    from langchain_community.document_loaders import PyPDFLoader

    loader = PyPDFLoader(file_path)
    documents = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", " "],
    )
    chunks = splitter.split_documents(documents)

    # Add tenant metadata to each chunk
    for chunk in chunks:
        chunk.metadata.update({**metadata, "tenant_id": tenant_id})

    vectorstore = get_vector_store()
    vectorstore.add_documents(chunks)

    return len(chunks)
```

---

## AI Feature 3: Performance Prediction

```python
# ai/performance_predictor.py
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
import joblib
from pathlib import Path

MODEL_PATH = Path("models/performance_predictor_v1.joblib")

FEATURE_COLUMNS = [
    "avg_kpi_score_prev_2_cycles",
    "attendance_rate_ytd",
    "training_completions_ytd",
    "peer_rating_avg",
    "manager_rating_avg",
    "self_rating_avg",
    "tenure_months",
    "days_since_last_promotion",
    "leave_days_taken_ytd",
    "late_arrivals_count_ytd",
    "training_hours_ytd",
    "pip_history_count",
]

BAND_LABELS = {0: "unsatisfactory", 1: "below", 2: "meets", 3: "exceeds", 4: "exceptional"}


def extract_prediction_features(employee_id: str, db_session) -> pd.DataFrame:
    """Build feature vector from DB for performance prediction."""
    # In production this is a SQL query joining multiple tables
    # Abbreviated here — see full implementation in services/ai_service.py

    raw = db_session.execute("""
        SELECT
            e.id,
            COALESCE(AVG(pr.overall_rating) FILTER (
                WHERE ac.year >= EXTRACT(YEAR FROM NOW()) - 2
            ), 2.5)                                          AS avg_kpi_score_prev_2_cycles,
            COALESCE(
                COUNT(ar.id) FILTER (WHERE ar.status = 'present') * 1.0
                / NULLIF(COUNT(ar.id), 0), 0.85
            )                                               AS attendance_rate_ytd,
            COALESCE(COUNT(te.id) FILTER (
                WHERE te.status = 'completed'
                AND te.completed_at >= date_trunc('year', NOW())
            ), 0)                                           AS training_completions_ytd,
            COALESCE(AVG(pr2.overall_rating) FILTER (
                WHERE pr2.review_type = 'peer'
            ), 2.5)                                         AS peer_rating_avg,
            COALESCE(AVG(pr3.overall_rating) FILTER (
                WHERE pr3.review_type = 'manager'
            ), 2.5)                                         AS manager_rating_avg,
            COALESCE(AVG(pr4.overall_rating) FILTER (
                WHERE pr4.review_type = 'self'
            ), 2.5)                                         AS self_rating_avg,
            EXTRACT(MONTH FROM AGE(NOW(), e.joining_date))  AS tenure_months,
            COALESCE(EXTRACT(DAYS FROM AGE(NOW(),
                MAX(eh.promotion_date))), 730)               AS days_since_last_promotion,
            COALESCE(SUM(lr.total_days) FILTER (
                WHERE lr.status = 'approved'
                AND lr.start_date >= date_trunc('year', NOW())
            ), 0)                                           AS leave_days_taken_ytd,
            COALESCE(COUNT(ar2.id) FILTER (
                WHERE ar2.late_minutes > 0
                AND ar2.attendance_date >= date_trunc('year', NOW())
            ), 0)                                           AS late_arrivals_count_ytd,
            COALESCE(SUM(te2.duration_hours) FILTER (
                WHERE te2.completed_at >= date_trunc('year', NOW())
            ), 0)                                           AS training_hours_ytd,
            COALESCE(COUNT(pip.id), 0)                      AS pip_history_count
        FROM employees e
        LEFT JOIN performance_reviews pr ON pr.employee_id = e.id
        LEFT JOIN appraisal_cycles ac ON ac.id = pr.cycle_id
        LEFT JOIN attendance_records ar ON ar.employee_id = e.id
        LEFT JOIN training_enrollments te ON te.employee_id = e.id
        LEFT JOIN performance_reviews pr2 ON pr2.employee_id = e.id
        LEFT JOIN performance_reviews pr3 ON pr3.employee_id = e.id
        LEFT JOIN performance_reviews pr4 ON pr4.employee_id = e.id
        LEFT JOIN employee_history eh ON eh.employee_id = e.id
        LEFT JOIN leave_requests lr ON lr.employee_id = e.id
        LEFT JOIN attendance_records ar2 ON ar2.employee_id = e.id
        LEFT JOIN training_enrollments te2 ON te2.employee_id = e.id
        LEFT JOIN pips pip ON pip.employee_id = e.id
        WHERE e.id = :employee_id
        GROUP BY e.id
    """, {"employee_id": employee_id}).fetchone()

    return pd.DataFrame([dict(raw._mapping)])[FEATURE_COLUMNS]


def predict_performance_band(employee_id: str, db_session) -> dict:
    """Predict next-cycle performance band for employee."""

    model = joblib.load(MODEL_PATH)
    explainer = shap.TreeExplainer(model)

    features_df = extract_prediction_features(employee_id, db_session)
    features_array = features_df.values

    # Predict
    proba = model.predict_proba(features_array)[0]  # shape: (5,) for 5 bands
    predicted_class = int(np.argmax(proba))
    confidence = float(proba[predicted_class])
    predicted_band = BAND_LABELS[predicted_class]

    # SHAP explanation
    shap_values = explainer.shap_values(features_array)
    # shap_values shape for multiclass: (n_classes, n_samples, n_features)
    class_shap = shap_values[predicted_class][0]

    # Top 3 positive and negative factors
    feature_impact = sorted(
        zip(FEATURE_COLUMNS, class_shap),
        key=lambda x: abs(x[1]),
        reverse=True
    )[:5]

    # Human-readable factor names
    readable_names = {
        "avg_kpi_score_prev_2_cycles": "Historical KPI Score",
        "attendance_rate_ytd": "Attendance Rate",
        "training_completions_ytd": "Training Completions",
        "peer_rating_avg": "Peer Review Rating",
        "manager_rating_avg": "Manager Rating",
        "tenure_months": "Tenure",
        "late_arrivals_count_ytd": "Late Arrivals",
        "pip_history_count": "PIP History",
    }

    explanations = []
    for feature, impact in feature_impact:
        direction = "positively" if impact > 0 else "negatively"
        explanations.append({
            "factor": readable_names.get(feature, feature),
            "impact": round(float(impact), 4),
            "direction": direction,
            "current_value": round(float(features_df[feature].values[0]), 2),
        })

    result = {
        "employee_id": employee_id,
        "predicted_band": predicted_band,
        "confidence_score": round(confidence, 4),
        "confidence_percentage": round(confidence * 100, 1),
        "band_probabilities": {
            BAND_LABELS[i]: round(float(p), 4) for i, p in enumerate(proba)
        },
        "key_factors": explanations,
        "explanation": (
            f"Predicted {predicted_band.replace('_', ' ').title()} "
            f"performer with {round(confidence * 100)}% confidence. "
            f"Primary driver: {explanations[0]['factor']} "
            f"({explanations[0]['direction']} impacting)."
        ),
        "model_version": "v1.2",
        "predicted_at": pd.Timestamp.now().isoformat(),
    }

    return result
```

---

## AI Feature 4: Attrition Prediction

```python
# ai/attrition_predictor.py
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
import joblib

ATTRITION_MODEL_PATH = "models/attrition_predictor_v1.joblib"

RISK_TIERS = {
    (0, 30): "low",
    (30, 50): "medium",
    (50, 70): "high",
    (70, 100): "critical",
}

INTERVENTIONS = {
    "salary_below_market": "Schedule compensation review against market benchmarks",
    "low_manager_rating": "Facilitate manager-employee 1:1 coaching sessions",
    "high_absenteeism": "Initiate wellbeing check-in and EAP referral",
    "no_promotion_3_years": "Review career progression path and create development plan",
    "low_peer_engagement": "Consider team building and cross-functional collaboration",
    "high_overtime": "Review workload distribution and consider backfill",
    "recent_team_departure": "Conduct stay interview, address team morale",
    "low_training_investment": "Assign targeted learning path with clear skill goals",
}

ATTRITION_FEATURES = [
    "tenure_months", "salary_vs_market_ratio", "manager_nps_score",
    "leave_days_used_ratio", "absenteeism_rate", "late_arrivals_count",
    "months_since_last_promotion", "peer_engagement_score",
    "training_hours_ytd", "avg_overtime_hours_monthly",
    "satisfaction_survey_score", "team_attrition_rate_ytd",
    "pending_grievances_count", "performance_band_numeric",
]


def get_risk_tier(risk_score: float) -> str:
    for (low, high), tier in RISK_TIERS.items():
        if low <= risk_score < high:
            return tier
    return "critical"


def predict_attrition_risk(employee_id: str, db_session) -> dict:
    """Predict attrition risk for a single employee."""

    model = joblib.load(ATTRITION_MODEL_PATH)
    explainer = shap.TreeExplainer(model)

    # Feature extraction (SQL in production)
    features = _extract_attrition_features(employee_id, db_session)
    features_df = pd.DataFrame([features])[ATTRITION_FEATURES]

    # Predict (binary: 0=stays, 1=leaves)
    risk_proba = float(model.predict_proba(features_df.values)[0][1])
    risk_score = round(risk_proba * 100, 1)
    risk_tier = get_risk_tier(risk_score)

    # SHAP
    shap_values = explainer.shap_values(features_df.values)
    class1_shap = shap_values[1][0] if isinstance(shap_values, list) else shap_values[0]

    # Top 3 risk factors
    factor_impacts = sorted(
        zip(ATTRITION_FEATURES, class1_shap),
        key=lambda x: x[1],  # highest positive SHAP = most contributing to attrition
        reverse=True
    )[:3]

    risk_factors = []
    recommendations = []
    for feature, impact in factor_impacts:
        if impact > 0:
            risk_factors.append({
                "factor": _readable_feature_name(feature),
                "current_value": features[feature],
                "shap_impact": round(float(impact), 4),
            })
            intervention_key = _get_intervention_key(feature, features[feature])
            if intervention_key:
                recommendations.append(INTERVENTIONS.get(intervention_key, ""))

    return {
        "employee_id": employee_id,
        "risk_score": risk_score,
        "risk_tier": risk_tier,
        "risk_factors": risk_factors[:3],
        "recommendations": [r for r in recommendations[:3] if r],
        "explanation": (
            f"{risk_tier.upper()} attrition risk ({risk_score}%). "
            f"Top driver: {risk_factors[0]['factor'] if risk_factors else 'N/A'}."
        ),
        "should_alert_hr": risk_score >= 70,
        "model_version": "v1.0",
        "predicted_at": pd.Timestamp.now().isoformat(),
    }


def _readable_feature_name(feature: str) -> str:
    names = {
        "salary_vs_market_ratio": "Salary Below Market Rate",
        "manager_nps_score": "Low Manager NPS Score",
        "months_since_last_promotion": "Long Time Without Promotion",
        "absenteeism_rate": "High Absenteeism Rate",
        "avg_overtime_hours_monthly": "High Overtime Load",
        "team_attrition_rate_ytd": "Recent Team Departures",
        "training_hours_ytd": "Low Training Investment",
    }
    return names.get(feature, feature.replace("_", " ").title())


def _get_intervention_key(feature: str, value) -> str | None:
    if feature == "salary_vs_market_ratio" and value < 0.9:
        return "salary_below_market"
    if feature == "manager_nps_score" and value < 5:
        return "low_manager_rating"
    if feature == "months_since_last_promotion" and value > 36:
        return "no_promotion_3_years"
    if feature == "avg_overtime_hours_monthly" and value > 40:
        return "high_overtime"
    return None


def _extract_attrition_features(employee_id: str, db_session) -> dict:
    """Extract attrition feature vector from DB."""
    # Abbreviated — full SQL in implementation
    return {
        "tenure_months": 24,
        "salary_vs_market_ratio": 0.85,
        "manager_nps_score": 4.0,
        "leave_days_used_ratio": 0.9,
        "absenteeism_rate": 0.05,
        "late_arrivals_count": 8,
        "months_since_last_promotion": 18,
        "peer_engagement_score": 3.5,
        "training_hours_ytd": 10,
        "avg_overtime_hours_monthly": 25,
        "satisfaction_survey_score": 3.2,
        "team_attrition_rate_ytd": 0.20,
        "pending_grievances_count": 0,
        "performance_band_numeric": 2,
    }
```

---

## AI Feature 5 & 6: Smart Analytics + Fairness Layer

```python
# ai/nlq_analytics.py
from openai import AsyncOpenAI
import json

client = AsyncOpenAI()

HRMS_SCHEMA_CONTEXT = """
Tables available: employees, attendance_records, payroll_records, leave_requests,
performance_reviews, job_applications, departments, branches.
tenant_id filtering is ALWAYS required. Date functions use PostgreSQL syntax.
"""

async def natural_language_to_chart(
    query: str,
    tenant_id: str,
    db_session,
) -> dict:
    """Convert natural language HR query to chart data."""

    # Step 1: LLM generates SQL
    sql_prompt = f"""
    You are a PostgreSQL expert for an HRMS database.
    Schema: {HRMS_SCHEMA_CONTEXT}
    Tenant ID: {tenant_id} (MUST be in every WHERE clause)

    Convert this HR analytics question to a safe, read-only PostgreSQL SELECT query.
    Return ONLY valid JSON: {{"sql": "...", "chart_type": "bar|line|pie|scatter", "title": "..."}}

    Question: {query}
    """

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": sql_prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )

    parsed = json.loads(response.choices[0].message.content)
    sql = parsed["sql"]

    # Step 2: Validate SQL is safe (read-only, has tenant_id)
    _validate_sql_safety(sql, tenant_id)

    # Step 3: Execute
    result = db_session.execute(sql).fetchall()
    data = [dict(row._mapping) for row in result]

    return {
        "chart_type": parsed["chart_type"],
        "title": parsed["title"],
        "data": data,
        "sql_generated": sql,
        "row_count": len(data),
    }


def _validate_sql_safety(sql: str, tenant_id: str):
    """Ensure generated SQL is safe for execution."""
    sql_upper = sql.upper().strip()

    forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "TRUNCATE", "ALTER",
                 "CREATE", "GRANT", "REVOKE", "EXEC", "--", "/*"]
    for keyword in forbidden:
        if keyword in sql_upper:
            raise ValueError(f"Forbidden SQL operation: {keyword}")

    if "SELECT" not in sql_upper:
        raise ValueError("Only SELECT queries are permitted")

    if tenant_id not in sql:
        raise ValueError("Query must filter by tenant_id")


# ai/fairness_monitor.py
def generate_monthly_fairness_report(tenant_id: str, month: int, year: int, db_session) -> dict:
    """Generate monthly AI fairness report per demographic group."""

    # AI hiring decisions vs actual outcomes
    hiring_fairness = db_session.execute("""
        SELECT
            e.gender,
            COUNT(ja.id) AS total_scored,
            AVG(ja.ai_score) AS avg_ai_score,
            COUNT(ja.id) FILTER (WHERE ja.stage = 'hired') AS hired_count,
            COUNT(ja.id) FILTER (WHERE ja.stage = 'rejected') AS rejected_count,
            ROUND(
                COUNT(ja.id) FILTER (WHERE ja.stage = 'hired') * 100.0
                / NULLIF(COUNT(ja.id), 0), 2
            ) AS hire_rate_pct
        FROM job_applications ja
        JOIN employees e ON e.id = ja.candidate_employee_id
        WHERE ja.tenant_id = :tenant_id
          AND ja.ai_scored_at >= date_trunc('month', :period)
          AND ja.ai_scored_at < date_trunc('month', :period) + INTERVAL '1 month'
        GROUP BY e.gender
    """, {"tenant_id": tenant_id, "period": f"{year}-{month:02d}-01"}).fetchall()

    # Attrition prediction accuracy by gender
    attrition_accuracy = db_session.execute("""
        SELECT
            e.gender,
            AVG(CASE WHEN ad.predicted_tier = 'high' OR ad.predicted_tier = 'critical'
                     AND e.lifecycle_status IN ('terminated', 'resigned')
                THEN 1.0 ELSE 0.0 END) AS prediction_accuracy
        FROM ai_decisions ad
        JOIN employees e ON e.resource_id = e.id::text
        WHERE ad.tenant_id = :tenant_id
          AND ad.model_type = 'attrition'
        GROUP BY e.gender
    """, {"tenant_id": tenant_id}).fetchall()

    return {
        "report_period": f"{year}-{month:02d}",
        "hiring_fairness": [dict(r._mapping) for r in hiring_fairness],
        "attrition_prediction_fairness": [dict(r._mapping) for r in attrition_accuracy],
        "generated_at": pd.Timestamp.now().isoformat(),
    }
```

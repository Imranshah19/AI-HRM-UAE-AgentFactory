"""
AI-HRMS — CV Scoring Engine (offline, no external API).

Works entirely on pattern matching, keyword intersection, and simple NLP heuristics.
No NLTK, spaCy, or cloud APIs required — runs with only stdlib + pdfplumber + python-docx.
"""

from __future__ import annotations

import io
import logging
import math
import os
import re
import tempfile
import urllib.request
from dataclasses import dataclass, field
from datetime    import datetime
from typing      import Optional

logger = logging.getLogger(__name__)


# ─── Data containers ─────────────────────────────────────────────────────────

@dataclass
class CVData:
    raw_text:         str
    skills:           list[str]        = field(default_factory=list)
    experience_years: float            = 0.0
    education_level:  str              = "unknown"   # phd/masters/bachelors/diploma/other
    current_title:    Optional[str]    = None
    summary:          Optional[str]    = None
    detected_name:    Optional[str]    = None


@dataclass
class ScoringResult:
    score:            float
    skills_matched:   list[str]
    skills_missing:   list[str]
    skills_score:     float
    experience_score: float
    title_relevance:  float
    education_score:  float
    explanation:      str
    bias_flags:       list[str]
    scored_at:        datetime = field(default_factory=datetime.utcnow)


# ─── Skill dictionaries ───────────────────────────────────────────────────────

# Common tech skills + normalisation aliases
_SKILL_ALIASES: dict[str, list[str]] = {
    "python":       ["python3", "py"],
    "javascript":   ["js", "node.js", "nodejs", "node"],
    "typescript":   ["ts"],
    "react":        ["react.js", "reactjs"],
    "fastapi":      ["fast api"],
    "django":       [],
    "flask":        [],
    "sql":          ["mysql", "postgres", "postgresql", "sqlite", "mssql", "oracle"],
    "postgresql":   ["postgres", "psql"],
    "mongodb":      ["mongo"],
    "docker":       [],
    "kubernetes":   ["k8s"],
    "aws":          ["amazon web services", "s3", "ec2", "lambda", "rds"],
    "azure":        ["microsoft azure"],
    "gcp":          ["google cloud", "bigquery"],
    "git":          ["github", "gitlab", "bitbucket"],
    "linux":        ["unix", "bash", "shell"],
    "java":         [],
    "c#":           ["csharp", "dotnet", ".net"],
    "php":          [],
    "golang":       ["go lang"],
    "rust":         [],
    "machine learning": ["ml", "sklearn", "scikit-learn", "tensorflow", "pytorch", "keras"],
    "deep learning": ["neural network", "cnn", "rnn", "lstm"],
    "nlp":          ["natural language processing", "transformers", "bert"],
    "data science": ["data analysis", "data analytics", "pandas", "numpy"],
    "power bi":     ["powerbi"],
    "excel":        ["ms excel", "microsoft excel"],
    "hr":           ["human resources", "hris", "hcm"],
    "accounting":   ["accounts", "bookkeeping", "ledger", "sap"],
    "marketing":    ["digital marketing", "seo", "sem", "google ads"],
    "sales":        ["business development", "crm"],
    "project management": ["pmp", "agile", "scrum", "jira", "kanban"],
}

# Reverse lookup: alias → canonical skill
_ALIAS_MAP: dict[str, str] = {}
for _canonical, _aliases in _SKILL_ALIASES.items():
    _ALIAS_MAP[_canonical] = _canonical
    for _alias in _aliases:
        _ALIAS_MAP[_alias.lower()] = _canonical


# ─── CV Text Extraction ───────────────────────────────────────────────────────

def extract_cv_text(file_url: str) -> str:
    """
    Download CV file from URL and extract raw text.
    Supports PDF (pdfplumber) and DOCX (python-docx).
    Falls back to plain text extraction if neither is available.
    """
    # Download file
    try:
        if file_url.startswith(("http://", "https://")):
            with urllib.request.urlopen(file_url, timeout=15) as resp:
                raw_bytes = resp.read()
        elif file_url.startswith("/"):
            with open(file_url, "rb") as f:
                raw_bytes = f.read()
        else:
            with open(file_url, "rb") as f:
                raw_bytes = f.read()
    except Exception as exc:
        logger.warning("Failed to download CV from %s: %s", file_url, exc)
        return ""

    ext = os.path.splitext(file_url.lower())[1]
    return _extract_text_from_bytes(raw_bytes, ext)


def _extract_text_from_bytes(raw_bytes: bytes, ext: str) -> str:
    if ext == ".pdf":
        return _extract_pdf(raw_bytes)
    elif ext in (".docx", ".doc"):
        return _extract_docx(raw_bytes)
    else:
        # Attempt UTF-8 decode
        try:
            return raw_bytes.decode("utf-8", errors="replace")
        except Exception:
            return ""


def _extract_pdf(raw_bytes: bytes) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n".join(text_parts)
    except ImportError:
        logger.warning("pdfplumber not installed; cannot parse PDF")
        return ""
    except Exception as exc:
        logger.warning("PDF extraction failed: %s", exc)
        return ""


def _extract_docx(raw_bytes: bytes) -> str:
    try:
        from docx import Document
        doc   = Document(io.BytesIO(raw_bytes))
        lines = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(lines)
    except ImportError:
        logger.warning("python-docx not installed; cannot parse DOCX")
        return ""
    except Exception as exc:
        logger.warning("DOCX extraction failed: %s", exc)
        return ""


# ─── CV Parsing ───────────────────────────────────────────────────────────────

# Regex patterns
_YEARS_EXP_PATTERNS = [
    r"(\d+)\+?\s*years?\s+(?:of\s+)?(?:work\s+)?experience",
    r"experience\s*[:\-–]?\s*(\d+)\+?\s*years?",
    r"(\d+)\s*(?:yrs?|years?)\s+(?:of\s+)?(?:professional\s+)?experience",
    r"(\d+)\s*to\s*(\d+)\s*years?\s+experience",
]

_EDU_LEVELS = {
    "phd":       ["phd", "ph.d", "doctorate", "doctoral"],
    "masters":   ["master", "msc", "m.sc", "mba", "m.b.a", "m.eng", "ms ", "m.s."],
    "bachelors": ["bachelor", "bsc", "b.sc", "be ", "b.e.", "bs ", "b.s.", "beng",
                  "b.eng", "undergraduate", "hons"],
    "diploma":   ["diploma", "associate", "a.a.", "a.s.", "certification", "certificate"],
}

_TITLE_KEYWORDS = [
    "engineer", "developer", "analyst", "manager", "designer", "architect",
    "specialist", "consultant", "lead", "senior", "junior", "intern",
    "officer", "executive", "director", "coordinator", "supervisor",
    "scientist", "researcher", "administrator",
]

# Bias-indicating patterns (for flagging only, NOT used in scoring)
_BIAS_PATTERNS = [
    (r"\b(male|female|man|woman|mr\.|mrs\.|miss)\b", "gender indicator"),
    (r"\baged?\s+\d+\b",                             "age mention"),
    (r"\bborn\s+in\s+\d{4}\b",                      "birth year"),
    (r"\bphoto\s+attached\b",                        "photo reference"),
    (r"\bmarried|single|divorced\b",                 "marital status"),
    (r"\bnationality\s*:\s*\w+",                     "nationality indicator"),
]


def parse_cv_sections(cv_text: str) -> CVData:
    """
    Parse raw CV text into structured CVData.
    Uses regex + keyword heuristics — no ML required.
    """
    text_lower = cv_text.lower()

    # 1. Skills detection
    skills = _detect_skills(text_lower)

    # 2. Experience years
    exp_years = _detect_experience_years(cv_text)

    # 3. Education level
    edu = _detect_education(text_lower)

    # 4. Current title (look for job title keywords near top of CV)
    title = _detect_current_title(cv_text)

    # 5. Summary (first paragraph-like block)
    summary = _extract_summary(cv_text)

    return CVData(
        raw_text         = cv_text,
        skills           = skills,
        experience_years = exp_years,
        education_level  = edu,
        current_title    = title,
        summary          = summary,
    )


def _detect_skills(text_lower: str) -> list[str]:
    found = set()
    for alias, canonical in _ALIAS_MAP.items():
        # Word-boundary match to avoid "java" matching "javascript" etc.
        pattern = r"(?<!\w)" + re.escape(alias) + r"(?!\w)"
        if re.search(pattern, text_lower):
            found.add(canonical)
    return sorted(found)


def _detect_experience_years(text: str) -> float:
    for pattern in _YEARS_EXP_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            groups = [g for g in m.groups() if g is not None]
            nums   = [float(g) for g in groups if g.isdigit()]
            if nums:
                return sum(nums) / len(nums)  # average if range given
    # Fallback: count year spans in employment history
    spans  = re.findall(r"(\d{4})\s*[-–]\s*(\d{4}|present|current|now)", text, re.IGNORECASE)
    total  = 0.0
    import datetime as _dt
    this_year = _dt.date.today().year
    for start, end in spans:
        try:
            s = int(start)
            e = this_year if end.lower() in ("present", "current", "now") else int(end)
            if 1980 <= s <= this_year and s <= e:
                total += e - s
        except ValueError:
            pass
    return min(total, 40.0)


def _detect_education(text_lower: str) -> str:
    for level, keywords in _EDU_LEVELS.items():
        for kw in keywords:
            if kw in text_lower:
                return level
    return "other"


def _detect_current_title(text: str) -> Optional[str]:
    """Extract the most prominent job title from near the top of the CV."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    # Check first 20 lines for title keywords
    for line in lines[:20]:
        line_lower = line.lower()
        for kw in _TITLE_KEYWORDS:
            if kw in line_lower and len(line) < 80:
                return line
    return None


def _extract_summary(text: str) -> Optional[str]:
    """Extract the professional summary/objective section."""
    markers = [
        r"(?:professional\s+)?(?:summary|profile|objective|about\s+me)\s*[:\n]",
        r"career\s+(?:summary|objective)\s*[:\n]",
    ]
    for marker in markers:
        m = re.search(marker, text, re.IGNORECASE)
        if m:
            start  = m.end()
            chunk  = text[start:start + 600].strip()
            # Stop at next section heading (all-caps line or double newline)
            stop   = re.search(r"\n\s*\n|\n[A-Z][A-Z\s]{5,}\n", chunk)
            return chunk[:stop.start()].strip() if stop else chunk[:300].strip()
    return None


# ─── CV Scoring ───────────────────────────────────────────────────────────────

def score_cv_against_job(
    cv_data:     CVData,
    job_title:   str,
    required_skills: list[str],
    experience_min:  int,
    experience_max:  Optional[int],
    description: str = "",
) -> ScoringResult:
    """
    Score a parsed CV against job requirements.
    Returns a ScoringResult with score 0-100 and human-readable explanation.

    Scoring breakdown:
      - Skills match:    40 points max
      - Experience:      30 points max
      - Title relevance: 20 points max
      - Education:       10 points max
    """
    # Normalise job skills to canonical form
    req_skills_norm = _normalise_skills(required_skills)
    cv_skills_norm  = set(cv_data.skills)

    # 1. Skills (40 pts)
    if req_skills_norm:
        matched  = req_skills_norm & cv_skills_norm
        missing  = req_skills_norm - cv_skills_norm
        skills_score = (len(matched) / len(req_skills_norm)) * 40
    else:
        matched  = set()
        missing  = set()
        skills_score = 20.0  # no requirements → half score

    # 2. Experience (30 pts)
    exp_score = _score_experience(cv_data.experience_years, experience_min, experience_max)

    # 3. Title relevance (20 pts)
    title_score = _score_title(cv_data.current_title, cv_data.raw_text, job_title, description)

    # 4. Education (10 pts)
    edu_score = _score_education(cv_data.education_level)

    total = round(min(100.0, skills_score + exp_score + title_score + edu_score), 1)

    # Human-readable explanation
    matched_list  = sorted(matched)
    missing_list  = sorted(missing)
    explanation   = _build_explanation(
        total, matched_list, missing_list, skills_score,
        cv_data.experience_years, experience_min, experience_max,
        cv_data.current_title, job_title, title_score,
        cv_data.education_level, edu_score,
    )

    bias_flags = detect_bias_flags(cv_data)

    return ScoringResult(
        score            = total,
        skills_matched   = matched_list,
        skills_missing   = missing_list,
        skills_score     = round(skills_score, 1),
        experience_score = round(exp_score, 1),
        title_relevance  = round(title_score, 1),
        education_score  = round(edu_score, 1),
        explanation      = explanation,
        bias_flags       = bias_flags,
    )


def _normalise_skills(skills: list[str]) -> set[str]:
    result = set()
    for s in skills:
        norm = s.strip().lower()
        canonical = _ALIAS_MAP.get(norm, norm)
        result.add(canonical)
    return result


def _score_experience(years: float, min_req: int, max_req: Optional[int]) -> float:
    """30 pts max. Perfect if within range; partial if close."""
    if years <= 0:
        return 0.0
    if years >= min_req:
        if max_req is None or years <= max_req:
            return 30.0  # within required range
        # Over-experienced (soft penalty)
        excess = years - max_req
        return max(20.0, 30.0 - excess * 1.5)
    # Under-experienced
    ratio = years / max(1, min_req)
    return round(ratio * 25, 1)  # max 25 if slightly under


def _score_title(
    cv_title: Optional[str],
    cv_text:  str,
    job_title: str,
    description: str,
) -> float:
    """20 pts max. Keyword overlap between job title and CV title / text."""
    if not cv_title and not cv_text:
        return 5.0

    job_words = set(re.findall(r"\b\w{3,}\b", job_title.lower()))
    job_words -= {"and", "the", "for", "with", "of", "in", "at"}

    if not job_words:
        return 10.0

    # Check CV title
    matched_in_title = 0
    if cv_title:
        cv_title_words = set(re.findall(r"\b\w{3,}\b", cv_title.lower()))
        matched_in_title = len(job_words & cv_title_words)

    # Check full text
    text_lower = cv_text.lower()
    matched_in_text = sum(1 for w in job_words if w in text_lower)

    title_ratio = matched_in_title / len(job_words) if job_words else 0
    text_ratio  = matched_in_text  / len(job_words) if job_words else 0

    # Weight title match higher
    score = min(20.0, title_ratio * 15 + text_ratio * 8)
    return round(score, 1)


def _score_education(level: str) -> float:
    """10 pts max."""
    mapping = {
        "phd":       10.0,
        "masters":   9.0,
        "bachelors": 8.0,
        "diploma":   5.0,
        "other":     3.0,
        "unknown":   3.0,
    }
    return mapping.get(level, 3.0)


def _build_explanation(
    total:          float,
    matched:        list[str],
    missing:        list[str],
    skills_score:   float,
    exp_years:      float,
    exp_min:        int,
    exp_max:        Optional[int],
    cv_title:       Optional[str],
    job_title:      str,
    title_score:    float,
    edu_level:      str,
    edu_score:      float,
) -> str:
    parts = [f"Score {total}/100:"]

    # Skills
    if matched:
        top_matched = ", ".join(matched[:6])
        parts.append(
            f"{len(matched)} skill(s) matched ({top_matched}"
            + (", …" if len(matched) > 6 else "") + ")"
        )
    else:
        parts.append("no required skills matched")

    if missing:
        top_missing = ", ".join(missing[:4])
        parts.append(
            f"missing: {top_missing}" + (", …" if len(missing) > 4 else "")
        )

    # Experience
    exp_range = f"{exp_min}–{exp_max}yr" if exp_max else f"{exp_min}+yr"
    parts.append(f"{exp_years:.0f}yr experience (required {exp_range})")

    # Title
    if cv_title:
        parts.append(f"current title: {cv_title[:50]}")
    elif title_score < 8:
        parts.append("title relevance: low")

    # Education
    if edu_level not in ("unknown", "other"):
        parts.append(f"education: {edu_level}")

    return "; ".join(parts)


# ─── Bias Detection ───────────────────────────────────────────────────────────

def detect_bias_flags(cv_data: CVData) -> list[str]:
    """
    Detect potential bias indicators in CV text.
    These are logged for HR awareness but NEVER used in scoring.
    """
    flags  = []
    sample = cv_data.raw_text[:3000].lower()
    for pattern, label in _BIAS_PATTERNS:
        if re.search(pattern, sample, re.IGNORECASE):
            flags.append(label)
    return flags

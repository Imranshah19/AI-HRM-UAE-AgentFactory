"""
AI-HRMS — HR Knowledge Base (TF-IDF powered, no external API).

Stores HR policy chunks (Pakistan labor law, FBR tax, EOBI, leave policies).
Uses sklearn TF-IDF for similarity search; falls back to keyword overlap.
"""

import re
from dataclasses import dataclass
from typing import Optional

# ─── Optional sklearn ─────────────────────────────────────────────────────────
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ─── Built-in Pakistan HR knowledge ──────────────────────────────────────────

BUILTIN_DOCS: dict[str, str] = {

"fbr_income_tax": """
FBR Income Tax Slabs 2024-2025 (Salaried Individuals):
- Annual income up to PKR 600,000: No tax (0%)
- PKR 600,001 to PKR 1,200,000: 5% of amount exceeding PKR 600,000
- PKR 1,200,001 to PKR 2,400,000: PKR 30,000 + 15% of amount exceeding PKR 1,200,000
- PKR 2,400,001 to PKR 3,600,000: PKR 210,000 + 25% of amount exceeding PKR 2,400,000
- PKR 3,600,001 to PKR 6,000,000: PKR 510,000 + 30% of amount exceeding PKR 3,600,000
- Above PKR 6,000,000: PKR 1,230,000 + 35% of amount exceeding PKR 6,000,000

Monthly tax calculation: Annualize the monthly salary, find the slab, divide annual tax by 12.
Example: Monthly salary PKR 100,000 → Annual PKR 1,200,000 → Tax = PKR 30,000/year → PKR 2,500/month.
Super tax applies to high earners (above PKR 150M annual income).
FBR tax is deducted at source by employer under Section 149 of Income Tax Ordinance 2001.
""",

"eobi": """
EOBI (Employees Old-Age Benefits Institution) Rules:
- Employer contribution: 5% of minimum wage per employee per month
- Employee contribution: 1% of wages (minimum PKR 10 per month)
- Current minimum wage (2024): PKR 37,000/month
- Employer monthly contribution per employee: PKR 1,850 (5% of 37,000)
- Employee monthly contribution: 1% of actual wages
- Registration mandatory for establishments with 5 or more employees
- Benefit: Monthly pension upon retirement (age 60 male, 55 female)
- Minimum pension: PKR 10,000/month (2024)
- Death grant: PKR 200,000 to nominee on employee death
- Invalidity pension for permanently disabled employees
EOBI registration number must appear on all payslips.
""",

"sessi": """
SESSI (Sindh Employees Social Security Institution):
- Applicable to establishments in Sindh with 10 or more employees
- Employee contribution: 1% of wages
- Employer contribution: 6% of wages
- Covers free medical treatment for insured employees and their families
- Maternity benefit: 100% of wages for 12 weeks
- Registration required within 30 days of reaching 10 employees
- SESSI card issued to registered employees
""",

"leave_entitlements": """
Leave Entitlements under Pakistan Law:
1. Annual / Earned Leave: 14 days per year after completing 1 year of continuous service
   (Factories Act 1934 / Industrial and Commercial Employment Ordinance 1968)
2. Casual Leave: 10 days per calendar year (full pay)
3. Sick Leave: 8–10 days per year (varies by province and sector)
4. Maternity Leave: 12 weeks (3 months) with full pay — Maternity Benefit Ordinance 1958
5. Paternity Leave: Not legally mandated; many companies offer 7–14 days voluntarily
6. Iddah Leave: 130 days for Muslim female employees on death of husband
7. Hajj Leave: Once in service lifetime, funded by employer (large organizations)
8. Compensatory Off: If worked on holiday/Sunday, entitled to compensatory leave

Carry forward: Annual leave can typically be carried forward; casual leave usually cannot.
Leave encashment: Unused annual leave may be encashed at end of service.
""",

"gratuity": """
Gratuity Policy (Pakistan):
- Mandatory for employees completing 3 or more years of continuous service
- Calculation formula: Last Basic Salary × (30/26) × Years of Service
  (30 days per month, 26 working days per month basis)
- Example: Basic PKR 50,000, 5 years service → 50,000 × (30/26) × 5 = PKR 288,462
- Payable on: Retirement, Resignation (after 5 years), Termination (without cause)
- Gratuity on termination for cause: May be forfeited (employer discretion)
- Tax treatment: First PKR 300,000 exempt from income tax; excess taxable
- Companies may also have provident fund instead of or in addition to gratuity
""",

"overtime_policy": """
Overtime Rules under Pakistan Labor Law:
- Overtime rate: 2× regular hourly wage for hours beyond regular shift
- Night shift premium: 25% additional on regular wages
- Maximum overtime: 2 hours per day, maximum 10 hours per week
- Overtime must be compensated within the same wage period (monthly)
- No employee can be forced to work overtime without consent
- Female employees: Cannot work after 8 PM without written consent
- Overtime records must be maintained in prescribed register
""",

"termination_notice": """
Notice Period and Termination (Pakistan):
- Standard notice period: 1 month for permanent employees (or as per contract)
- For non-permanent / probationary: Notice period as specified in appointment letter
- WPPF (Workers Profit Participation Fund): 5% of annual profits distributed among workers
  (applicable to companies with 20+ workers and profits above PKR 100,000)
- Retrenchment: 1 month notice per year of service (Industrial Relations Act)
- Wrongful termination: Employee may file complaint with Labour Court within 3 years
- End of service payment: Notice pay + gratuity (if applicable) + leave encashment
""",

"probation": """
Probation Period Policy:
- Standard probation period in Pakistan: 3–6 months (varies by employer)
- During probation: Either party may terminate with short notice (usually 7–30 days)
- Probationary employees: Not entitled to annual leave until confirmed
- Benefits during probation: Basic salary, EOBI contribution by employer
- Confirmation: After successful probation, employee receives confirmation letter
- Extension of probation: Allowed once (typically for another 3 months)
- SESSI and other statutory contributions: Apply from day 1 regardless of probation
""",

"hr_procedures": """
Common HR Procedures:
1. Joining Formalities: CNIC copy, educational certificates, experience letters, 2 photos, bank account
2. Payslip components: Basic pay, House Rent Allowance (HRA), Medical Allowance, Transport, deductions
3. Performance Review cycle: Typically annual (Jan-Dec or Jul-Jun) with mid-year check-in
4. Leave application: Submit via HRMS; approval from direct manager; > 3 days may need HR approval
5. Loan policy: Many companies offer salary loans up to 3× monthly salary; repaid over 6–12 months
6. Travel claims: Submit within 7 days of travel with receipts; approved by manager
7. Training nomination: Apply through Learning & Development portal; manager approval required
8. Resignation: Submit formal letter to manager + HR; serve notice period unless waived
""",

}


@dataclass
class KBResult:
    chunk: str
    score: float
    source: str


class HRKnowledgeBase:
    """TF-IDF powered HR knowledge base. No external API required."""

    def __init__(self) -> None:
        self._chunks: list[str] = []
        self._sources: list[str] = []
        self._vectorizer: Optional[object] = None
        self._matrix = None
        self._build_from_builtin()

    def _build_from_builtin(self) -> None:
        """Load all built-in documents into the chunk store."""
        for source, text in BUILTIN_DOCS.items():
            for chunk in self._chunk_text(text, chunk_size=350):
                self._chunks.append(chunk)
                self._sources.append(source)
        self._fit()

    def _chunk_text(self, text: str, chunk_size: int = 350) -> list[str]:
        """Split text into overlapping chunks of ~chunk_size words."""
        sentences = re.split(r'(?<=[.!?])\s+|\n+', text.strip())
        chunks: list[str] = []
        current = ""
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            if len(current.split()) + len(sent.split()) <= chunk_size:
                current = (current + " " + sent).strip()
            else:
                if current:
                    chunks.append(current)
                current = sent
        if current:
            chunks.append(current)
        return chunks or [text[:500]]

    def load_documents(self, texts: list[tuple[str, str]]) -> None:
        """Add external documents: list of (source_name, text)."""
        for source, text in texts:
            for chunk in self._chunk_text(text):
                self._chunks.append(chunk)
                self._sources.append(source)
        self._fit()

    def _fit(self) -> None:
        if not self._chunks:
            return
        if SKLEARN_AVAILABLE:
            self._vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=5000,
            )
            self._matrix = self._vectorizer.fit_transform(self._chunks)
        # else: keyword fallback used in search()

    def search(self, query: str, top_k: int = 3) -> list[KBResult]:
        """Return top-k most relevant KB chunks for the query."""
        if not self._chunks:
            return []

        if SKLEARN_AVAILABLE and self._vectorizer is not None:
            return self._tfidf_search(query, top_k)
        return self._keyword_search(query, top_k)

    def _tfidf_search(self, query: str, top_k: int) -> list[KBResult]:
        q_vec  = self._vectorizer.transform([query])  # type: ignore[union-attr]
        sims   = cosine_similarity(q_vec, self._matrix).flatten()  # type: ignore[arg-type]
        top_i  = sims.argsort()[::-1][:top_k]
        return [
            KBResult(chunk=self._chunks[i], score=float(sims[i]), source=self._sources[i])
            for i in top_i
            if sims[i] > 0.01
        ]

    def _keyword_search(self, query: str, top_k: int) -> list[KBResult]:
        q_words = set(re.findall(r'\w+', query.lower()))
        scored: list[tuple[float, int]] = []
        for i, chunk in enumerate(self._chunks):
            chunk_words = set(re.findall(r'\w+', chunk.lower()))
            overlap = len(q_words & chunk_words) / max(len(q_words), 1)
            scored.append((overlap, i))
        scored.sort(reverse=True)
        return [
            KBResult(chunk=self._chunks[i], score=s, source=self._sources[i])
            for s, i in scored[:top_k]
            if s > 0
        ]


# ─── Singleton ────────────────────────────────────────────────────────────────

_kb: HRKnowledgeBase | None = None


def get_knowledge_base() -> HRKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = HRKnowledgeBase()
    return _kb

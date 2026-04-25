"""
AI-HRMS — Attrition Prediction Model.

Uses XGBoost when available and trained; falls back to rule-based scoring.
No external API needed — fully offline.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model_data", "attrition_model.json")

# ── Optional ML deps ──────────────────────────────────────────────────────────
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

RiskTier = Literal["Low", "Medium", "High", "Critical"]

# ─── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class AttritionResult:
    risk_score:          float          # 0–100
    risk_tier:           RiskTier
    top_risk_factors:    list[dict]     # [{factor, impact, direction}]
    recommended_actions: list[str]
    confidence:          float          # 0–1
    model_type:          str = "rule_based"


def _tier(score: float) -> RiskTier:
    if score >= 80: return "Critical"
    if score >= 60: return "High"
    if score >= 30: return "Medium"
    return "Low"


# ─── Rule weights ─────────────────────────────────────────────────────────────

RULE_WEIGHTS: dict[str, tuple[float, str, str]] = {
    # feature_key: (max_points, human_label, direction_note)
    "tenure_short":         (20, "Short tenure",          "New employees have higher departure risk"),
    "absent_rate_30d":      (18, "High absenteeism",       "Frequent absences correlate with disengagement"),
    "perf_rating_low":      (18, "Low performance rating", "Poor ratings often precede resignation"),
    "salary_below_avg":     (15, "Below-average salary",   "Below-market pay motivates job searching"),
    "days_since_promotion": (12, "No recent promotion",    "Stagnation increases flight risk"),
    "perf_trend_negative":  (10, "Declining performance",  "Declining trajectory signals dissatisfaction"),
    "salary_growth_low":    (10, "Low salary growth",      "Flat compensation growth drives attrition"),
    "overtime_high":        (9,  "Excessive overtime",     "Chronic overwork leads to burnout"),
    "dept_turnover":        (8,  "High dept turnover",     "Peer attrition creates contagion risk"),
    "manager_changes":      (6,  "Manager instability",    "Frequent manager changes reduce retention"),
    "training_incomplete":  (5,  "Low training completion","Disengaged employees skip training"),
    "leave_utilization":    (4,  "High leave usage",       "High leave use may indicate work dissatisfaction"),
    "pending_leaves":       (3,  "Many pending leaves",    "Queued leave requests signal planned absence"),
}

ACTIONS_BY_FACTOR: dict[str, str] = {
    "tenure_short":         "Assign onboarding buddy and schedule 30/60/90-day check-ins",
    "absent_rate_30d":      "Schedule 1:1 with manager to discuss attendance concerns",
    "perf_rating_low":      "Create performance improvement plan with clear milestones",
    "salary_below_avg":     "Review salary against market benchmarks; consider adjustment",
    "days_since_promotion": "Evaluate eligibility for promotion or role expansion",
    "perf_trend_negative":  "Provide coaching and additional training resources",
    "salary_growth_low":    "Review compensation history; schedule salary discussion",
    "overtime_high":        "Audit workload distribution; consider additional headcount",
    "dept_turnover":        "Conduct stay interviews within the department",
    "manager_changes":      "Assign stable manager relationship; clarify reporting lines",
    "training_incomplete":  "Encourage training participation; link to career path",
    "leave_utilization":    "Conduct wellness check-in; review work-life balance",
    "pending_leaves":       "Clear leave backlog; ensure approvals are timely",
}


# ─── Model class ──────────────────────────────────────────────────────────────

class AttritionModel:
    def __init__(self) -> None:
        self._xgb_model = None
        self._feature_names: list[str] = []
        self._load_model()

    def _load_model(self) -> None:
        if not XGBOOST_AVAILABLE or not NUMPY_AVAILABLE:
            return
        if not os.path.exists(MODEL_PATH):
            return
        try:
            self._xgb_model = xgb.XGBClassifier()
            self._xgb_model.load_model(MODEL_PATH)
            meta_path = MODEL_PATH.replace(".json", "_meta.json")
            if os.path.exists(meta_path):
                with open(meta_path) as f:
                    meta = json.load(f)
                self._feature_names = meta.get("feature_names", [])
            logger.info("Attrition XGBoost model loaded from %s", MODEL_PATH)
        except Exception as e:
            logger.warning("Failed to load attrition model: %s — using rule-based", e)
            self._xgb_model = None

    def predict(self, features: dict[str, float]) -> AttritionResult:
        if self._xgb_model is not None and NUMPY_AVAILABLE:
            return self._ml_predict(features)
        return self.rule_based_predict(features)

    def _ml_predict(self, features: dict[str, float]) -> AttritionResult:
        try:
            import numpy as np
            feat_order = self._feature_names or list(RULE_WEIGHTS.keys())
            vec = np.array([[features.get(k, 0.0) for k in feat_order]], dtype=np.float32)
            prob = float(self._xgb_model.predict_proba(vec)[0][1])
            score = prob * 100
            # Build factor importances from feature importances
            importances = self._xgb_model.feature_importances_
            factors = [
                {
                    "factor": feat_order[i],
                    "impact": round(float(importances[i]) * features.get(feat_order[i], 0), 3),
                    "direction": RULE_WEIGHTS.get(feat_order[i], (0, feat_order[i], ""))[2],
                }
                for i in range(len(feat_order))
            ]
            factors.sort(key=lambda x: x["impact"], reverse=True)
            top = factors[:3]
            actions = [ACTIONS_BY_FACTOR.get(f["factor"], "Review with HR") for f in top[:4]]
            return AttritionResult(
                risk_score=round(score, 1),
                risk_tier=_tier(score),
                top_risk_factors=top,
                recommended_actions=list(dict.fromkeys(actions)),
                confidence=0.82,
                model_type="xgboost",
            )
        except Exception as e:
            logger.warning("ML predict failed: %s — falling back to rules", e)
            return self.rule_based_predict(features)

    def rule_based_predict(self, features: dict[str, float]) -> AttritionResult:
        total_possible = sum(w for w, _, _ in RULE_WEIGHTS.values())
        scored: list[tuple[float, str, str, str]] = []

        for key, (max_pts, label, direction) in RULE_WEIGHTS.items():
            val = features.get(key, 0.0)
            pts = val * max_pts
            scored.append((pts, key, label, direction))

        scored.sort(reverse=True)
        raw_score = sum(p for p, *_ in scored)
        score = min(100.0, (raw_score / total_possible) * 100)

        top_factors = [
            {
                "factor": key,
                "label":  label,
                "impact": round(pts / total_possible, 3),
                "direction": direction,
            }
            for pts, key, label, direction in scored[:4]
            if pts > 0
        ]

        # Recommended actions from top risk factors
        actions: list[str] = []
        for f in top_factors[:4]:
            a = ACTIONS_BY_FACTOR.get(f["factor"])
            if a and a not in actions:
                actions.append(a)

        tier = _tier(score)
        if tier == "Critical" and "Schedule urgent meeting with HR and manager" not in actions:
            actions.insert(0, "Schedule urgent meeting with HR and manager")
        if tier in ("High", "Critical"):
            actions.append("Consider retention bonus or career development discussion")

        # Confidence based on data completeness
        filled = sum(1 for v in features.values() if v != 0.5)
        confidence = 0.55 + (filled / len(RULE_WEIGHTS)) * 0.30

        return AttritionResult(
            risk_score=round(score, 1),
            risk_tier=tier,
            top_risk_factors=top_factors[:3],
            recommended_actions=list(dict.fromkeys(actions))[:5],
            confidence=round(confidence, 2),
            model_type="rule_based",
        )

    def train(
        self,
        training_data: list[dict[str, float]],
        labels: list[int],
    ) -> None:
        """Train XGBoost classifier and save model."""
        if not XGBOOST_AVAILABLE or not NUMPY_AVAILABLE:
            raise RuntimeError("xgboost and numpy are required for training")
        import numpy as np

        feat_names = list(RULE_WEIGHTS.keys())
        X = np.array([[d.get(k, 0.0) for k in feat_names] for d in training_data], dtype=np.float32)
        y = np.array(labels, dtype=np.int32)

        model = xgb.XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            use_label_encoder=False,
            eval_metric="logloss",
        )
        model.fit(X, y)

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        model.save_model(MODEL_PATH)
        meta_path = MODEL_PATH.replace(".json", "_meta.json")
        with open(meta_path, "w") as f:
            json.dump({"feature_names": feat_names}, f)
        self._xgb_model = model
        self._feature_names = feat_names
        logger.info("Attrition model trained on %d samples and saved", len(labels))


# ─── Singleton ────────────────────────────────────────────────────────────────

_model: AttritionModel | None = None


def get_attrition_model() -> AttritionModel:
    global _model
    if _model is None:
        _model = AttritionModel()
    return _model

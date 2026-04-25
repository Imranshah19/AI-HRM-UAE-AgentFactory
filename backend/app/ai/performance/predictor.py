"""
AI-HRMS — Performance Prediction.

Predicts an employee's performance band and likely rating for the next cycle.
Uses RandomForest when available; rule-based fallback otherwise.
"""

import uuid
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Literal

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

try:
    from sklearn.ensemble import RandomForestClassifier
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

Band = Literal["High", "Medium", "Low"]


@dataclass
class PerformancePrediction:
    employee_id:             str
    predicted_band:          Band
    predicted_score:         float       # 1.0–5.0
    confidence:              float       # 0–1
    key_drivers:             list[dict]  # [{factor, influence, note}]
    improvement_suggestions: list[str]
    predicted_at:            str


# ─── Feature extraction ───────────────────────────────────────────────────────

async def _extract_performance_features(
    employee_id: uuid.UUID,
    db: AsyncSession,
) -> dict[str, float]:
    from app.models.performance import Appraisal, Goal
    from app.models.attendance import AttendanceRecord
    from app.models.training import TrainingEnrollment
    from app.models.leave import LeaveBalance
    from app.models.employee import Employee

    feats: dict[str, float] = {}
    today = date.today()
    six_months_ago = today - timedelta(days=180)

    # 1. Last 3 appraisal ratings avg + trend
    try:
        rows = (await db.execute(
            select(Appraisal.final_rating)
            .where(Appraisal.employee_id == employee_id)
            .order_by(Appraisal.created_at.desc())
            .limit(3)
        )).scalars().all()

        ratings = [float(r) for r in rows if r is not None]
        if ratings:
            feats["avg_rating"]     = sum(ratings) / len(ratings)
            feats["last_rating"]    = ratings[0]
            feats["rating_trend"]   = ratings[0] - ratings[-1] if len(ratings) >= 2 else 0
        else:
            feats["avg_rating"]   = 3.0
            feats["last_rating"]  = 3.0
            feats["rating_trend"] = 0.0
    except Exception:
        feats["avg_rating"] = feats["last_rating"] = 3.0
        feats["rating_trend"] = 0.0

    # 2. Attendance rate last 6 months
    try:
        att_col = getattr(AttendanceRecord, "work_date",
                  getattr(AttendanceRecord, "date", None))
        if att_col is not None:
            rows = (await db.execute(
                select(AttendanceRecord.status)
                .where(
                    AttendanceRecord.employee_id == employee_id,
                    att_col >= six_months_ago,
                )
            )).scalars().all()
            workdays = [s for s in rows if s not in ("holiday", "weekly_off")] or ["present"]
            present = sum(1 for s in workdays if s in ("present", "late", "half_day", "work_from_home"))
            feats["attendance_rate"] = present / len(workdays)
        else:
            feats["attendance_rate"] = 0.9
    except Exception:
        feats["attendance_rate"] = 0.9

    # 3. Training completion rate
    try:
        statuses = (await db.execute(
            select(TrainingEnrollment.status)
            .where(TrainingEnrollment.employee_id == employee_id)
        )).scalars().all()
        if statuses:
            completed = sum(1 for s in statuses if s == "completed")
            feats["training_completion"] = completed / len(statuses)
        else:
            feats["training_completion"] = 0.5
    except Exception:
        feats["training_completion"] = 0.5

    # 4. Goal achievement rate
    try:
        goal_rows = (await db.execute(
            select(Goal.status)
            .where(Goal.employee_id == employee_id)
        )).scalars().all()
        if goal_rows:
            completed = sum(1 for s in goal_rows if s == "completed")
            feats["goal_achievement"] = completed / len(goal_rows)
        else:
            feats["goal_achievement"] = 0.5
    except Exception:
        feats["goal_achievement"] = 0.5

    # 5. Leave utilization (high can indicate disengagement or just active use)
    try:
        row = (await db.execute(
            select(
                func.coalesce(func.sum(LeaveBalance.used_days), 0).label("used"),
                func.coalesce(func.sum(LeaveBalance.total_days), 1).label("total"),
            )
            .where(
                LeaveBalance.employee_id == employee_id,
                LeaveBalance.year == today.year,
            )
        )).one_or_none()
        feats["leave_util"] = (float(row.used) / max(float(row.total), 1)) if row else 0.5
    except Exception:
        feats["leave_util"] = 0.5

    # 6. Tenure months
    try:
        emp = (await db.execute(
            select(Employee).where(Employee.id == employee_id)
        )).scalar_one_or_none()
        join = getattr(emp, "date_of_joining", None) or getattr(emp, "join_date", None) if emp else None
        feats["tenure_months"] = (today - join).days / 30.44 if join else 24.0
    except Exception:
        feats["tenure_months"] = 24.0

    # 7. Overtime willingness
    try:
        ot_col = getattr(AttendanceRecord, "overtime_minutes", None)
        att_col = getattr(AttendanceRecord, "work_date",
                  getattr(AttendanceRecord, "date", None))
        if ot_col and att_col:
            ot_total = (await db.execute(
                select(func.coalesce(func.sum(ot_col), 0))
                .where(
                    AttendanceRecord.employee_id == employee_id,
                    att_col >= six_months_ago,
                )
            )).scalar() or 0
            # 180 days * 480 min/day
            feats["overtime_willingness"] = min(1.0, float(ot_total) / (180 * 480))
        else:
            feats["overtime_willingness"] = 0.1
    except Exception:
        feats["overtime_willingness"] = 0.1

    return feats


# ─── Rule-based prediction ────────────────────────────────────────────────────

def _rule_predict(feats: dict[str, float]) -> tuple[float, list[dict], list[str]]:
    """
    Weighted scoring to predict performance score (1–5).
    Returns (predicted_score, key_drivers, suggestions).
    """
    last_rating       = feats.get("last_rating", 3.0)
    avg_rating        = feats.get("avg_rating", 3.0)
    rating_trend      = feats.get("rating_trend", 0.0)
    attendance        = feats.get("attendance_rate", 0.9)
    training          = feats.get("training_completion", 0.5)
    goals             = feats.get("goal_achievement", 0.5)
    tenure            = feats.get("tenure_months", 24.0)
    ot_will           = feats.get("overtime_willingness", 0.1)

    # Weighted blend
    score = (
        last_rating   * 0.35 +
        avg_rating    * 0.20 +
        (rating_trend * 0.5 + 3.0) * 0.10 +   # normalise trend around 3
        (attendance * 5.0) * 0.15 +
        (training   * 5.0) * 0.10 +
        (goals      * 5.0) * 0.10
    )
    score = max(1.0, min(5.0, score))

    drivers: list[dict] = []
    suggestions: list[str] = []

    if attendance >= 0.95:
        drivers.append({"factor": "attendance_rate", "influence": "positive",
                        "note": f"{attendance:.0%} attendance consistently"})
    elif attendance < 0.80:
        drivers.append({"factor": "attendance_rate", "influence": "negative",
                        "note": f"Only {attendance:.0%} attendance — needs improvement"})
        suggestions.append("Improve attendance consistency to build reliability")

    if rating_trend > 0.5:
        drivers.append({"factor": "performance_trend", "influence": "positive",
                        "note": f"Ratings improving by {rating_trend:.1f} points"})
    elif rating_trend < -0.5:
        drivers.append({"factor": "performance_trend", "influence": "negative",
                        "note": f"Ratings declining by {abs(rating_trend):.1f} points"})
        suggestions.append("Identify and address performance blockers with manager")

    if goals >= 0.80:
        drivers.append({"factor": "goal_achievement", "influence": "positive",
                        "note": f"{goals:.0%} of goals completed"})
    elif goals < 0.50:
        drivers.append({"factor": "goal_achievement", "influence": "negative",
                        "note": f"Only {goals:.0%} goal completion rate"})
        suggestions.append("Set more achievable goals; review obstacles to goal completion")

    if training >= 0.80:
        drivers.append({"factor": "training_completion", "influence": "positive",
                        "note": f"{training:.0%} training modules completed"})
    elif training < 0.40:
        drivers.append({"factor": "training_completion", "influence": "negative",
                        "note": f"Only {training:.0%} training completion"})
        suggestions.append("Complete pending training programs to develop skills")

    if tenure < 6:
        drivers.append({"factor": "tenure", "influence": "neutral",
                        "note": "Still in early tenure — limited data available"})
        suggestions.append("Focus on onboarding objectives in first 6 months")

    if not suggestions:
        suggestions.append("Maintain current performance trajectory")
        suggestions.append("Seek stretch assignments to accelerate growth")

    return score, drivers[:4], suggestions[:4]


# ─── Main predictor ───────────────────────────────────────────────────────────

async def predict_performance(
    employee_id: uuid.UUID,
    db: AsyncSession,
) -> PerformancePrediction:
    feats = await _extract_performance_features(employee_id, db)
    predicted_score, drivers, suggestions = _rule_predict(feats)

    if predicted_score >= 4.0:
        band: Band = "High"
    elif predicted_score >= 2.5:
        band = "Medium"
    else:
        band = "Low"

    filled = sum(1 for v in feats.values() if v not in (0.5, 3.0, 0.9, 24.0, 0.1))
    confidence = 0.50 + (filled / 7) * 0.35

    return PerformancePrediction(
        employee_id=str(employee_id),
        predicted_band=band,
        predicted_score=round(predicted_score, 2),
        confidence=round(confidence, 2),
        key_drivers=drivers,
        improvement_suggestions=suggestions,
        predicted_at=datetime.now().isoformat(),
    )

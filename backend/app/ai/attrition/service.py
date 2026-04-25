"""
AI-HRMS — Attrition Prediction Service.

Orchestrates feature extraction → model prediction → caching → notifications.
"""

import json
import uuid
from datetime import datetime, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.attrition.feature_extractor import extract_employee_features
from app.ai.attrition.model import AttritionResult, get_attrition_model

logger = structlog.get_logger(__name__)

# Redis TTLs
_EMPLOYEE_TTL = 60 * 60 * 24      # 24 hours
_TENANT_TTL   = 60 * 60 * 6       # 6 hours


def _emp_cache_key(tenant_id: uuid.UUID, employee_id: uuid.UUID) -> str:
    return f"hrms:attrition:{tenant_id}:{employee_id}"


def _tenant_cache_key(tenant_id: uuid.UUID) -> str:
    return f"hrms:attrition:overview:{tenant_id}"


# ─── Single employee prediction ───────────────────────────────────────────────

async def predict_attrition(
    tenant_id: uuid.UUID,
    employee_id: uuid.UUID,
    db: AsyncSession,
    redis=None,
    force_refresh: bool = False,
) -> AttritionResult:
    """
    Predict attrition risk for one employee.
    Results are cached in Redis for 24 hours.
    Critical risk triggers an HR notification.
    """
    cache_key = _emp_cache_key(tenant_id, employee_id)

    # ── Cache hit ─────────────────────────────────────────────────────────────
    if redis and not force_refresh:
        try:
            cached = await redis.get(cache_key)
            if cached:
                data = json.loads(cached)
                return AttritionResult(**data)
        except Exception:
            pass

    # ── Extract features & predict ────────────────────────────────────────────
    features = await extract_employee_features(employee_id, tenant_id, db)
    model    = get_attrition_model()
    result   = model.predict(features)

    # ── Cache result ──────────────────────────────────────────────────────────
    if redis:
        try:
            payload = {
                "risk_score":          result.risk_score,
                "risk_tier":           result.risk_tier,
                "top_risk_factors":    result.top_risk_factors,
                "recommended_actions": result.recommended_actions,
                "confidence":          result.confidence,
                "model_type":          result.model_type,
            }
            await redis.setex(cache_key, _EMPLOYEE_TTL, json.dumps(payload))
        except Exception:
            pass

    # ── Critical risk → notify HR ─────────────────────────────────────────────
    if result.risk_tier == "Critical":
        try:
            await _notify_hr_critical(tenant_id, employee_id, result, db)
        except Exception as e:
            logger.warning("attrition.notify_hr_failed", error=str(e))

    return result


async def _notify_hr_critical(
    tenant_id: uuid.UUID,
    employee_id: uuid.UUID,
    result: AttritionResult,
    db: AsyncSession,
) -> None:
    from app.models.employee import Employee
    from app.api.v1.notifications.service import create_notification

    emp = (await db.execute(
        select(Employee).where(Employee.id == employee_id)
    )).scalar_one_or_none()
    if emp is None:
        return

    name = f"{emp.first_name} {emp.last_name}"
    top_factor = result.top_risk_factors[0].get("label", "multiple factors") if result.top_risk_factors else "multiple factors"

    # Find HR managers to notify
    from app.models.tenant import User, UserRole, Role
    hr_users = (await db.execute(
        select(User.id)
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, UserRole.role_id == Role.id)
        .where(
            User.tenant_id == tenant_id,
            Role.name.ilike("%hr%"),
        )
        .limit(5)
    )).scalars().all()

    for hr_user_id in hr_users:
        try:
            await create_notification(
                db=db,
                tenant_id=tenant_id,
                user_id=hr_user_id,
                title=f"Critical Attrition Risk: {name}",
                message=(
                    f"{name} has been flagged as Critical attrition risk "
                    f"(score: {result.risk_score:.0f}/100). "
                    f"Top factor: {top_factor}. Immediate action recommended."
                ),
                type="warning",
                action_url=f"/ai?tab=attrition&employee={employee_id}",
            )
        except Exception:
            pass


# ─── Tenant-wide overview ─────────────────────────────────────────────────────

async def get_tenant_attrition_overview(
    tenant_id: uuid.UUID,
    db: AsyncSession,
    redis=None,
) -> dict:
    """Run predictions for all active employees and return tier counts."""
    from app.models.employee import Employee

    cache_key = _tenant_cache_key(tenant_id)

    if redis:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception:
            pass

    employees = (await db.execute(
        select(Employee.id, Employee.first_name, Employee.last_name)
        .where(
            Employee.tenant_id == tenant_id,
            Employee.employment_status == "active",
        )
        .limit(200)
    )).fetchall()

    counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    high_risk: list[dict] = []

    for emp_id, fname, lname in employees:
        try:
            result = await predict_attrition(tenant_id, emp_id, db, redis)
            counts[result.risk_tier] += 1
            if result.risk_tier in ("High", "Critical"):
                top = result.top_risk_factors[0] if result.top_risk_factors else {}
                high_risk.append({
                    "id":         str(emp_id),
                    "name":       f"{fname} {lname}",
                    "score":      result.risk_score,
                    "tier":       result.risk_tier,
                    "top_factor": top.get("label", top.get("factor", "—")),
                })
        except Exception as e:
            logger.warning("overview.predict_failed", emp=str(emp_id), error=str(e))

    high_risk.sort(key=lambda x: x["score"], reverse=True)

    overview = {
        "total":              len(employees),
        "low_count":          counts["Low"],
        "medium_count":       counts["Medium"],
        "high_count":         counts["High"],
        "critical_count":     counts["Critical"],
        "high_risk_employees": high_risk[:10],
        "computed_at":        datetime.now(timezone.utc).isoformat(),
    }

    if redis:
        try:
            await redis.setex(cache_key, _TENANT_TTL, json.dumps(overview))
        except Exception:
            pass

    return overview

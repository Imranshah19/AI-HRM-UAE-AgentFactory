"""
AI-HRMS — Attrition Prediction API Router.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.core.redis import get_redis
from app.ai.attrition.service import get_tenant_attrition_overview, predict_attrition
from app.models.tenant import User

router = APIRouter(prefix="/ai/attrition", tags=["AI — Attrition"])


# ─── Response schemas ─────────────────────────────────────────────────────────

class RiskFactor(BaseModel):
    factor:    str
    label:     str = ""
    impact:    float
    direction: str

    model_config = ConfigDict(from_attributes=True)


class AttritionResultResponse(BaseModel):
    employee_id:         str
    risk_score:          float
    risk_tier:           str
    top_risk_factors:    list[RiskFactor]
    recommended_actions: list[str]
    confidence:          float
    model_type:          str

    model_config = ConfigDict(from_attributes=True)


class HighRiskEmployee(BaseModel):
    id:         str
    name:       str
    score:      float
    tier:       str
    top_factor: str

    model_config = ConfigDict(from_attributes=True)


class AttritionOverviewResponse(BaseModel):
    total:                int
    low_count:            int
    medium_count:         int
    high_count:           int
    critical_count:       int
    high_risk_employees:  list[HighRiskEmployee]
    computed_at:          str | None = None


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/overview",
    response_model=AttritionOverviewResponse,
    dependencies=[require_permission("employees", "read")],
)
async def get_attrition_overview(
    db:      AsyncSession = Depends(get_db),
    current: User         = Depends(get_current_user),
    redis                 = Depends(get_redis),
):
    """Tenant-wide attrition risk summary (cached 6h)."""
    overview = await get_tenant_attrition_overview(
        tenant_id=current.tenant_id, db=db, redis=redis,
    )
    return overview


@router.get(
    "/{employee_id}",
    response_model=AttritionResultResponse,
    dependencies=[require_permission("employees", "read")],
)
async def get_employee_attrition(
    employee_id: uuid.UUID,
    force:       bool         = False,
    db:          AsyncSession = Depends(get_db),
    current:     User         = Depends(get_current_user),
    redis                     = Depends(get_redis),
):
    """Predict attrition risk for a single employee."""
    result = await predict_attrition(
        tenant_id=current.tenant_id,
        employee_id=employee_id,
        db=db,
        redis=redis,
        force_refresh=force,
    )
    return {
        "employee_id":         str(employee_id),
        "risk_score":          result.risk_score,
        "risk_tier":           result.risk_tier,
        "top_risk_factors":    result.top_risk_factors,
        "recommended_actions": result.recommended_actions,
        "confidence":          result.confidence,
        "model_type":          result.model_type,
    }


@router.post(
    "/bulk-predict",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[require_permission("employees", "read")],
)
async def bulk_predict_attrition(
    background: BackgroundTasks,
    db:         AsyncSession = Depends(get_db),
    current:    User         = Depends(get_current_user),
    redis                    = Depends(get_redis),
):
    """
    Trigger attrition prediction for all active employees (async, cached).
    Returns immediately; results available via /overview after completion.
    """
    async def _run():
        try:
            await get_tenant_attrition_overview(
                tenant_id=current.tenant_id, db=db, redis=redis,
            )
        except Exception:
            pass

    background.add_task(_run)
    return {"message": "Bulk attrition prediction started. Check /overview in ~30 seconds."}

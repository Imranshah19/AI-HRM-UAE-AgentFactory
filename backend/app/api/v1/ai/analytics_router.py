"""
AI-HRMS — AI Analytics / Anomalies API Router.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.ai.analytics.anomaly_detector import Anomaly, detect_anomalies
from app.models.tenant import User

router = APIRouter(prefix="/ai/analytics", tags=["AI — Analytics"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class AnomalyResponse(BaseModel):
    id:                 str
    type:               str
    severity:           str
    description:        str
    affected_entities:  list[str]
    detected_at:        str
    recommended_action: str
    is_reviewed:        bool = False

    model_config = ConfigDict(from_attributes=True)


class AIInsightsResponse(BaseModel):
    anomalies:          list[AnomalyResponse]
    anomaly_count:      int
    high_severity:      int
    last_refreshed:     str

    model_config = ConfigDict(from_attributes=True)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/anomalies",
    response_model=list[AnomalyResponse],
    dependencies=[require_permission("reports", "read")],
)
async def get_anomalies(
    db:      AsyncSession = Depends(get_db),
    current: User         = Depends(get_current_user),
):
    """Detect and return all current HR anomalies for the tenant."""
    anomalies = await detect_anomalies(tenant_id=current.tenant_id, db=db)
    return [
        {
            "id":                 a.id,
            "type":               a.type,
            "severity":           a.severity,
            "description":        a.description,
            "affected_entities":  a.affected_entities,
            "detected_at":        a.detected_at,
            "recommended_action": a.recommended_action,
            "is_reviewed":        a.is_reviewed,
        }
        for a in anomalies
    ]


@router.get(
    "/insights",
    response_model=AIInsightsResponse,
    dependencies=[require_permission("reports", "read")],
)
async def get_ai_insights(
    db:      AsyncSession = Depends(get_db),
    current: User         = Depends(get_current_user),
    redis                 = Depends(__import__("app.core.redis", fromlist=["get_redis"]).get_redis),
):
    """
    Combined AI insights dashboard widget:
    anomalies + attrition summary + key metrics.
    """
    from datetime import datetime, timezone
    from app.ai.attrition.service import get_tenant_attrition_overview

    anomalies = await detect_anomalies(tenant_id=current.tenant_id, db=db)
    high_sev  = sum(1 for a in anomalies if a.severity == "high")

    return {
        "anomalies":      [
            {
                "id":                 a.id,
                "type":               a.type,
                "severity":           a.severity,
                "description":        a.description,
                "affected_entities":  a.affected_entities,
                "detected_at":        a.detected_at,
                "recommended_action": a.recommended_action,
                "is_reviewed":        a.is_reviewed,
            }
            for a in anomalies
        ],
        "anomaly_count":  len(anomalies),
        "high_severity":  high_sev,
        "last_refreshed": datetime.now(timezone.utc).isoformat(),
    }

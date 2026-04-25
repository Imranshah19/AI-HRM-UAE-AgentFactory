"""
AI-HRMS — Performance Prediction API Router.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db, require_permission
from app.ai.performance.predictor import predict_performance
from app.models.employee import Employee
from app.models.tenant import User

router = APIRouter(prefix="/ai/performance", tags=["AI — Performance"])


# ─── Schemas ──────────────────────────────────────────────────────────────────

class KeyDriver(BaseModel):
    factor:    str
    influence: str
    note:      str = ""

    model_config = ConfigDict(from_attributes=True)


class PerformancePredictionResponse(BaseModel):
    employee_id:             str
    predicted_band:          str
    predicted_score:         float
    confidence:              float
    key_drivers:             list[KeyDriver]
    improvement_suggestions: list[str]
    predicted_at:            str

    model_config = ConfigDict(from_attributes=True)


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get(
    "/{employee_id}",
    response_model=PerformancePredictionResponse,
    dependencies=[require_permission("employees", "read")],
)
async def get_performance_prediction(
    employee_id: uuid.UUID,
    db:          AsyncSession = Depends(get_db),
    current:     User         = Depends(get_current_user),
):
    """Predict performance band and score for a single employee."""
    # Verify employee belongs to tenant
    emp = (await db.execute(
        select(Employee).where(
            Employee.id == employee_id,
            Employee.tenant_id == current.tenant_id,
        )
    )).scalar_one_or_none()

    if emp is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    result = await predict_performance(employee_id=employee_id, db=db)
    return result


@router.get(
    "/team/{manager_id}",
    response_model=list[PerformancePredictionResponse],
    dependencies=[require_permission("performance", "read")],
)
async def get_team_performance_predictions(
    manager_id: uuid.UUID,
    db:         AsyncSession = Depends(get_db),
    current:    User         = Depends(get_current_user),
):
    """Predict performance for all direct reports of a manager."""
    team = (await db.execute(
        select(Employee.id)
        .where(
            Employee.manager_id == manager_id,
            Employee.tenant_id == current.tenant_id,
            Employee.employment_status == "active",
        )
    )).scalars().all()

    results = []
    for emp_id in team:
        try:
            pred = await predict_performance(employee_id=emp_id, db=db)
            results.append(pred)
        except Exception:
            continue

    return results

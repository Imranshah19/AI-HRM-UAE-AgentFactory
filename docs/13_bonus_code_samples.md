# BONUS DELIVERABLES — CODE SAMPLES & JSON OBJECTS

## Bonus 3a — FastAPI: GET /employees with JWT, RBAC, Tenant, Pagination

```python
# api/v1/employees.py
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from typing import Annotated
from core.tenant import TenantContext, get_current_tenant
from core.database import get_db
from core.rbac import require_permission
from core.rate_limit import rate_limit
from models.employee import Employee
from models.department import Department
from schemas.employee import EmployeeListItem, PaginatedEmployeeResponse
from services.search_service import search_employees
import math

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get(
    "",
    response_model=PaginatedEmployeeResponse,
    summary="List employees with RBAC, tenant isolation, and pagination",
)
@rate_limit(max_calls=100, period=60)  # 100 req/min
async def list_employees(
    # Query params
    search: Annotated[str | None, Query(max_length=100)] = None,
    department_id: str | None = None,
    branch_id: str | None = None,
    lifecycle_status: str | None = None,
    contract_type: str | None = None,
    page: Annotated[int, Query(ge=1, le=1000)] = 1,
    per_page: Annotated[int, Query(ge=1, le=100)] = 25,
    sort: Annotated[str, Query()] = "full_name",
    order: Annotated[str, Query(pattern="^(asc|desc)$")] = "asc",
    # Dependencies
    tenant: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("employees:read")),
):
    # If search query provided, use Elasticsearch for relevance ranking
    if search and len(search.strip()) >= 2:
        es_result = await search_employees(
            tenant_id=tenant.tenant_id,
            query=search,
            department_id=department_id,
            status=lifecycle_status,
            page=page,
            per_page=per_page,
        )
        return PaginatedEmployeeResponse(
            data=es_result["hits"],
            meta={
                "total": es_result["total"],
                "page": page,
                "per_page": per_page,
                "pages": math.ceil(es_result["total"] / per_page),
                "search_engine": "elasticsearch",
            },
        )

    # Standard PostgreSQL query for non-search listing
    query = (
        select(Employee)
        .where(Employee.tenant_id == tenant.tenant_id)  # tenant isolation
        .where(Employee.deleted_at.is_(None))
    )

    # RBAC scope: dept managers only see own department
    if tenant.role == "dept_manager":
        query = query.where(Employee.department_id == tenant.department_id)

    # Filters
    if department_id:
        query = query.where(Employee.department_id == department_id)
    if branch_id:
        query = query.where(Employee.branch_id == branch_id)
    if lifecycle_status:
        query = query.where(Employee.lifecycle_status == lifecycle_status)
    if contract_type:
        query = query.where(Employee.contract_type == contract_type)

    # Validate sort column (whitelist to prevent SQL injection)
    allowed_sort_cols = {
        "full_name": Employee.full_name,
        "joining_date": Employee.joining_date,
        "designation": Employee.designation,
        "employee_number": Employee.employee_number,
        "created_at": Employee.created_at,
    }
    sort_col = allowed_sort_cols.get(sort, Employee.full_name)
    if order == "desc":
        sort_col = sort_col.desc()

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Paginate
    query = query.order_by(sort_col).offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    employees = result.scalars().all()

    # Apply field-level RBAC (mask salary for non-Finance/HR roles)
    employee_data = [
        _apply_field_rbac(emp, tenant.role)
        for emp in employees
    ]

    return PaginatedEmployeeResponse(
        data=employee_data,
        meta={
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": math.ceil(total / per_page) if total else 0,
            "search_engine": "postgresql",
        },
    )


def _apply_field_rbac(employee: Employee, role: str) -> dict:
    """Apply field-level permissions: hide salary for non-privileged roles."""
    data = {
        "id": str(employee.id),
        "employee_number": employee.employee_number,
        "full_name": employee.full_name,
        "designation": employee.designation,
        "department_id": str(employee.department_id) if employee.department_id else None,
        "branch_id": str(employee.branch_id) if employee.branch_id else None,
        "lifecycle_status": employee.lifecycle_status,
        "contract_type": employee.contract_type,
        "joining_date": employee.joining_date.isoformat() if employee.joining_date else None,
        "profile_photo_url": employee.profile_photo_url,
        "work_email": employee.work_email,
    }

    # Only HR, Finance, Admin see salary-related info
    if role in ("hr_manager", "finance", "super_admin"):
        data["grade_level"] = employee.grade_level
        data["cost_center"] = employee.cost_center
    else:
        data["grade_level"] = None  # hidden
        data["cost_center"] = None

    return data
```

---

## Bonus 3b — FastAPI: POST /payroll/run with Celery + Feature Flag

```python
# api/v1/payroll.py
from fastapi import APIRouter, Depends, HTTPException, status
from celery_app import celery_app
from core.tenant import TenantContext, get_current_tenant
from core.database import get_db
from core.rbac import require_permission
from core.feature_flags import evaluate_flag
from core.rate_limit import rate_limit
from models.payroll import PayrollRun
from schemas.payroll import PayrollRunCreate, PayrollRunResponse
from datetime import datetime
import uuid

router = APIRouter(prefix="/payroll", tags=["payroll"])


@router.post(
    "/runs",
    response_model=PayrollRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@rate_limit(max_calls=1, period=3600)  # Only 1 payroll run initiation per hour
async def create_payroll_run(
    payload: PayrollRunCreate,
    tenant: TenantContext = Depends(get_current_tenant),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("payroll:run")),
):
    """
    Create and initiate a new payroll run.
    Dispatches to Celery for async processing.
    """
    # 1. Check for existing run in same period
    existing = await db.scalar(
        select(PayrollRun).where(
            PayrollRun.tenant_id == tenant.tenant_id,
            PayrollRun.period_month == payload.period_month,
            PayrollRun.period_year == payload.period_year,
            PayrollRun.status.not_in(["cancelled"]),
        )
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "RUN_ALREADY_EXISTS_FOR_PERIOD",
                "message": f"Payroll run already exists for {payload.period_month}/{payload.period_year}",
                "existing_run_id": str(existing.id),
            }
        )

    # 2. Determine which payroll engine to use (feature flag)
    use_new_engine = await evaluate_flag(
        "new_payroll_engine_v2",
        tenant_id=tenant.tenant_id,
        role=tenant.role,
    )

    # 3. Create PayrollRun record in DB
    run_code = f"PR-{payload.period_year}-{payload.period_month:02d}"
    payroll_run = PayrollRun(
        id=uuid.uuid4(),
        tenant_id=tenant.tenant_id,
        run_code=run_code,
        period_month=payload.period_month,
        period_year=payload.period_year,
        currency=payload.currency or "PKR",
        scope_type=payload.scope_type,
        scope_department_id=payload.scope_department_id,
        scope_branch_id=payload.scope_branch_id,
        status="processing",
        created_by=tenant.user_id,
    )
    db.add(payroll_run)
    await db.commit()
    await db.refresh(payroll_run)

    # 4. Dispatch Celery task (fire-and-forget)
    if use_new_engine:
        task = process_payroll_run_v2.delay(
            payroll_run_id=str(payroll_run.id),
            tenant_id=tenant.tenant_id,
            initiated_by=tenant.user_id,
        )
    else:
        task = process_payroll_run_v1.delay(
            payroll_run_id=str(payroll_run.id),
            tenant_id=tenant.tenant_id,
            initiated_by=tenant.user_id,
        )

    # 5. Store Celery task ID for status polling
    payroll_run.celery_task_id = task.id
    await db.commit()

    return PayrollRunResponse(
        run_id=str(payroll_run.id),
        run_code=run_code,
        job_id=task.id,
        status="processing",
        message=f"Payroll run initiated for {payload.period_month}/{payload.period_year}. "
                f"You will be notified on completion.",
        engine_version="v2" if use_new_engine else "v1",
    )


# celery_tasks/payroll_tasks.py
from celery_app import celery_app
from decimal import Decimal

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 min retry delay
    queue="payroll",
    acks_late=True,           # task not acked until complete (no data loss)
)
def process_payroll_run_v2(self, payroll_run_id: str, tenant_id: str, initiated_by: str):
    """
    Process payroll run for all employees in scope.
    This runs as a Celery task on dedicated payroll workers.
    """
    from sqlalchemy import create_engine
    from core.config import settings

    engine = create_engine(settings.DATABASE_URL)

    try:
        with engine.begin() as conn:
            # 1. Set tenant context for RLS
            conn.execute(text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                         {"tid": tenant_id})

            # 2. Fetch payroll run
            run = conn.execute(
                text("SELECT * FROM payroll_runs WHERE id = :id"),
                {"id": payroll_run_id}
            ).fetchone()

            # 3. Get employees in scope
            employees = _get_employees_in_scope(conn, run, tenant_id)

            # 4. Process each employee
            total_gross = Decimal("0")
            total_net = Decimal("0")
            processed = 0

            for emp in employees:
                try:
                    record = _calculate_employee_payroll(conn, emp, run)
                    total_gross += record["gross_salary"]
                    total_net += record["net_salary"]
                    processed += 1

                    # Update progress (stored in Redis for UI polling)
                    celery_app.backend.set(
                        f"payroll_progress:{payroll_run_id}",
                        f"{processed}/{len(employees)}",
                        ex=3600,
                    )

                except Exception as emp_error:
                    # Log per-employee errors but continue run
                    _log_payroll_error(conn, payroll_run_id, emp["id"], str(emp_error))
                    continue

            # 5. Update run totals + status
            conn.execute(text("""
                UPDATE payroll_runs
                SET status = 'calculated',
                    employee_count = :count,
                    total_gross_salary = :gross,
                    total_net_salary = :net,
                    updated_at = NOW()
                WHERE id = :run_id
            """), {
                "count": processed,
                "gross": float(total_gross),
                "net": float(total_net),
                "run_id": payroll_run_id,
            })

        # 6. Notify HR that payroll is ready for review
        send_notification.delay(
            tenant_id=tenant_id,
            event_type="payroll_calculated",
            recipient_role="hr_manager",
            variables={
                "run_code": run.run_code,
                "employee_count": processed,
                "total_net": float(total_net),
            }
        )

    except Exception as exc:
        # Update run status to failed
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE payroll_runs SET status='failed', notes=:err WHERE id=:id"
            ), {"err": str(exc), "id": payroll_run_id})

        raise self.retry(exc=exc)
```

---

## Bonus 3c — WebSocket: Real-time Attendance Feed

```python
# api/v1/websocket.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from jose import JWTError, jwt
from typing import dict
import asyncio
import json
import redis.asyncio as aioredis

router = APIRouter()

# Active connections: {tenant_id: {connection_id: WebSocket}}
active_connections: dict[str, dict[str, WebSocket]] = {}


async def authenticate_ws_token(token: str) -> dict | None:
    """Validate JWT from WebSocket query param."""
    try:
        payload = jwt.decode(token, os.environ["JWT_SECRET_KEY"], algorithms=["HS256"])
        return payload
    except JWTError:
        return None


@router.websocket("/ws/attendance")
async def attendance_websocket(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Real-time attendance feed.
    Clients receive events when any employee checks in or out within their tenant.
    """
    # 1. Authenticate
    payload = await authenticate_ws_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    tenant_id = payload["tenant_id"]
    user_role = payload["role"]

    # Only HR and Admin roles can access live attendance feed
    if user_role not in ("hr_manager", "super_admin", "dept_manager"):
        await websocket.close(code=4003, reason="Forbidden")
        return

    await websocket.accept()
    connection_id = f"{tenant_id}:{payload['sub']}:{id(websocket)}"

    # Register connection
    if tenant_id not in active_connections:
        active_connections[tenant_id] = {}
    active_connections[tenant_id][connection_id] = websocket

    # Send initial snapshot (today's attendance summary)
    try:
        snapshot = await _get_attendance_snapshot(tenant_id)
        await websocket.send_json({
            "type": "snapshot",
            "data": snapshot,
        })

        # Subscribe to Redis pub/sub channel for this tenant
        redis = aioredis.from_url(os.environ["REDIS_URL"])
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"attendance:{tenant_id}")

        # Listen for events
        async def listen_redis():
            async for message in pubsub.listen():
                if message["type"] == "message":
                    event_data = json.loads(message["data"])

                    # Apply dept_manager scope filter
                    if user_role == "dept_manager":
                        if event_data.get("department_id") != payload.get("department_id"):
                            continue

                    try:
                        await websocket.send_json({
                            "type": "attendance_event",
                            "data": event_data,
                        })
                    except Exception:
                        break  # WebSocket closed

        # Run Redis listener with heartbeat
        async def heartbeat():
            while True:
                await asyncio.sleep(30)
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

        await asyncio.gather(
            listen_redis(),
            heartbeat(),
        )

    except WebSocketDisconnect:
        pass
    finally:
        # Cleanup
        if tenant_id in active_connections:
            active_connections[tenant_id].pop(connection_id, None)
        await pubsub.unsubscribe(f"attendance:{tenant_id}")
        await redis.close()


def publish_attendance_event(tenant_id: str, event: dict):
    """
    Called from attendance check-in/out endpoint to broadcast event.
    Uses synchronous Redis publish (called from sync context).
    """
    import redis as sync_redis
    r = sync_redis.from_url(os.environ["REDIS_URL"])
    r.publish(f"attendance:{tenant_id}", json.dumps(event))

# Example event published on check-in:
# {
#   "event": "employee_checked_in",
#   "employee_id": "uuid",
#   "full_name": "Ahmed Khan",
#   "designation": "Software Engineer",
#   "department_id": "uuid",
#   "check_in_time": "2024-01-15T09:12:00Z",
#   "method": "geo_fence",
#   "geofence_status": "within",
#   "late_minutes": 12,
#   "avatar_url": "https://..."
# }
```

---

## Bonus 3d — Rate Limiting Middleware (slowapi + Redis)

```python
# core/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
import redis.asyncio as aioredis
import time
import functools

# Sliding window rate limiter using Redis
class SlidingWindowRateLimiter:
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> tuple[bool, dict]:
        """
        Sliding window rate limit check.
        Returns (allowed: bool, headers: dict)
        """
        now = time.time()
        window_start = now - window_seconds
        pipe_key = f"rl:{key}"

        async with self.redis.pipeline() as pipe:
            # Remove old requests outside window
            await pipe.zremrangebyscore(pipe_key, 0, window_start)
            # Count requests in window
            await pipe.zcard(pipe_key)
            # Add current request
            await pipe.zadd(pipe_key, {str(now): now})
            # Set expiry
            await pipe.expire(pipe_key, window_seconds)
            results = await pipe.execute()

        current_count = results[1]
        allowed = current_count < limit
        remaining = max(0, limit - current_count - (1 if allowed else 0))

        # TTL for retry-after
        oldest = await self.redis.zrange(pipe_key, 0, 0, withscores=True)
        retry_after = 0
        if oldest and not allowed:
            retry_after = int(oldest[0][1] + window_seconds - now) + 1

        return allowed, {
            "X-RateLimit-Limit": str(limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(now + window_seconds)),
            "Retry-After": str(retry_after) if retry_after > 0 else "0",
        }


# Role-based rate limits
ROLE_RATE_LIMITS = {
    "super_admin": 500,
    "hr_manager": 200,
    "finance": 200,
    "recruiter": 150,
    "dept_manager": 100,
    "employee": 60,
    "anonymous": 20,
}

rate_limiter = SlidingWindowRateLimiter(os.environ["REDIS_URL"])

async def check_rate_limit(request: Request, tenant: TenantContext | None = None):
    """FastAPI middleware for role-aware rate limiting."""
    role = tenant.role if tenant else "anonymous"
    limit = ROLE_RATE_LIMITS.get(role, 60)
    user_key = f"{tenant.user_id}:{request.url.path}" if tenant else get_remote_address(request)

    allowed, headers = await rate_limiter.is_allowed(
        key=user_key,
        limit=limit,
        window_seconds=60,
    )

    # Add headers to response regardless of allowed/denied
    for k, v in headers.items():
        request.state.rate_limit_headers = headers

    if not allowed:
        # Check for abuse: if this IP has been rate-limited 10+ times in 1 hour
        abuse_key = f"rl_abuse:{get_remote_address(request)}"
        abuse_count = await rate_limiter.redis.incr(abuse_key)
        await rate_limiter.redis.expire(abuse_key, 3600)

        if abuse_count >= 10:
            # Block IP for 1 hour
            block_key = f"rl_block:{get_remote_address(request)}"
            await rate_limiter.redis.setex(block_key, 3600, "1")

        from fastapi import HTTPException
        raise HTTPException(
            status_code=429,
            detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": f"Too many requests. Limit: {limit}/min for role: {role}",
                "retry_after": headers["Retry-After"],
            },
            headers=headers,
        )


# Endpoint-specific rate limit decorator
def rate_limit(max_calls: int, period: int):
    """Decorator to apply per-endpoint rate limits."""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            request = kwargs.get("request") or next(
                (a for a in args if isinstance(a, Request)), None
            )
            if request:
                endpoint_key = f"ep:{request.url.path}"
                allowed, headers = await rate_limiter.is_allowed(
                    key=endpoint_key,
                    limit=max_calls,
                    window_seconds=period,
                )
                if not allowed:
                    raise HTTPException(
                        status_code=429,
                        detail={"code": "ENDPOINT_RATE_LIMIT",
                                "retry_after": headers["Retry-After"]},
                        headers=headers,
                    )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## Bonus 5 — Sample JSON Objects

### employee_object
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "tenant_acme_corp",
  "employee_number": "EMP-0042",
  "first_name": "Muhammad",
  "middle_name": null,
  "last_name": "Ahmed",
  "full_name": "Muhammad Ahmed",
  "date_of_birth": "1992-03-15",
  "gender": "male",
  "marital_status": "married",
  "nationality": "Pakistani",
  "cnic_nid": "42201-1234567-1",
  "cnic_expiry": "2030-12-31",
  "profile_photo_url": "https://cdn.hrms.com/photos/emp-0042.jpg",
  "personal_email": "m.ahmed@gmail.com",
  "work_email": "m.ahmed@acmecorp.com",
  "phone_primary": "+92-300-1234567",
  "phone_secondary": null,
  "address": {
    "line1": "House 42, Street 5, DHA Phase 6",
    "line2": null,
    "city": "Karachi",
    "state": "Sindh",
    "postal_code": "75500",
    "country": "Pakistan"
  },
  "emergency_contact": {
    "name": "Fatima Ahmed",
    "relation": "spouse",
    "phone": "+92-333-7654321",
    "email": "fatima@gmail.com"
  },
  "employment": {
    "department": {"id": "uuid", "name": "Engineering", "code": "ENG"},
    "branch": {"id": "uuid", "name": "Karachi HQ", "city": "Karachi"},
    "designation": "Senior Software Engineer",
    "grade_level": "L5",
    "contract_type": "permanent",
    "work_schedule": "hybrid",
    "joining_date": "2021-06-01",
    "probation_end_date": "2021-09-01",
    "confirmation_date": "2021-09-15",
    "lifecycle_status": "active",
    "notice_period_days": 30,
    "reporting_manager": {
      "id": "uuid",
      "full_name": "Sarah Khan",
      "designation": "Engineering Manager"
    }
  },
  "compensation": {
    "currency": "PKR",
    "basic_salary": 150000,
    "gross_salary": 225000,
    "allowances": {
      "hra": 45000,
      "medical": 10000,
      "transport": 10000,
      "fuel": 5000,
      "utility": 5000
    },
    "effective_date": "2024-01-01"
  },
  "metrics": {
    "tenure_months": 32,
    "leave_balance": {"annual": 12, "sick": 10, "casual": 8},
    "last_performance_band": "exceeds",
    "attrition_risk_score": 22.5,
    "attrition_risk_tier": "low"
  },
  "created_at": "2021-05-28T10:30:00Z",
  "updated_at": "2024-01-15T09:00:00Z"
}
```

### payslip_object
```json
{
  "payslip_id": "uuid",
  "employee": {
    "id": "uuid",
    "name": "Muhammad Ahmed",
    "employee_number": "EMP-0042",
    "designation": "Senior Software Engineer",
    "department": "Engineering",
    "bank": "HBL",
    "account_number": "****3456"
  },
  "period": {"month": 1, "year": 2024, "label": "January 2024"},
  "attendance": {
    "working_days": 23,
    "present_days": 22,
    "absent_days": 0,
    "leave_days": 1,
    "holidays": 1,
    "late_arrivals": 2,
    "overtime_hours": 5.5
  },
  "earnings": {
    "basic_salary": 150000,
    "house_rent_allowance": 45000,
    "medical_allowance": 10000,
    "transport_allowance": 10000,
    "fuel_allowance": 5000,
    "utility_allowance": 5000,
    "overtime_pay": 4891,
    "gross_salary": 229891
  },
  "deductions": {
    "income_tax": 8750,
    "eobi": 370,
    "sessi": 0,
    "loan_deduction": 5000,
    "advance_recovery": 0,
    "total_deductions": 14120
  },
  "net_salary": 215771,
  "ytd": {
    "gross_ytd": 229891,
    "tax_ytd": 8750,
    "net_ytd": 215771
  },
  "generated_at": "2024-02-01T06:00:00Z",
  "payslip_pdf_url": "https://s3.hrms.com/payslips/tenant/2024/01/EMP-0042.pdf",
  "digital_signature": "SHA256:a3f5c...",
  "status": "approved"
}
```

### cv_score_result_object
```json
{
  "application_id": "uuid",
  "job_id": "uuid",
  "candidate_name": "Ali Hassan",
  "job_title": "Senior Python Developer",
  "overall_score": 84.5,
  "score_band": "strong_match",
  "breakdown": {
    "semantic_similarity": 78.2,
    "skills_match": 91.4,
    "experience_match": 85.0,
    "education_match": 100.0
  },
  "matched_skills": ["python", "fastapi", "postgresql", "docker", "redis"],
  "missing_skills": ["aws", "kubernetes"],
  "candidate_experience_years": 6,
  "required_experience_years": 5,
  "candidate_education": "Bachelor",
  "explanation": "Score 84.5/100 — Skills matched: python, fastapi, postgresql, docker, redis | Skills missing: aws, kubernetes | 6yr exp matched (5yr required) | Education: Bachelor",
  "bias_flags": {
    "potential_age_indicator": false,
    "potential_gender_indicator": false,
    "personal_demographic_data": false
  },
  "recommended_action": "shortlist",
  "model_version": "v1.2",
  "scored_at": "2024-01-15T11:23:45Z"
}
```

### attrition_risk_object
```json
{
  "employee_id": "uuid",
  "employee_name": "Sara Ali",
  "risk_score": 73.4,
  "risk_tier": "critical",
  "risk_factors": [
    {
      "factor": "Salary Below Market Rate",
      "current_value": 0.82,
      "shap_impact": 0.1842,
      "direction": "positively"
    },
    {
      "factor": "Long Time Without Promotion",
      "current_value": 42,
      "shap_impact": 0.1234,
      "direction": "positively"
    },
    {
      "factor": "High Overtime Load",
      "current_value": 48.5,
      "shap_impact": 0.0987,
      "direction": "positively"
    }
  ],
  "recommendations": [
    "Schedule compensation review against market benchmarks",
    "Review career progression path and create development plan",
    "Review workload distribution and consider backfill"
  ],
  "explanation": "CRITICAL attrition risk (73.4%). Top driver: Salary Below Market Rate.",
  "should_alert_hr": true,
  "alert_sent_at": "2024-01-15T06:00:00Z",
  "model_version": "v1.0",
  "predicted_at": "2024-01-15T06:00:00Z"
}
```

### feature_flag_config_object
```json
{
  "id": "uuid",
  "key": "new_payroll_engine_v2",
  "name": "New Payroll Engine V2",
  "description": "Enables the rewritten payroll calculation engine with improved tax slab handling",
  "flag_type": "percentage",
  "is_enabled": true,
  "rollout_percentage": 25.0,
  "variants": [],
  "tenant_overrides": {
    "tenant_acme_corp": true,
    "tenant_beta_test": true,
    "tenant_legacy_client": false
  },
  "role_overrides": {
    "super_admin": true
  },
  "department_overrides": {},
  "environment": "production",
  "expires_at": null,
  "tags": ["payroll", "v2", "backend"],
  "created_by": "admin_uuid",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

### notification_event_object
```json
{
  "event_id": "uuid",
  "event_type": "probation_ending_soon",
  "tenant_id": "tenant_acme_corp",
  "recipient": {
    "employee_id": "uuid",
    "name": "Muhammad Ahmed",
    "email": "m.ahmed@acmecorp.com",
    "phone": "+92-300-1234567"
  },
  "channels": ["email", "in_app"],
  "priority": "high",
  "template_id": "uuid",
  "variables": {
    "employee_name": "Muhammad Ahmed",
    "probation_end_date": "2024-02-01",
    "days_remaining": 7,
    "hr_contact": "hr@acmecorp.com",
    "manager_name": "Sarah Khan",
    "action_required": "Conduct performance review and submit confirmation decision"
  },
  "rendered": {
    "subject": "⚠️ Probation Ending in 7 Days — Muhammad Ahmed",
    "body": "Dear Sarah Khan,\n\nThis is a reminder that Muhammad Ahmed's probation period ends on 01 February 2024 (7 days from now).\n\nAction Required: Please submit the probation review decision at your earliest.\n\nBest regards,\nHR Team"
  },
  "delivery_status": {
    "email": "sent",
    "in_app": "delivered"
  },
  "sent_at": "2024-01-25T06:00:00Z",
  "created_at": "2024-01-25T06:00:00Z"
}
```

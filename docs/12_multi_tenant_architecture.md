# SECTION 11 — MULTI-TENANT, FEATURE FLAGS, API VERSIONING, ELASTICSEARCH

## 11.1 Multi-Tenant Isolation — Final Decision: Shared Schema

### Comparison Table
| Criteria | Shared Schema (tenant_id) | Schema-per-Tenant | DB-per-Tenant |
|---|---|---|---|
| Ops overhead | Low (1 migration) | Medium (N migrations) | High (N DB instances) |
| Cost at 50 tenants | $ (shared instances) | $$ | $$$$ |
| Isolation strength | Application-level | Schema boundary | Full isolation |
| Cross-tenant query | Easy (admin analytics) | JOIN across schemas | Impossible |
| Tenant data export | Complex query | pg_dump schema | pg_dump whole DB |
| Backup granularity | Full DB backup | Per-schema possible | Per-DB backup |
| Performance at scale | Good with RLS + indexes | Good | Good |
| Compliance (GDPR) | Requires careful RLS | Easier | Strongest |

**Decision: Shared Schema** — justified by scale (50–200 subsidiaries expected), low
ops overhead requirement, and the fact that application-layer + PostgreSQL RLS provides
sufficient isolation if implemented correctly.

**When to reconsider**: If any tenant requires dedicated hardware (SOC2 Type II, bank-level
compliance), provision a DB-per-tenant instance for that tenant specifically.

### Row-Level Security (Defense in Depth)

```sql
-- Enable RLS on all sensitive tables
ALTER TABLE employees ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE leave_requests ENABLE ROW LEVEL SECURITY;

-- Policy: app user can only see own tenant's rows
-- Application sets tenant context via SET LOCAL
CREATE POLICY tenant_isolation_employees ON employees
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_payroll ON payroll_records
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_attendance ON attendance_records
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

CREATE POLICY tenant_isolation_leaves ON leave_requests
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid);

-- Superuser/service role bypasses RLS for migrations and admin operations
-- Application role (hrms_app) is NOT a superuser
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO hrms_app;
```

### FastAPI Tenant Injection

```python
# core/tenant.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from core.database import get_db
import os

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
SECRET_KEY = os.environ["JWT_SECRET_KEY"]
ALGORITHM = "HS256"


class TenantContext:
    def __init__(self, tenant_id: str, user_id: str, role: str, email: str):
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role
        self.email = email


async def get_current_tenant(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> TenantContext:
    """
    Dependency that:
    1. Validates JWT
    2. Extracts tenant_id from JWT claims
    3. Sets PostgreSQL session variable for RLS
    4. Returns TenantContext for downstream use
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        tenant_id: str = payload.get("tenant_id")
        user_id: str = payload.get("sub")
        role: str = payload.get("role")
        email: str = payload.get("email")

        if not all([tenant_id, user_id, role]):
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    # Set tenant context in PostgreSQL session — enables RLS policies
    await db.execute(
        "SELECT set_config('app.current_tenant_id', :tid, true)",
        {"tid": tenant_id},
    )

    return TenantContext(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        email=email,
    )


# Usage in any endpoint:
# async def get_employees(
#     tenant: TenantContext = Depends(get_current_tenant),
#     db: AsyncSession = Depends(get_db),
# ):
#     # tenant.tenant_id is now set in DB session via RLS
#     # All queries automatically filtered by RLS policy
#     result = await db.execute(select(Employee))  # RLS applies automatically
```

### Tenant Onboarding Lifecycle

```python
# services/tenant_service.py
async def onboard_tenant(tenant_data: dict, db: AsyncSession) -> dict:
    """
    Full tenant onboarding:
    1. Create tenant record
    2. Create default roles and permissions
    3. Create default leave types
    4. Create default notification templates
    5. Create default feature flag overrides
    6. Create super admin user for tenant
    7. Send welcome email with setup instructions
    """
    # 1. Create tenant
    tenant = Tenant(**tenant_data)
    db.add(tenant)
    await db.flush()

    tenant_id = str(tenant.id)

    # 2. Default roles
    default_roles = [
        {"name": "super_admin", "level": 10},
        {"name": "hr_manager", "level": 8},
        {"name": "recruiter", "level": 6},
        {"name": "finance", "level": 7},
        {"name": "dept_manager", "level": 5},
        {"name": "employee", "level": 1},
    ]
    for role_data in default_roles:
        db.add(Role(tenant_id=tenant_id, **role_data))

    # 3. Default leave types (Pakistan)
    default_leaves = [
        {"name": "Annual Leave", "code": "AL", "annual_allocation": 20,
         "carry_forward_allowed": True, "carry_forward_max_days": 10},
        {"name": "Sick Leave", "code": "SL", "annual_allocation": 10,
         "requires_document": True},
        {"name": "Casual Leave", "code": "CL", "annual_allocation": 10},
        {"name": "Maternity Leave", "code": "ML", "annual_allocation": 90,
         "gender_restriction": "female"},
        {"name": "Paternity Leave", "code": "PL", "annual_allocation": 7,
         "gender_restriction": "male"},
        {"name": "Unpaid Leave", "code": "UL", "annual_allocation": 0,
         "is_paid": False},
    ]
    for leave_data in default_leaves:
        db.add(LeaveType(tenant_id=tenant_id, **leave_data))

    await db.commit()

    # 4. Trigger welcome email via Celery
    send_tenant_welcome_email.delay(tenant_id=tenant_id)

    return {"tenant_id": tenant_id, "status": "onboarded"}


async def offboard_tenant(tenant_id: str, db: AsyncSession):
    """
    GDPR-compliant tenant offboarding:
    1. Export all tenant data to S3 (for handover)
    2. Anonymize PII after 30-day grace period
    3. Soft-delete tenant record
    4. Revoke all active sessions
    5. Archive payroll/legal records per retention policy (7 years)
    """
    # Trigger async Celery task for long-running export
    export_tenant_data.delay(tenant_id=tenant_id)

    # Revoke sessions immediately
    await revoke_all_tenant_sessions(tenant_id, db)

    # Mark for deletion (actual deletion after 30-day grace)
    await db.execute(
        "UPDATE tenants SET deleted_at = NOW() + INTERVAL '30 days', is_active = FALSE "
        "WHERE id = :tid",
        {"tid": tenant_id},
    )
    await db.commit()
```

---

## 11.2 Feature Flag System

### Schema (Already in Section 2 — feature_flags table)

### Redis-backed Flag Evaluation

```python
# core/feature_flags.py
import json
import hashlib
from typing import Any
import redis.asyncio as aioredis

redis_client: aioredis.Redis = None  # initialized at startup

FLAG_CACHE_TTL = 300  # 5 minutes


async def evaluate_flag(
    flag_key: str,
    user_id: str | None = None,
    tenant_id: str | None = None,
    role: str | None = None,
) -> bool | Any:
    """
    Evaluate a feature flag for given context.
    Resolution order:
    1. Per-tenant override
    2. Per-role override
    3. Percentage rollout (deterministic by user_id hash)
    4. Global is_enabled
    """

    # Try Redis cache first
    cache_key = f"ff:{flag_key}"
    cached = await redis_client.get(cache_key)
    if cached:
        flag = json.loads(cached)
    else:
        # Fetch from DB
        flag = await _load_flag_from_db(flag_key)
        if flag:
            await redis_client.setex(cache_key, FLAG_CACHE_TTL, json.dumps(flag))

    if not flag:
        return False  # Unknown flags default to off

    # Check expiry
    if flag.get("expires_at"):
        from datetime import datetime, timezone
        if datetime.now(timezone.utc) > datetime.fromisoformat(flag["expires_at"]):
            return False

    # Per-tenant override
    if tenant_id and flag.get("tenant_overrides"):
        tenant_override = flag["tenant_overrides"].get(tenant_id)
        if tenant_override is not None:
            return tenant_override

    # Per-role override
    if role and flag.get("role_overrides"):
        role_override = flag["role_overrides"].get(role)
        if role_override is not None:
            return role_override

    # Percentage rollout
    if flag.get("flag_type") == "percentage" and user_id:
        rollout_pct = flag.get("rollout_percentage", 0)
        # Deterministic hash: same user always gets same result
        hash_val = int(hashlib.md5(f"{flag_key}:{user_id}".encode()).hexdigest(), 16)
        user_bucket = (hash_val % 10000) / 100.0  # 0.00 to 99.99
        return user_bucket < rollout_pct

    # Multivariate
    if flag.get("flag_type") == "multivariate" and user_id:
        variants = flag.get("variants", [])
        if variants:
            hash_val = int(hashlib.md5(f"{flag_key}:{user_id}".encode()).hexdigest(), 16)
            bucket = (hash_val % 100)
            cumulative = 0
            for variant in variants:
                cumulative += variant["weight"]
                if bucket < cumulative:
                    return variant["value"]

    return flag.get("is_enabled", False)


# Decorator for easy use in endpoints
def feature_required(flag_key: str, fallback=None):
    """Dependency that checks feature flag before executing endpoint."""
    async def _check_flag(
        tenant: TenantContext = Depends(get_current_tenant),
    ):
        enabled = await evaluate_flag(
            flag_key,
            user_id=tenant.user_id,
            tenant_id=tenant.tenant_id,
            role=tenant.role,
        )
        if not enabled:
            if fallback:
                return fallback
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Feature '{flag_key}' is not available for your account",
            )
        return enabled
    return Depends(_check_flag)


# Usage examples:
# @router.post("/payroll/runs")
# async def create_payroll_run(
#     payload: PayrollRunCreate,
#     _: bool = feature_required("new_payroll_engine"),
#     tenant: TenantContext = Depends(get_current_tenant),
# ):
#     if await evaluate_flag("new_payroll_engine", user_id=tenant.user_id):
#         return await new_payroll_engine_service.run(payload, tenant)
#     return await legacy_payroll_service.run(payload, tenant)
```

---

## 11.3 API Versioning Strategy

### Policy
- URL-based versioning: `/api/v1/`, `/api/v2/` (headers-only versioning rejected
  for HRMS — URL versioning is explicit, cacheable, and bookmark-friendly)
- v1 supported minimum 12 months after v2 launch
- No breaking changes within a major version (additive only)

### Deprecation Timeline
```
Month 0   : v2 launched
Month 1   : v1 docs show "Deprecated" banner
Month 3   : v1 responses include header:
            Deprecation: true
            Sunset: Sat, 01 Jan 2027 00:00:00 GMT
            Link: </api/v2/employees>; rel="successor-version"
Month 9   : Email notifications to API clients with registered webhooks
Month 12  : v1 returns HTTP 410 Gone with body:
            {"error": {"code": "API_VERSION_SUNSET",
             "message": "API v1 was sunset on 2027-01-01. Migrate to /api/v2/",
             "migration_guide": "https://docs.hrms.com/api-migration-v1-to-v2"}}
```

### FastAPI Version Router

```python
# main.py
from fastapi import FastAPI
from api.v1 import router as v1_router
from api.v2 import router as v2_router
from core.versioning import DeprecationMiddleware

app = FastAPI()

app.add_middleware(DeprecationMiddleware, deprecated_versions=["v1"])

app.include_router(v1_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api/v2")

# core/versioning.py
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import time

class DeprecationMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, deprecated_versions: list[str]):
        super().__init__(app)
        self.deprecated_versions = deprecated_versions

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        for version in self.deprecated_versions:
            if f"/api/{version}/" in path:
                response.headers["Deprecation"] = "true"
                response.headers["Sunset"] = "Sat, 01 Jan 2027 00:00:00 GMT"
                response.headers["Link"] = (
                    f'<{path.replace(f"/api/{version}/", "/api/v2/")}>;'
                    f' rel="successor-version"'
                )
        return response
```

---

## 11.4 Elasticsearch Index Design

### Index Definitions

```json
// PUT /hrms-employees-{tenant_id}
{
  "settings": {
    "number_of_shards": 2,
    "number_of_replicas": 1,
    "refresh_interval": "5s",
    "analysis": {
      "filter": {
        "hr_synonym_filter": {
          "type": "synonym",
          "synonyms": [
            "sr => senior", "snr => senior",
            "jr => junior", "jnr => junior",
            "mgr => manager", "dir => director",
            "eng => engineer", "dev => developer",
            "hr => human resources"
          ]
        },
        "edge_ngram_filter": {
          "type": "edge_ngram",
          "min_gram": 2,
          "max_gram": 20
        }
      },
      "analyzer": {
        "autocomplete_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "edge_ngram_filter"]
        },
        "search_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "hr_synonym_filter"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "id":              {"type": "keyword"},
      "tenant_id":       {"type": "keyword"},
      "employee_number": {"type": "keyword"},
      "full_name": {
        "type": "text",
        "analyzer": "autocomplete_analyzer",
        "search_analyzer": "search_analyzer",
        "fields": {"keyword": {"type": "keyword"}}
      },
      "designation": {
        "type": "text",
        "boost": 3,
        "analyzer": "search_analyzer",
        "fields": {"keyword": {"type": "keyword"}}
      },
      "department_name": {"type": "keyword"},
      "branch_name":     {"type": "keyword"},
      "skills":          {"type": "keyword"},
      "email":           {"type": "keyword"},
      "phone":           {"type": "keyword"},
      "lifecycle_status": {"type": "keyword"},
      "joining_date":    {"type": "date"},
      "is_active":       {"type": "boolean"}
    }
  }
}
```

### Query Examples

```python
# services/search_service.py
from elasticsearch import AsyncElasticsearch

es = AsyncElasticsearch(hosts=[os.environ["ELASTICSEARCH_URL"]])

async def search_employees(
    tenant_id: str,
    query: str,
    department_id: str | None = None,
    status: str | None = None,
    page: int = 1,
    per_page: int = 25,
) -> dict:
    """
    Elasticsearch employee search with:
    - Fuzzy matching (handles typos)
    - Field boosting (designation > full_name > email)
    - Filters (department, status)
    - Pagination via search_after
    """
    must_clauses = [
        {"term": {"tenant_id": tenant_id}},  # tenant isolation in ES
    ]

    should_clauses = [
        {"match": {
            "full_name": {
                "query": query,
                "fuzziness": "AUTO",
                "boost": 2.0,
            }
        }},
        {"match": {
            "designation": {
                "query": query,
                "fuzziness": "AUTO",
                "boost": 3.0,  # title matches rank highest
            }
        }},
        {"match": {
            "employee_number": {
                "query": query,
                "boost": 5.0,  # exact ID match highest priority
            }
        }},
        {"term": {"email": query}},
        {"terms_set": {
            "skills": {
                "terms": query.split(),
                "minimum_should_match_script": {"source": "1"},
                "boost": 2.0,
            }
        }},
    ]

    filter_clauses = []
    if department_id:
        filter_clauses.append({"term": {"department_id": department_id}})
    if status:
        filter_clauses.append({"term": {"lifecycle_status": status}})
    else:
        filter_clauses.append({"term": {"is_active": True}})

    body = {
        "query": {
            "bool": {
                "must": must_clauses,
                "should": should_clauses,
                "filter": filter_clauses,
                "minimum_should_match": 1,
            }
        },
        "sort": [
            {"_score": "desc"},
            {"joining_date": "desc"},
        ],
        "from": (page - 1) * per_page,
        "size": per_page,
        "highlight": {
            "fields": {
                "full_name": {},
                "designation": {},
            }
        },
    }

    response = await es.search(index=f"hrms-employees-{tenant_id}", body=body)

    return {
        "hits": [
            {**hit["_source"], "highlight": hit.get("highlight", {})}
            for hit in response["hits"]["hits"]
        ],
        "total": response["hits"]["total"]["value"],
    }


async def autocomplete_employee_name(tenant_id: str, prefix: str) -> list[str]:
    """Fast autocomplete for employee name search input."""
    body = {
        "suggest": {
            "name_suggest": {
                "prefix": prefix,
                "completion": {
                    "field": "full_name_suggest",
                    "size": 5,
                    "contexts": {
                        "tenant": [{"context": tenant_id}]
                    }
                }
            }
        }
    }
    response = await es.search(index=f"hrms-employees-*", body=body)
    suggestions = response["suggest"]["name_suggest"][0]["options"]
    return [s["text"] for s in suggestions]
```

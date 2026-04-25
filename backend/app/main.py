"""
AI-HRMS — FastAPI Application Entry Point
"""

import uuid
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from app.core.config import settings
from app.core.database import engine
from app.core.logging import configure_logging
from app.core.rate_limit import limiter, rate_limit_exceeded_handler

logger = structlog.get_logger(__name__)


# ─── Lifespan ─────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ────────────────────────────────────────────────────────────
    configure_logging()
    logger.info("AI-HRMS starting", environment=settings.APP_ENV, debug=settings.DEBUG)

    # Verify DB connectivity
    try:
        import sqlalchemy
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as exc:
        logger.error("Database connection failed", error=str(exc))
        raise

    # Verify Redis connectivity
    try:
        from app.core.redis import get_redis
        redis = get_redis()
        await redis.ping()
        await redis.aclose()
        logger.info("Redis connection verified")
    except Exception as exc:
        logger.warning("Redis connection failed (non-fatal in dev)", error=str(exc))

    # Seed first super-admin if needed
    from app.core.seeder import seed_superadmin
    await seed_superadmin()

    logger.info("AI-HRMS startup complete")
    yield

    # ── Shutdown ───────────────────────────────────────────────────────────
    logger.info("AI-HRMS shutting down")
    await engine.dispose()
    logger.info("Database connections closed")


# ─── App Factory ──────────────────────────────────────────────────────────────

app = FastAPI(
    title="AI-HRMS API",
    description=(
        "Enterprise Human Resource Management System with AI capabilities. "
        "Multi-tenant, RBAC-secured, async FastAPI backend."
    ),
    version="1.0.0",
    docs_url="/docs"         if settings.DEBUG else None,
    redoc_url="/redoc"       if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ─── Rate Limiter State ────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# ─── Middleware (order matters — outermost runs first on request) ──────────────

# 1. CORS — must come before any middleware that might return early
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Content-Type",
        "Authorization",
        "X-Request-ID",
        "X-Tenant-Slug",
        "X-Forwarded-For",
    ],
    expose_headers=["X-Request-ID", "X-Total-Count", "X-Page", "X-Page-Size"],
)

# 2. Trusted hosts (production only)
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS,
    )

# 3. Audit middleware (fires background task after mutating requests)
from app.middleware.audit import AuditMiddleware
app.add_middleware(AuditMiddleware)

# 4. Tenant middleware (resolves + injects tenant context)
from app.middleware.tenant import TenantMiddleware
app.add_middleware(TenantMiddleware)


# ─── Request ID Middleware ─────────────────────────────────────────────────────

@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    # Stash on request state for audit middleware to read
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# ─── Global Exception Handlers ────────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", None)
    logger.error(
        "Unhandled exception",
        path=str(request.url),
        method=request.method,
        request_id=request_id,
        error=str(exc),
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code":       "INTERNAL_SERVER_ERROR",
                "message":    "An unexpected error occurred. Please try again later.",
                "request_id": request_id,
            },
        },
    )


# ─── Routers ──────────────────────────────────────────────────────────────────

from app.api.v1.router import v1_router  # noqa: E402

app.include_router(v1_router)


# ─── Health & Root ────────────────────────────────────────────────────────────

@app.get("/health", tags=["System"], summary="Health check")
async def health_check():
    """
    Returns health status of all dependent services.
    Used by Docker, load balancers, and uptime monitors.
    """
    import sqlalchemy
    from app.core.redis import get_redis as _get_redis

    result: dict = {
        "status":      "healthy",
        "version":     "1.0.0",
        "environment": settings.APP_ENV,
        "services":    {},
    }

    try:
        async with engine.connect() as conn:
            await conn.execute(sqlalchemy.text("SELECT 1"))
        result["services"]["database"] = "healthy"
    except Exception as exc:
        result["services"]["database"] = f"unhealthy: {exc}"
        result["status"] = "degraded"

    try:
        redis = _get_redis()
        await redis.ping()
        await redis.aclose()
        result["services"]["redis"] = "healthy"
    except Exception as exc:
        result["services"]["redis"] = f"unhealthy: {exc}"
        result["status"] = "degraded"

    http_status = (
        status.HTTP_200_OK
        if result["status"] == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    return JSONResponse(content=result, status_code=http_status)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name":    "AI-HRMS API",
        "version": "1.0.0",
        "docs":    "/docs" if settings.DEBUG else "disabled",
        "health":  "/health",
    }

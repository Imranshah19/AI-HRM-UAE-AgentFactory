"""
AI-HRMS — Rate limiting via slowapi + Redis.

Usage in a router:
    from app.core.rate_limit import limiter

    @router.post("/login")
    @limiter.limit("10/minute")
    async def login(request: Request, ...):
        ...

Register in main.py:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from app.core.rate_limit import limiter

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
"""

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.core.config import settings


def _get_real_ip(request: Request) -> str:
    """
    Extract the real client IP, respecting X-Forwarded-For behind a proxy.
    Falls back to the direct connection remote address.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return get_remote_address(request)


# ─── Limiter Instance ─────────────────────────────────────────────────────────

limiter = Limiter(
    key_func=_get_real_ip,
    storage_uri=settings.REDIS_URL,
    default_limits=["100/minute"],
    # swallow_errors=True keeps the app up if Redis is temporarily unavailable
    swallow_errors=True,
)

# ─── Rate limit constants (import these in routers) ──────────────────────────

RATE_AUTH      = "10/minute"     # Login, refresh (brute-force protection)
RATE_DEFAULT   = "100/minute"    # General API endpoints
RATE_UPLOADS   = "20/minute"     # File upload endpoints
RATE_REPORTS   = "15/minute"     # Heavy report/export endpoints


# ─── Exception Handler ────────────────────────────────────────────────────────

def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    """
    Custom 429 response that matches the project's standard error envelope.
    """
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code":    "RATE_LIMIT_EXCEEDED",
                "message": f"Too many requests. Limit: {exc.detail}. Please slow down.",
            },
        },
        headers={"Retry-After": "60"},
    )

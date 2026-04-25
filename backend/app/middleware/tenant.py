"""
AI-HRMS — TenantMiddleware

Resolves which tenant a request belongs to and injects it into
``request.state`` so all downstream handlers and dependencies can
access it without hitting the database again.

Resolution order:
  1. ``X-Tenant-Slug`` request header   (e.g. API clients)
  2. Subdomain of ``Host`` header        (e.g. acme.hrms.app → slug "acme")
  3. Falls back to DEFAULT_TENANT_SLUG  (single-tenant / dev mode)

Endpoints under ``/health``, ``/docs``, ``/redoc``, ``/openapi.json``
are excluded from tenant resolution.
"""

import re
import uuid

import structlog
from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.tenant import Tenant

logger = structlog.get_logger(__name__)

# Paths that do NOT need a tenant context
_BYPASS_PATHS: set[str] = {
    "/health",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/favicon.ico",
}

# Regex to extract subdomain: "acme.hrms.app" → "acme"
_SUBDOMAIN_RE = re.compile(r"^([a-z0-9-]+)\.[^.]+\.[^.]+$")


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Starlette/FastAPI middleware that resolves the current tenant from
    the request and stores it in ``request.state``:

    - ``request.state.tenant_id``   (uuid.UUID)
    - ``request.state.tenant_slug`` (str)
    - ``request.state.tenant``      (Tenant ORM object)
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        # Skip resolution for infrastructure / docs paths
        if request.url.path in _BYPASS_PATHS or request.url.path.startswith("/static"):
            return await call_next(request)

        slug = self._resolve_slug(request)

        if not slug:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": {
                        "code":    "TENANT_REQUIRED",
                        "message": "Tenant slug could not be resolved. "
                                   "Provide the X-Tenant-Slug header.",
                    },
                },
            )

        # Look up tenant in DB
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Tenant).where(
                    Tenant.slug == slug,
                    Tenant.is_active.is_(True),
                )
            )
            tenant: Tenant | None = result.scalar_one_or_none()

        if tenant is None:
            logger.warning("Tenant not found or inactive", slug=slug)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "success": False,
                    "error": {
                        "code":    "TENANT_NOT_FOUND",
                        "message": f"Tenant '{slug}' does not exist or is inactive.",
                    },
                },
            )

        # Inject into request state for downstream use
        request.state.tenant_id   = tenant.id
        request.state.tenant_slug = tenant.slug
        request.state.tenant      = tenant

        logger.debug("Tenant resolved", slug=slug, tenant_id=str(tenant.id))
        return await call_next(request)

    @staticmethod
    def _resolve_slug(request: Request) -> str | None:
        """Try each resolution strategy in order."""
        # 1. Explicit header
        slug = request.headers.get("X-Tenant-Slug", "").strip().lower()
        if slug:
            return slug

        # 2. Subdomain
        host = request.headers.get("Host", "").split(":")[0]  # strip port
        match = _SUBDOMAIN_RE.match(host)
        if match:
            subdomain = match.group(1)
            # Ignore www and common non-tenant subdomains
            if subdomain not in {"www", "api", "app", "portal"}:
                return subdomain

        # 3. Default (single-tenant / dev)
        if settings.DEFAULT_TENANT_SLUG:
            return settings.DEFAULT_TENANT_SLUG

        return None

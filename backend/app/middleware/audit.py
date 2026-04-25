"""
AI-HRMS — AuditMiddleware

After every mutating request (POST / PUT / PATCH / DELETE) that
returns a 2xx response, this middleware fires an async background
task to write one record to ``audit_logs``.

It captures:
- tenant_id   — from request.state (set by TenantMiddleware)
- user_id     — decoded from the access_token cookie / Bearer header
- action      — derived from HTTP method (create / update / delete)
- resource    — first meaningful path segment after /api/v1/
- resource_id — UUID path segment, if present
- ip_address  — real client IP (respects X-Forwarded-For)
- user_agent  — User-Agent header
- request_id  — X-Request-ID header

The write runs in ``asyncio.create_task`` so it never blocks the
response delivery to the client.
"""

import asyncio
import re
import uuid
from datetime import datetime, timezone

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.database import AsyncSessionLocal
from app.models.audit import AuditLog

logger = structlog.get_logger(__name__)

# Methods that trigger an audit entry
_AUDIT_METHODS: set[str] = {"POST", "PUT", "PATCH", "DELETE"}

# Path segments that should NOT be audited (infrastructure / auth refresh)
_SKIP_SEGMENTS: set[str] = {"health", "docs", "redoc", "openapi.json", "static"}

# Map HTTP method → audit action verb
_METHOD_TO_ACTION: dict[str, str] = {
    "POST":   "create",
    "PUT":    "update",
    "PATCH":  "update",
    "DELETE": "delete",
}

# Regex to find a UUID in the URL path
_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)


def _extract_resource(path: str) -> tuple[str, uuid.UUID | None]:
    """
    Parse a URL path like ``/api/v1/employees/abc-uuid/documents``
    into ``("employees", UUID("abc-uuid"))``.
    """
    segments = [s for s in path.strip("/").split("/") if s]
    # Strip common prefixes
    while segments and segments[0] in {"api", "v1", "v2"}:
        segments.pop(0)

    resource = segments[0] if segments else "unknown"

    # Look for a UUID in the remaining segments
    resource_id: uuid.UUID | None = None
    for seg in segments[1:]:
        m = _UUID_RE.fullmatch(seg)
        if m:
            try:
                resource_id = uuid.UUID(seg)
            except ValueError:
                pass
            break

    return resource, resource_id


def _get_real_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_user_id_from_state(request: Request) -> uuid.UUID | None:
    """Try to read the user_id FastAPI may have stored on request.state."""
    return getattr(request.state, "user_id", None)


async def _write_audit_log(
    tenant_id:   uuid.UUID | None,
    user_id:     uuid.UUID | None,
    user_email:  str | None,
    action:      str,
    resource:    str,
    resource_id: uuid.UUID | None,
    ip_address:  str,
    user_agent:  str,
    request_id:  str | None,
) -> None:
    """Insert a single audit_log row. Runs in an asyncio task."""
    try:
        async with AsyncSessionLocal() as db:
            log = AuditLog(
                tenant_id=tenant_id or uuid.UUID(int=0),
                user_id=user_id,
                user_email=user_email,
                action=action,
                resource=resource,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None,
                request_id=request_id,
                created_at=datetime.now(timezone.utc),
            )
            db.add(log)
            await db.commit()
    except Exception as exc:
        # Audit failures must never crash the application
        logger.error("Audit log write failed", error=str(exc), resource=resource)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Non-blocking audit middleware.

    Only fires for mutating methods (POST/PUT/PATCH/DELETE) that
    return a successful (2xx) response.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        response = await call_next(request)

        method = request.method.upper()
        if method not in _AUDIT_METHODS:
            return response

        path = request.url.path
        resource, _ = _extract_resource(path)
        if resource in _SKIP_SEGMENTS:
            return response

        # Only audit successful mutations
        if not (200 <= response.status_code < 300):
            return response

        # Collect context
        tenant_id:  uuid.UUID | None = getattr(request.state, "tenant_id",  None)
        user_id:    uuid.UUID | None = getattr(request.state, "user_id",    None)
        user_email: str | None       = getattr(request.state, "user_email", None)

        resource_name, resource_id = _extract_resource(path)
        action     = _METHOD_TO_ACTION.get(method, "mutate")
        ip_address = _get_real_ip(request)
        user_agent = request.headers.get("User-Agent", "")
        request_id = request.headers.get("X-Request-ID")

        # Fire and forget — does NOT block the response
        asyncio.create_task(
            _write_audit_log(
                tenant_id=tenant_id,
                user_id=user_id,
                user_email=user_email,
                action=action,
                resource=resource_name,
                resource_id=resource_id,
                ip_address=ip_address,
                user_agent=user_agent,
                request_id=request_id,
            )
        )

        return response

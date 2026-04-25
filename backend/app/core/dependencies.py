"""
AI-HRMS — FastAPI reusable dependencies.

All route handlers use these via Depends().
"""

import uuid
from typing import Annotated

import structlog
from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.redis import get_redis
from app.core.security import decode_token
from app.models.tenant import Permission, Role, RolePermission, User, UserRole

logger = structlog.get_logger(__name__)

# ─── Optional Bearer extractor (does NOT auto-raise 403) ─────────────────────
_bearer = HTTPBearer(auto_error=False)


# ─── Database ─────────────────────────────────────────────────────────────────

async def get_db() -> AsyncSession:  # type: ignore[return]
    """
    Yield an async database session for the duration of a request.
    Auto-commits on success, rolls back on any exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


DbDep = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


# ─── Token extraction ─────────────────────────────────────────────────────────

def _extract_token(
    bearer: HTTPAuthorizationCredentials | None,
    cookie_token: str | None,
) -> str:
    """
    Pull the raw JWT from either:
      1. Authorization: Bearer <token>   header, OR
      2. access_token                    httpOnly cookie.

    Raises 401 if neither is present.
    """
    if bearer and bearer.credentials:
        return bearer.credentials
    if cookie_token:
        return cookie_token
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication credentials were not provided.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ─── Current User ─────────────────────────────────────────────────────────────

async def get_current_user(
    db:           DbDep,
    redis:        RedisDep,
    bearer:       Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)] = None,
    cookie_token: Annotated[str | None, Cookie(alias="access_token")] = None,
) -> User:
    """
    Resolve the authenticated user from the request token.

    Token is read from (in priority order):
      1. ``Authorization: Bearer <token>`` header
      2. ``access_token`` httpOnly cookie

    Eagerly loads the user's roles and permissions so downstream handlers
    don't need extra DB queries.

    Raises:
        401 — missing, expired, or tampered token
        401 — user no longer exists in the database
    """
    raw_token = _extract_token(bearer, cookie_token)
    payload   = decode_token(raw_token)

    user_id: str = payload["sub"]
    jti: str | None = payload.get("jti")

    # Check token blacklist (logout before expiry)
    if jti:
        is_blacklisted = await redis.exists(f"hrms:blacklist:{jti}")
        if is_blacklisted:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been invalidated. Please log in again.",
            )

    result = await db.execute(
        select(User)
        .where(User.id == uuid.UUID(user_id))
        .options(
            selectinload(User.user_roles).selectinload(UserRole.role).selectinload(
                Role.role_permissions
            ).selectinload(RolePermission.permission)
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account no longer exists.",
        )
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Extends ``get_current_user`` with an active-account check.

    Raises:
        403 — user account is disabled (is_active = False)
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact HR.",
        )
    return current_user


# Convenient annotated shorthand
CurrentUser = Annotated[User, Depends(get_current_active_user)]


# ─── Tenant ───────────────────────────────────────────────────────────────────

def get_tenant_id(request: Request) -> uuid.UUID:
    """
    Extract the tenant_id that TenantMiddleware has already resolved and
    stored in ``request.state.tenant_id``.

    Raises:
        400 — tenant context is missing (middleware wasn't applied)
    """
    tenant_id: uuid.UUID | None = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant context could not be resolved.",
        )
    return tenant_id


TenantIdDep = Annotated[uuid.UUID, Depends(get_tenant_id)]


# ─── Permission Guard ─────────────────────────────────────────────────────────

def require_permission(module: str, action: str):
    """
    Dependency factory that enforces RBAC.

    Usage::

        @router.delete("/{id}")
        async def delete_employee(
            _: Annotated[None, Depends(require_permission("employee_management", "delete"))],
            ...
        ):

    Raises:
        403 — authenticated user lacks the required permission
    """
    async def _check(
        current_user: Annotated[User, Depends(get_current_active_user)],
    ) -> None:
        # Super-admins bypass all permission checks
        if current_user.is_superadmin:
            return

        # Collect all permissions granted through any of the user's roles
        granted: set[str] = set()
        for user_role in current_user.user_roles:
            for rp in user_role.role.role_permissions:
                p: Permission = rp.permission
                granted.add(f"{p.module_name}.{p.action}")

        if f"{module}.{action}" not in granted:
            logger.warning(
                "Permission denied",
                user_id=str(current_user.id),
                required=f"{module}.{action}",
                granted=list(granted),
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You do not have '{action}' permission for module '{module}'.",
            )

    return Depends(_check)


# ─── Superadmin guard ────────────────────────────────────────────────────────

async def require_superadmin(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """Allow only super-admins. Raises 403 otherwise."""
    if not current_user.is_superadmin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint requires super-admin privileges.",
        )
    return current_user


SuperAdminDep = Annotated[User, Depends(require_superadmin)]

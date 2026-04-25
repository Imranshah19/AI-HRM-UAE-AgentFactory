"""
AI-HRMS — Auth service layer.

All business logic lives here; the router delegates to these functions.
"""

import hashlib
import uuid
from datetime import timedelta, timezone, datetime

import structlog
from fastapi import HTTPException, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.redis import login_attempts_key, refresh_token_key
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.models.tenant import Permission, Role, RolePermission, User, UserRole
from app.api.v1.auth.schemas import (
    PermissionOut,
    RoleOut,
    TokenResponse,
    UserMeResponse,
)

logger = structlog.get_logger(__name__)

# Maximum failed login attempts before temporary lockout
_MAX_ATTEMPTS = 5
_LOCKOUT_SECONDS = 900  # 15 minutes


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _hash_token(token: str) -> str:
    """SHA-256 hash of a token for safe storage in Redis."""
    return hashlib.sha256(token.encode()).hexdigest()


async def _get_user_with_roles(
    db: AsyncSession,
    *,
    email: str,
    tenant_id: uuid.UUID,
) -> User | None:
    """Fetch a user by email + tenant, eagerly loading roles and permissions."""
    result = await db.execute(
        select(User)
        .where(User.email == email.lower().strip(), User.tenant_id == tenant_id)
        .options(
            selectinload(User.user_roles)
            .selectinload(UserRole.role)
            .selectinload(Role.role_permissions)
            .selectinload(RolePermission.permission)
        )
    )
    return result.scalar_one_or_none()


def _build_token_pair(user: User) -> tuple[str, str]:
    """Create access + refresh tokens for a user."""
    payload = {
        "sub":       str(user.id),
        "tenant_id": str(user.tenant_id),
        "email":     user.email,
    }
    return (
        create_access_token(payload),
        create_refresh_token(payload),
    )


def _collect_permissions(user: User) -> list[PermissionOut]:
    seen: set[str] = set()
    perms: list[PermissionOut] = []
    for ur in user.user_roles:
        for rp in ur.role.role_permissions:
            p: Permission = rp.permission
            key = f"{p.module_name}.{p.action}"
            if key not in seen:
                seen.add(key)
                perms.append(PermissionOut(module_name=p.module_name, action=p.action))
    return perms


# ─── Login ────────────────────────────────────────────────────────────────────

async def login(
    email:     str,
    password:  str,
    tenant_id: uuid.UUID,
    db:        AsyncSession,
    redis:     Redis,
) -> tuple[str, str]:
    """
    Authenticate a user and return (access_token, refresh_token).

    Raises:
        401 — invalid credentials
        403 — account inactive or locked
    """
    # Brute-force protection
    attempt_key = login_attempts_key(f"{tenant_id}:{email.lower()}")
    attempts = await redis.get(attempt_key)
    if attempts and int(attempts) >= _MAX_ATTEMPTS:
        ttl = await redis.ttl(attempt_key)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account temporarily locked due to too many failed attempts. "
                   f"Try again in {ttl} seconds.",
        )

    user = await _get_user_with_roles(db, email=email, tenant_id=tenant_id)

    # Use a constant-time-ish comparison path to avoid user enumeration
    _invalid_credentials = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if user is None:
        # Still verify a dummy hash to prevent timing attacks
        verify_password(password, hash_password("dummy"))
        # Increment failed attempts for the email even if user doesn't exist
        await redis.incr(attempt_key)
        await redis.expire(attempt_key, _LOCKOUT_SECONDS)
        raise _invalid_credentials

    if not verify_password(password, user.hashed_password):
        await redis.incr(attempt_key)
        await redis.expire(attempt_key, _LOCKOUT_SECONDS)
        logger.warning("Failed login attempt", user_id=str(user.id), email=email)
        raise _invalid_credentials

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact HR.",
        )

    # Clear failed attempts on success
    await redis.delete(attempt_key)

    # Issue tokens
    access_token, refresh_token = _build_token_pair(user)

    # Store hashed refresh token in Redis with TTL
    rt_key = refresh_token_key(str(user.id))
    await redis.setex(
        rt_key,
        timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS),
        _hash_token(refresh_token),
    )

    # Update last_login in DB
    user.last_login = datetime.now(timezone.utc)
    user.failed_login_attempts = 0
    db.add(user)

    logger.info("User logged in", user_id=str(user.id), email=user.email)
    return access_token, refresh_token


# ─── Refresh Tokens ───────────────────────────────────────────────────────────

async def refresh_tokens(
    refresh_token: str,
    db:            AsyncSession,
    redis:         Redis,
) -> str:
    """
    Validate a refresh token and issue a new access token.

    Implements refresh token rotation: the supplied token is verified
    against the hash stored in Redis, then a fresh access token is returned.
    The refresh token itself is NOT rotated (caller receives the same one).

    Raises:
        401 — token invalid, expired, or not found in Redis
    """
    payload = decode_refresh_token(refresh_token)
    user_id = payload["sub"]

    # Verify stored hash matches
    stored_hash = await redis.get(refresh_token_key(user_id))
    if not stored_hash or stored_hash != _hash_token(refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token is invalid or has already been used.",
        )

    result = await db.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or inactive.",
        )

    new_access_token = create_access_token(
        {"sub": str(user.id), "tenant_id": str(user.tenant_id), "email": user.email}
    )
    logger.debug("Token refreshed", user_id=user_id)
    return new_access_token


# ─── Logout ───────────────────────────────────────────────────────────────────

async def logout(user_id: str, redis: Redis) -> None:
    """Invalidate the stored refresh token so it can no longer be used."""
    await redis.delete(refresh_token_key(user_id))
    logger.info("User logged out", user_id=user_id)


# ─── Change Password ──────────────────────────────────────────────────────────

async def change_password(
    user:         User,
    old_password: str,
    new_password: str,
    db:           AsyncSession,
    redis:        Redis,
) -> None:
    """
    Verify old_password then update to new_password.
    Also invalidates all existing refresh tokens (forces re-login).

    Raises:
        400 — old password is incorrect
        400 — new password is same as old
    """
    if not verify_password(old_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    if verify_password(new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from the current password.",
        )

    user.hashed_password       = hash_password(new_password)
    user.password_changed_at   = datetime.now(timezone.utc)
    db.add(user)

    # Force re-login on all devices
    await redis.delete(refresh_token_key(str(user.id)))

    logger.info("Password changed", user_id=str(user.id))


# ─── My Profile ───────────────────────────────────────────────────────────────

async def get_my_profile(user: User) -> UserMeResponse:
    """
    Build the UserMeResponse from the already-loaded User ORM object.
    The caller (dependency) must have eagerly loaded roles + permissions.
    """
    roles = [
        RoleOut(
            id=ur.role.id,
            name=ur.role.name,
            is_system_role=ur.role.is_system_role,
        )
        for ur in user.user_roles
    ]
    permissions = _collect_permissions(user)

    return UserMeResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        avatar_url=user.avatar_url,
        tenant_id=user.tenant_id,
        is_superadmin=user.is_superadmin,
        roles=roles,
        permissions=permissions,
    )

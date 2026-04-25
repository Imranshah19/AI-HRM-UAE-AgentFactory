"""
AI-HRMS — Auth router.

Endpoints:
  POST   /api/v1/auth/login           → issue tokens (set httpOnly cookies)
  POST   /api/v1/auth/refresh         → rotate access token
  POST   /api/v1/auth/logout          → clear cookies + invalidate refresh token
  GET    /api/v1/auth/me              → current user profile + permissions
  POST   /api/v1/auth/change-password → update password
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from redis.asyncio import Redis

from app.core.config import settings
from app.core.dependencies import CurrentUser, DbDep, RedisDep, get_tenant_id
from app.core.rate_limit import RATE_AUTH, limiter
from app.api.v1.auth import service
from app.api.v1.auth.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutResponse,
    MessageResponse,
    RefreshRequest,
    TokenResponse,
    UserMeResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Cookie configuration (read from settings)
_COOKIE_OPTS = dict(
    httponly=True,
    secure=settings.COOKIE_SECURE,
    samesite=settings.COOKIE_SAMESITE,
    path="/",
)


# ─── POST /auth/login ─────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login and obtain tokens",
)
@limiter.limit(RATE_AUTH)
async def login(
    request:   Request,       # required by slowapi
    response:  Response,
    body:      LoginRequest,
    db:        DbDep,
    redis:     RedisDep,
    tenant_id: Annotated[object, Depends(get_tenant_id)] = None,
) -> TokenResponse:
    """
    Authenticate with email + password.

    On success:
    - Sets **httpOnly** cookies: ``access_token`` and ``refresh_token``
    - Returns ``TokenResponse`` in the body (for API clients that can't read cookies)
    """
    import uuid
    from app.core.config import settings as s

    access_token, refresh_token = await service.login(
        email=body.email,
        password=body.password,
        tenant_id=tenant_id,  # type: ignore[arg-type]
        db=db,
        redis=redis,
    )

    # Set httpOnly cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_COOKIE_OPTS,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        max_age=s.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **_COOKIE_OPTS,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ─── POST /auth/refresh ───────────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh access token",
)
@limiter.limit(RATE_AUTH)
async def refresh(
    request:        Request,
    response:       Response,
    db:             DbDep,
    redis:          RedisDep,
    body:           RefreshRequest | None = None,
    cookie_refresh: Annotated[str | None, Cookie(alias="refresh_token")] = None,
) -> TokenResponse:
    """
    Exchange a refresh token for a new access token.

    Token is read from (in priority order):
    1. ``refresh_token`` cookie
    2. Request body ``{ "refresh_token": "..." }``
    """
    raw_refresh = cookie_refresh or (body.refresh_token if body else None)
    if not raw_refresh:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No refresh token provided.",
        )

    new_access_token = await service.refresh_tokens(raw_refresh, db, redis)

    response.set_cookie(
        key="access_token",
        value=new_access_token,
        max_age=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_COOKIE_OPTS,
    )

    return TokenResponse(
        access_token=new_access_token,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ─── POST /auth/logout ────────────────────────────────────────────────────────

@router.post(
    "/logout",
    response_model=LogoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Log out and invalidate tokens",
)
async def logout(
    response:     Response,
    current_user: CurrentUser,
    redis:        RedisDep,
) -> LogoutResponse:
    """
    Invalidate the user's refresh token in Redis and clear both cookies.
    """
    await service.logout(str(current_user.id), redis)

    response.delete_cookie(key="access_token",  path="/")
    response.delete_cookie(key="refresh_token", path="/")

    return LogoutResponse()


# ─── GET /auth/me ─────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=UserMeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
)
async def me(current_user: CurrentUser) -> UserMeResponse:
    """
    Return the authenticated user's profile including all roles and permissions.
    """
    return await service.get_my_profile(current_user)


# ─── POST /auth/change-password ───────────────────────────────────────────────

@router.post(
    "/change-password",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Change account password",
)
@limiter.limit(RATE_AUTH)
async def change_password(
    request:      Request,
    body:         ChangePasswordRequest,
    current_user: CurrentUser,
    db:           DbDep,
    redis:        RedisDep,
) -> MessageResponse:
    """
    Change the authenticated user's password.

    - Verifies the current (old) password before accepting the new one.
    - Invalidates all existing sessions after the change (forces re-login).
    """
    await service.change_password(
        user=current_user,
        old_password=body.old_password,
        new_password=body.new_password,
        db=db,
        redis=redis,
    )
    return MessageResponse(
        message="Password changed successfully. Please log in again with your new password."
    )

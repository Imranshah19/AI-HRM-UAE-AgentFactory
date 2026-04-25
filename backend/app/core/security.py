"""
AI-HRMS — Security utilities: password hashing and JWT token management.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

logger = structlog.get_logger(__name__)

# ─── Password Hashing ─────────────────────────────────────────────────────────

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash of the given plain-text password."""
    return _pwd_context.hash(plain_password)


# Alias used in tests and some older code paths
get_password_hash = hash_password


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Return True if plain_password matches the stored bcrypt hash."""
    return _pwd_context.verify(plain_password, hashed_password)


# ─── JWT Tokens ───────────────────────────────────────────────────────────────

_ALGORITHM = settings.JWT_ALGORITHM
_SECRET    = settings.JWT_SECRET_KEY


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Payload claims (must include ``sub`` = user_id string).
        expires_delta: Override the default 15-minute expiry.

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        **data,
        "exp":  expire,
        "iat":  datetime.now(timezone.utc),
        "type": "access",
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    """
    Create a signed JWT refresh token (7-day TTL).

    Args:
        data: Payload claims (must include ``sub`` = user_id string).

    Returns:
        Encoded JWT string.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS
    )
    payload = {
        **data,
        "exp":  expire,
        "iat":  datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, _SECRET, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT token.

    Raises:
        :class:`fastapi.HTTPException` 401 if the token is invalid, expired,
        or has been tampered with.

    Returns:
        The decoded payload dictionary.
    """
    from fastapi import HTTPException, status

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        if payload.get("sub") is None:
            logger.warning("JWT missing 'sub' claim")
            raise credentials_exc
        return payload
    except JWTError as exc:
        logger.warning("JWT decode failed", error=str(exc))
        raise credentials_exc from exc


def decode_refresh_token(token: str) -> dict[str, Any]:
    """
    Decode a refresh token and assert its type is 'refresh'.

    Raises:
        :class:`fastapi.HTTPException` 401 if invalid or wrong type.
    """
    from fastapi import HTTPException, status

    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. A refresh token is required.",
        )
    return payload

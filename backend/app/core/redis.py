"""
AI-HRMS — Async Redis client (shared singleton).
Used by auth (refresh tokens), rate limiting, and caching.
"""

from redis.asyncio import Redis, ConnectionPool

from app.core.config import settings

# ─── Connection Pool (created once at import time) ────────────────────────────

_pool: ConnectionPool = ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=20,
    decode_responses=True,
)


def get_redis() -> Redis:
    """
    Return a Redis client using the shared async connection pool.

    Usage as a FastAPI dependency::

        @router.get("/example")
        async def example(redis: Redis = Depends(get_redis)):
            value = await redis.get("my_key")
    """
    return Redis(connection_pool=_pool)


# ─── Key helpers ─────────────────────────────────────────────────────────────

def refresh_token_key(user_id: str) -> str:
    """Redis key that stores the hashed refresh token for a user."""
    return f"hrms:refresh:{user_id}"


def blacklist_key(jti: str) -> str:
    """Redis key for a blacklisted access token (logout before expiry)."""
    return f"hrms:blacklist:{jti}"


def login_attempts_key(email: str) -> str:
    """Redis key tracking failed login attempts for brute-force protection."""
    return f"hrms:login_attempts:{email}"

"""
AI-HRMS — High-level Redis cache helpers.
Wraps get_redis() with JSON serialization for common cache operations.
"""
import json
from typing import Any, Optional

from app.core.redis import get_redis


async def cache_get(key: str) -> Optional[Any]:
    """Get a JSON-serialized value from cache. Returns None if missing/expired."""
    redis = get_redis()
    raw = await redis.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def cache_set(key: str, value: Any, ttl: int = 300) -> None:
    """Set a JSON-serialized value with TTL in seconds (default 5 min)."""
    redis = get_redis()
    await redis.setex(key, ttl, json.dumps(value, default=str))


async def cache_delete(key: str) -> None:
    """Delete a cache key."""
    redis = get_redis()
    await redis.delete(key)


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a pattern (e.g. 'hrms:payroll:*'). Returns count deleted."""
    redis = get_redis()
    keys = await redis.keys(pattern)
    if keys:
        return await redis.delete(*keys)
    return 0


# Key namespaces
def cache_key_employee(tenant_id: str, employee_id: str) -> str:
    return f"hrms:employee:{tenant_id}:{employee_id}"

def cache_key_dashboard(tenant_id: str) -> str:
    return f"hrms:dashboard:{tenant_id}"

def cache_key_payroll(tenant_id: str, run_id: str) -> str:
    return f"hrms:payroll:{tenant_id}:{run_id}"

def cache_key_reports(tenant_id: str, report_type: str, period: str) -> str:
    return f"hrms:reports:{tenant_id}:{report_type}:{period}"

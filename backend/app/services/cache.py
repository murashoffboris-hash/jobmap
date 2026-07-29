"""Typed Redis caching service.

Provides async-friendly cache operations with JSON serialisation
and configurable TTL. Used to offload repeat DB queries (vacancy lists,
health checks) from PostgreSQL under load.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Optional, TypeVar

from redis.asyncio import Redis

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ── Connection singleton ──────────────────────────────────────────
_redis: Optional[Redis] = None


async def get_redis() -> Redis:
    """Return a shared async Redis connection, creating it on first call."""
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def close_redis() -> None:
    """Gracefully close the Redis connection (call during app shutdown)."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


# ── Cache primitives ──────────────────────────────────────────────

async def cache_get(key: str) -> Optional[Any]:
    """Return the deserialised value at *key*, or *None* if missing."""
    try:
        r = await get_redis()
        raw = await r.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        logger.warning("cache_get(%s) failed, returning None", key, exc_info=True)
        return None


async def cache_set(
    key: str,
    value: Any,
    ttl_seconds: int = 30,
) -> None:
    """Store *value* under *key* with a TTL in seconds."""
    try:
        r = await get_redis()
        await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception:
        logger.warning("cache_set(%s) failed", key, exc_info=True)


async def cache_delete(*keys: str) -> int:
    """Delete one or more keys. Returns the number of keys actually removed."""
    if not keys:
        return 0
    try:
        r = await get_redis()
        return await r.delete(*keys)
    except Exception:
        logger.warning("cache_delete(%s) failed", keys, exc_info=True)
        return 0


async def cache_delete_pattern(pattern: str) -> int:
    """Delete all keys matching a glob pattern (e.g. ``vacancy_list:*``).

    Uses SCAN under the hood — safe for production with large key spaces.
    Returns the number of keys removed.
    """
    try:
        r = await get_redis()
        deleted = 0
        async for key in r.scan_iter(match=pattern):
            deleted += await r.delete(key)
        return deleted
    except Exception:
        logger.warning(
            "cache_delete_pattern(%s) failed", pattern, exc_info=True,
        )
        return 0


# ── Cache metrics (lightweight, no external deps) ─────────────────

_cache_hits = 0
_cache_misses = 0


async def record_cache_hit() -> None:
    """Increment the cache-hit counter (non-blocking, in-memory)."""
    global _cache_hits
    _cache_hits += 1


async def record_cache_miss() -> None:
    """Increment the cache-miss counter (non-blocking, in-memory)."""
    global _cache_misses
    _cache_misses += 1


async def get_cache_stats() -> dict:
    """Return current hit/miss counters."""
    return {"hits": _cache_hits, "misses": _cache_misses}

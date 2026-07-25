"""Health-check endpoint — lightweight, pool-friendly dependency checks.

Every health check previously opened a fresh ``asyncpg.connect()``,
exhausting PostgreSQL connections under load (>10 concurrent users).
Now reuses the application's SQLAlchemy async session factory and
caches results briefly so that burst health probes (k8s, load-balancers)
don't translate into DB connection storms.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.database import async_session_factory
from app.services.cache import cache_get, cache_set

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

HEALTH_CACHE_KEY = "health:check"
HEALTH_CACHE_TTL = 10  # seconds — short enough for alerts, long enough to absorb bursts


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    dependencies: dict[str, str]


async def _check_postgres() -> str:
    """Probe PostgreSQL via the shared async pool — no raw connection."""
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                text("SELECT PostGIS_Version()")
            )
            version = result.scalar_one()
            return f"ok (PostGIS {version})"
    except Exception as e:
        logger.warning("PostgreSQL health check failed: %s", e)
        return f"error: {e}"


async def _check_redis() -> str:
    """Probe Redis via the shared cache connection."""
    try:
        from app.services.cache import get_redis

        r = await get_redis()
        pong = await r.ping()
        return "ok" if pong else "error: no pong"
    except Exception as e:
        return f"error: {e}"


async def _collect_dependencies() -> dict[str, str]:
    """Gather all dependency statuses."""
    return {
        "postgresql": await _check_postgres(),
        "redis": await _check_redis(),
    }


@router.get("", response_model=HealthResponse)
async def health_check():
    """Health probe — cached for 10 s to survive burst traffic.

    At 500 concurrent users a naive probe-per-request would require 500
    simultaneous PostgreSQL connections.  This endpoint caps that to
    **one** probe every 10 seconds regardless of caller count.
    """
    cached = await cache_get(HEALTH_CACHE_KEY)
    if cached is not None:
        return HealthResponse(**cached)

    deps = await _collect_dependencies()
    status = "ok" if all(v.startswith("ok") for v in deps.values()) else "degraded"

    result = HealthResponse(
        status=status,
        service="jobmap-backend",
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=deps,
    )

    # Cache the serialised result
    await cache_set(
        HEALTH_CACHE_KEY,
        result.model_dump(),
        ttl_seconds=HEALTH_CACHE_TTL,
    )

    return result

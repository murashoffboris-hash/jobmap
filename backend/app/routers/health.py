"""Health-check endpoint — real dependency checks with mandatory + optional components."""

from __future__ import annotations

import logging
from datetime import datetime

import asyncpg
import httpx
import redis
from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])

__all__ = ["router"]


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    dependencies: dict[str, str]
    optional: dict[str, str]


async def _check_postgres() -> str:
    try:
        url = settings.database_url.replace("+asyncpg", "")
        conn = await asyncpg.connect(url)
        result = await conn.fetchval("SELECT PostGIS_Version()")
        await conn.close()
        return f"ok (PostGIS {result})"
    except Exception as e:
        return f"error: {e}"


async def _check_redis() -> str:
    try:
        r = redis.Redis.from_url(settings.REDIS_URL, socket_timeout=3)
        return "ok" if r.ping() else "error: no pong"
    except Exception as e:
        return f"error: {e}"


async def _check_nominatim() -> str:
    """Check Nominatim — tries primary URL first, then fallback."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.NOMINATIM_URL}/status.php")
            return f"ok (primary)" if resp.status_code == 200 else f"error: {resp.status_code}"
    except Exception:
        pass

    # Try fallback
    try:
        headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            resp = await client.get("https://nominatim.openstreetmap.org/status.php")
            return "ok (fallback)" if resp.status_code == 200 else f"degraded: fallback {resp.status_code}"
    except Exception as e:
        return f"degraded: {e}"


async def _check_osrm() -> str:
    """Check OSRM — tries primary URL first, then fallback."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OSRM_URL}/version")
            data = resp.json()
            return f"ok (v{data.get('osrm', '?')})"
    except Exception:
        pass

    # Try fallback
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get("https://router.project-osrm.org/version")
            data = resp.json()
            return f"ok (fallback v{data.get('osrm', '?')})"
    except Exception as e:
        return f"degraded: {e}"


@router.get("", response_model=HealthResponse)
async def health_check():
    """Health probe with real dependency checks.

    Mandatory: postgresql, redis — any error means 'down'.
    Optional:  nominatim, osrm — degraded is not fatal; the service still
               operates using fallback URLs.
    """
    deps = {
        "postgresql": await _check_postgres(),
        "redis": await _check_redis(),
    }

    optional = {
        "nominatim": await _check_nominatim(),
        "osrm": await _check_osrm(),
    }

    # Status is 'ok' if all mandatory deps are healthy.
    # Optional deps in 'degraded' state don't bring the service down.
    mandatory_ok = all(v.startswith("ok") for v in deps.values())
    status = "ok" if mandatory_ok else "degraded"

    return HealthResponse(
        status=status,
        service="jobmap-backend",
        timestamp=datetime.utcnow().isoformat(),
        dependencies=deps,
        optional=optional,
    )

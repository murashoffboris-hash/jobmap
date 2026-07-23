"""Health-check endpoint with real dependency checks."""

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


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: str
    dependencies: dict[str, str]


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
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.NOMINATIM_URL}/status.php")
            return "ok" if resp.status_code == 200 else f"error: {resp.status_code}"
    except Exception as e:
        return f"error: {e}"


async def _check_osrm() -> str:
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{settings.OSRM_URL}/version")
            data = resp.json()
            return f"ok (v{data.get('osrm', '?')})"
    except Exception as e:
        return f"error: {e}"


@router.get("", response_model=HealthResponse)
async def health_check():
    """Health probe with real dependency checks."""
    deps = {
        "postgresql": await _check_postgres(),
        "redis": await _check_redis(),
        "nominatim": await _check_nominatim(),
        "osrm": await _check_osrm(),
    }

    status = "ok" if all(v.startswith("ok") for v in deps.values()) else "degraded"

    return HealthResponse(
        status=status,
        service="jobmap-backend",
        timestamp=datetime.utcnow().isoformat(),
        dependencies=deps,
    )

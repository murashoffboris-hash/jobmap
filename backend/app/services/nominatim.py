"""Nominatim geocoding service with Redis cache, fallback chain, rate limiting, and logging."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any

import httpx
import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import GeocodingLog

logger = logging.getLogger(__name__)

# ── Redis cache TTL ──

_GEOCODE_CACHE_TTL: int = 86400  # 24 hours

# ── Rate limiter for public Nominatim (1 req/s per usage policy) ──

_fallback_lock = asyncio.Lock()
_fallback_last_request: float = 0.0
_FALLBACK_MIN_INTERVAL: float = 1.0  # seconds between requests

# ── Shared User-Agent header (required by OSM usage policy) ──

_USER_AGENT_HEADER = {"User-Agent": settings.NOMINATIM_USER_AGENT}


async def _get_redis() -> aioredis.Redis:
    """Return a Redis connection. Created on-demand; closed by the caller or pool."""
    return aioredis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def _cache_key(address: str) -> str:
    """Build a normalized Redis cache key for a geocoding query."""
    normalized = " ".join(address.lower().split())
    return f"geocode:{normalized}"


async def _rate_limited_fallback_request(
    client: httpx.AsyncClient, url: str, params: dict
) -> httpx.Response:
    """Make a rate-limited request to the public Nominatim fallback (1 req/s)."""
    global _fallback_last_request
    async with _fallback_lock:
        elapsed = time.monotonic() - _fallback_last_request
        if elapsed < _FALLBACK_MIN_INTERVAL:
            await asyncio.sleep(_FALLBACK_MIN_INTERVAL - elapsed)
        _fallback_last_request = time.monotonic()
    return await client.get(url, params=params)


def _build_search_params(address: str) -> dict[str, str]:
    """Build query params for a forward geocoding search request."""
    return {
        "q": address,
        "format": "jsonv2",
        "limit": "1",
        "addressdetails": "1",
    }


async def _try_geocode(
    url: str,
    params: dict[str, str],
    timeout: float,
    use_rate_limit: bool = False,
) -> httpx.Response | None:
    """Attempt a single geocoding request to one Nominatim instance.

    Returns the response on success, or None on any transport-level error.
    User-Agent header is sent on every request (OSM usage policy requirement).
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout, headers=_USER_AGENT_HEADER
        ) as client:
            if use_rate_limit:
                resp = await _rate_limited_fallback_request(client, url, params)
            else:
                resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
        logger.debug("Nominatim request to %s failed: %s", url, exc)
        return None


async def geocode_address(
    session: AsyncSession,
    address: str,
    vacancy_id: int | None = None,
) -> dict[str, Any] | None:
    """Geocode an address string via Nominatim with primary → fallback chain.

    Flow:
    1. Check Redis cache → return cached result on hit.
    2. Try primary Nominatim (NOMINATIM_URL, short timeout).
    3. On failure, fall back to public Nominatim (NOMINATIM_FALLBACK_URL)
       with rate limiting and full timeout.
    4. On success, store result in Redis (24h TTL) and geocoding_log table.
    5. On complete failure, log to geocoding_log and return None.

    Returns dict with lat, lon, osm_id, display_name, type, source or None.
    """
    # ── Step 0: Redis cache check ──
    cache_key = _cache_key(address)
    try:
        redis = await _get_redis()
        cached = await redis.get(cache_key)
        if cached:
            logger.debug("Redis cache HIT for '%s'", address)
            return json.loads(cached)
    except Exception:
        logger.debug("Redis unavailable for cache read, continuing without cache")

    # ── Build request params ──
    params = _build_search_params(address)
    search_path = f"{settings.NOMINATIM_URL}/search"
    fallback_path = f"{settings.NOMINATIM_FALLBACK_URL}/search"

    source: str = "none"
    data = None
    last_error: str | None = None

    # ── Step 1: primary (internal) Nominatim ──
    logger.debug("Geocoding '%s' via primary %s", address, search_path)
    resp = await _try_geocode(
        search_path, params, timeout=settings.NOMINATIM_TIMEOUT,
    )
    if resp is not None:
        data = resp.json()
        source = "primary"
    else:
        # ── Step 2: fallback to public Nominatim ──
        logger.info(
            "Primary Nominatim unavailable, falling back to %s for '%s'",
            settings.NOMINATIM_FALLBACK_URL, address,
        )
        resp = await _try_geocode(
            fallback_path, params,
            timeout=10.0,  # public Nominatim may be slower
            use_rate_limit=True,
        )
        if resp is not None:
            data = resp.json()
            source = "fallback"
        else:
            last_error = "Both primary and fallback Nominatim failed"

    # ── Handle result ──

    if not data:
        logger.warning("Geocoding failed for '%s': %s", address, last_error)
        log_entry = GeocodingLog(
            address_raw=address,
            success=False,
            vacancy_id=vacancy_id,
            error_message=last_error or "No results from Nominatim",
        )
        session.add(log_entry)
        await session.commit()
        return None

    result = data[0]
    geocode_result = {
        "lat": float(result["lat"]),
        "lon": float(result["lon"]),
        "osm_id": str(result.get("osm_id", "")),
        "display_name": result.get("display_name", ""),
        "type": result.get("type", ""),
        "source": source,
    }

    # ── Store in Redis cache ──
    try:
        redis = await _get_redis()
        await redis.setex(cache_key, _GEOCODE_CACHE_TTL, json.dumps(geocode_result))
        logger.debug("Stored geocode result in Redis for '%s'", address)
    except Exception:
        logger.debug("Redis unavailable for cache write, continuing without cache")

    # ── Log to DB ──
    log_entry = GeocodingLog(
        address_raw=address,
        address_normalized=result.get("display_name", ""),
        lat=geocode_result["lat"],
        lon=geocode_result["lon"],
        osm_id=str(result.get("osm_id", "")),
        result_type=result.get("type", ""),
        accuracy=None,
        raw_response=result,
        success=True,
        vacancy_id=vacancy_id,
    )
    session.add(log_entry)
    await session.commit()

    return geocode_result


async def reverse_geocode(lat: float, lon: float) -> dict[str, Any] | None:
    """Reverse geocode coordinates to an address — primary → fallback chain.

    Returns dict with lat, lon, display_name, type etc., or None on failure.
    """
    params = {
        "lat": str(lat),
        "lon": str(lon),
        "format": "jsonv2",
        "addressdetails": "1",
    }
    reverse_path = f"{settings.NOMINATIM_URL}/reverse"
    fallback_path = f"{settings.NOMINATIM_FALLBACK_URL}/reverse"

    # Step 1: primary
    resp = await _try_geocode(reverse_path, params, timeout=settings.NOMINATIM_TIMEOUT)
    if resp is not None:
        data = resp.json()
        if not data or "error" in data:
            logger.warning(
                "Nominatim reverse geocode returned no results for lat=%s, lon=%s",
                lat, lon,
            )
            return None
        return data

    # Step 2: fallback
    logger.info("Reverse geocode falling back to %s", settings.NOMINATIM_FALLBACK_URL)
    resp = await _try_geocode(
        fallback_path, params, timeout=10.0, use_rate_limit=True,
    )
    if resp is not None:
        data = resp.json()
        if not data or "error" in data:
            logger.warning(
                "Nominatim reverse geocode fallback returned no results for lat=%s, lon=%s",
                lat, lon,
            )
            return None
        return data

    logger.warning(
        "Reverse geocode failed for lat=%s, lon=%s — both primary and fallback", lat, lon,
    )
    return None

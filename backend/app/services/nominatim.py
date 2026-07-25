"""Nominatim geocoding service with caching, retries, fallback, and logging."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import GeocodingLog

logger = logging.getLogger(__name__)

# ── Rate limiter for public Nominatim (1 req/s per usage policy) ──

_fallback_lock = asyncio.Lock()
_fallback_last_request: float = 0.0
_FALLBACK_MIN_INTERVAL: float = 1.0  # seconds between requests


async def _rate_limited_fallback_request(client: httpx.AsyncClient, url: str, params: dict) -> httpx.Response:
    """Make a rate-limited request to the public Nominatim fallback (1 req/s)."""
    global _fallback_last_request
    async with _fallback_lock:
        elapsed = time.monotonic() - _fallback_last_request
        if elapsed < _FALLBACK_MIN_INTERVAL:
            await asyncio.sleep(_FALLBACK_MIN_INTERVAL - elapsed)
        _fallback_last_request = time.monotonic()
    return await client.get(url, params=params)


# ── Shared helpers ──

def _build_search_params(address: str) -> dict[str, str]:
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
    headers: dict[str, str] | None = None,
    use_rate_limit: bool = False,
) -> httpx.Response | None:
    """Attempt a single geocoding request to one Nominatim instance.

    Returns the response on success, or None on any transport-level error.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, headers=headers or {}) as client:
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

    Tries the primary (internal) Nominatim first with a short timeout.
    On failure, falls back to the public Nominatim with rate limiting.
    Logs every attempt to the geocoding_log table.

    Returns dict with lat, lon, osm_id, display_name, type, source or None.
    """
    params = _build_search_params(address)
    search_path = f"{settings.NOMINATIM_URL}/search"
    fallback_path = f"{settings.NOMINATIM_FALLBACK_URL}/search"
    fallback_headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}

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
            headers=fallback_headers,
            use_rate_limit=True,
        )
        if resp is not None:
            data = resp.json()
            source = "fallback"
        else:
            last_error = "Both primary and fallback Nominatim failed"

    # ── Handle result ──

    if not data:
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
    log_entry = GeocodingLog(
        address_raw=address,
        address_normalized=result.get("display_name", ""),
        lat=float(result["lat"]),
        lon=float(result["lon"]),
        osm_id=str(result.get("osm_id", "")),
        result_type=result.get("type", ""),
        accuracy=None,
        raw_response=result,
        success=True,
        vacancy_id=vacancy_id,
    )
    session.add(log_entry)
    await session.commit()
    return {
        "lat": log_entry.lat,
        "lon": log_entry.lon,
        "osm_id": log_entry.osm_id,
        "display_name": log_entry.address_normalized,
        "type": log_entry.result_type,
        "source": source,
    }


async def reverse_geocode(lat: float, lon: float) -> dict[str, Any] | None:
    """Reverse geocode coordinates to an address — primary → fallback chain."""
    params = {
        "lat": str(lat),
        "lon": str(lon),
        "format": "jsonv2",
        "addressdetails": "1",
    }
    reverse_path = f"{settings.NOMINATIM_URL}/reverse"
    fallback_path = f"{settings.NOMINATIM_FALLBACK_URL}/reverse"
    fallback_headers = {"User-Agent": settings.NOMINATIM_USER_AGENT}

    # Step 1: primary
    resp = await _try_geocode(reverse_path, params, timeout=settings.NOMINATIM_TIMEOUT)
    if resp is not None:
        return resp.json()

    # Step 2: fallback
    logger.info("Reverse geocode falling back to %s", settings.NOMINATIM_FALLBACK_URL)
    resp = await _try_geocode(
        fallback_path, params, timeout=10.0,
        headers=fallback_headers, use_rate_limit=True,
    )
    if resp is not None:
        return resp.json()

    logger.warning("Reverse geocode failed for lat=%s, lon=%s — both primary and fallback", lat, lon)
    return None

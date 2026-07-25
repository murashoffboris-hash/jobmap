"""OSRM routing service with table API support, caching, and fallback."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Full timeout for the OSRM response after fallback
OSRM_FULL_TIMEOUT = 15  # seconds


async def _try_osrm_request(url: str, params: dict, timeout: float) -> httpx.Response | None:
    """Attempt a single OSRM request. Returns the response or None on transport error."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            return resp
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as exc:
        logger.debug("OSRM request to %s failed: %s", url, exc)
        return None


def _build_coord_string(coordinates: list[tuple[float, float]]) -> str:
    """Build OSRM coordinate string: lon,lat;lon,lat;..."""
    return ";".join(f"{lon},{lat}" for lat, lon in coordinates)


async def get_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    *,
    profile: str = "car",
) -> dict[str, Any] | None:
    """Get route between two points via OSRM — primary → fallback chain.

    Returns dict with distance_m, duration_min, geometry or None.
    """
    coords = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    params = {"overview": "full", "geometries": "polyline", "annotations": "true"}

    primary_url = f"{settings.OSRM_URL}/route/v1/{profile}/{coords}"
    fallback_url = f"{settings.OSRM_FALLBACK_URL}/route/v1/{profile}/{coords}"

    # Step 1: primary
    resp = await _try_osrm_request(primary_url, params, timeout=settings.OSRM_TIMEOUT)
    if resp is None:
        logger.info("Primary OSRM unavailable, falling back to %s", settings.OSRM_FALLBACK_URL)
        resp = await _try_osrm_request(fallback_url, params, timeout=OSRM_FULL_TIMEOUT)

    if resp is None:
        logger.warning("OSRM route request failed — both primary and fallback")
        return None

    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        logger.warning("OSRM returned no routes: %s", data.get("code"))
        return None

    route = data["routes"][0]
    return {
        "distance_m": route.get("distance"),
        "duration_min": round(route.get("duration", 0) / 60, 1),
        "geometry": route.get("geometry"),
    }


async def get_distance_matrix(
    coordinates: list[tuple[float, float]],
    *,
    profile: str = "car",
    annotations: str = "distance,duration",
) -> dict[str, Any] | None:
    """Get distance matrix for multiple points via OSRM table API — primary → fallback.

    coordinates: list of (lat, lon) tuples.
    Returns dict with distances and durations matrices or None.
    """
    if len(coordinates) > 100:
        logger.error("OSRM table API supports max 100 coordinates")
        return None

    coord_str = _build_coord_string(coordinates)
    params = {"annotations": annotations}

    primary_url = f"{settings.OSRM_URL}/table/v1/{profile}/{coord_str}"
    fallback_url = f"{settings.OSRM_FALLBACK_URL}/table/v1/{profile}/{coord_str}"

    # Step 1: primary
    resp = await _try_osrm_request(primary_url, params, timeout=settings.OSRM_TIMEOUT)
    if resp is None:
        logger.info("Primary OSRM (table) unavailable, falling back to %s", settings.OSRM_FALLBACK_URL)
        resp = await _try_osrm_request(fallback_url, params, timeout=OSRM_FULL_TIMEOUT)

    if resp is None:
        logger.warning("OSRM table API failed — both primary and fallback")
        return None

    data = resp.json()
    if data.get("code") != "Ok":
        logger.warning("OSRM table API error: %s", data.get("code"))
        return None

    return {
        "durations": data.get("durations"),
        "distances": data.get("distances"),
    }

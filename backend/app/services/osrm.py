"""OSRM routing service with table API support and caching."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

OSRM_TIMEOUT = 15  # seconds


async def get_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    *,
    profile: str = "car",
) -> dict[str, Any] | None:
    """Get route between two points via OSRM.

    Returns dict with distance_m, duration_min, geometry or None.
    """
    coords = f"{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
    url = f"{settings.OSRM_URL}/route/v1/{profile}/{coords}"
    params = {"overview": "full", "geometries": "polyline", "annotations": "true"}

    try:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
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

    except httpx.HTTPError as exc:
        logger.error("OSRM route request failed: %s", exc)
        return None


async def get_distance_matrix(
    coordinates: list[tuple[float, float]],
    *,
    profile: str = "car",
    annotations: str = "distance,duration",
) -> dict[str, Any] | None:
    """Get distance matrix for multiple points via OSRM table API.

    coordinates: list of (lat, lon) tuples.
    Returns dict with distances and durations matrices or None.
    """
    if len(coordinates) > 100:
        logger.error("OSRM table API supports max 100 coordinates")
        return None

    coord_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
    url = f"{settings.OSRM_URL}/table/v1/{profile}/{coord_str}"
    params = {"annotations": annotations}

    try:
        async with httpx.AsyncClient(timeout=OSRM_TIMEOUT) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != "Ok":
                logger.warning("OSRM table API error: %s", data.get("code"))
                return None

            return {
                "durations": data.get("durations"),
                "distances": data.get("distances"),
            }

    except httpx.HTTPError as exc:
        logger.error("OSRM table API request failed: %s", exc)
        return None

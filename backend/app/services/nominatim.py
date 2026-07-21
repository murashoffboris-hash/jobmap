"""Nominatim geocoding service with caching, retries, and logging."""

from __future__ import annotations

import logging
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import GeocodingLog

logger = logging.getLogger(__name__)

# Timeouts
NOMINATIM_TIMEOUT = 10  # seconds
NOMINATIM_RETRIES = 3


async def geocode_address(
    session: AsyncSession,
    address: str,
    vacancy_id: int | None = None,
) -> dict[str, Any] | None:
    """Geocode an address string via Nominatim.

    Returns dict with lat, lon, osm_id, display_name, type or None.
    Logs every attempt to the geocoding_log table.
    """
    params = {
        "q": address,
        "format": "jsonv2",
        "limit": "1",
        "addressdetails": "1",
    }

    last_error = None
    for attempt in range(1, NOMINATIM_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=NOMINATIM_TIMEOUT) as client:
                resp = await client.get(f"{settings.NOMINATIM_URL}/search", params=params)
                resp.raise_for_status()
                data = resp.json()

                if not data:
                    log_entry = GeocodingLog(
                        address_raw=address,
                        success=False,
                        vacancy_id=vacancy_id,
                        error_message="No results from Nominatim",
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
                }

        except (httpx.TimeoutException, httpx.ConnectError) as exc:
            last_error = str(exc)
            logger.warning(
                "Nominatim geocoding attempt %d/%d failed: %s",
                attempt, NOMINATIM_RETRIES, exc,
            )
            if attempt < NOMINATIM_RETRIES:
                continue

    # All retries exhausted
    log_entry = GeocodingLog(
        address_raw=address,
        success=False,
        vacancy_id=vacancy_id,
        error_message=f"All retries exhausted: {last_error}",
    )
    session.add(log_entry)
    await session.commit()
    return None


async def reverse_geocode(lat: float, lon: float) -> dict[str, Any] | None:
    """Reverse geocode coordinates to an address."""
    params = {
        "lat": str(lat),
        "lon": str(lon),
        "format": "jsonv2",
        "addressdetails": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=NOMINATIM_TIMEOUT) as client:
            resp = await client.get(f"{settings.NOMINATIM_URL}/reverse", params=params)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPError as exc:
        logger.error("Nominatim reverse geocoding failed: %s", exc)
        return None

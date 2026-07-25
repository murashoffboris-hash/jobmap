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


class NominatimError(Exception):
    """Base exception for Nominatim service errors."""


class NominatimServiceError(NominatimError):
    """Upstream Nominatim service is unavailable or returned an error."""


class NominatimNoResults(NominatimError):
    """Nominatim returned zero results for the query."""


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

        except httpx.HTTPStatusError as exc:
            # Nominatim returned a non-2xx response — do not retry
            last_error = f"HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            logger.error(
                "Nominatim geocoding returned error status %d on attempt %d/%d",
                exc.response.status_code, attempt, NOMINATIM_RETRIES,
            )
            break

    # All retries exhausted
    log_entry = GeocodingLog(
        address_raw=address,
        success=False,
        vacancy_id=vacancy_id,
        error_message=f"All retries exhausted: {last_error}",
    )
    session.add(log_entry)
    await session.commit()
    raise NominatimServiceError(
        f"Nominatim geocoding failed after {attempt} attempt(s): {last_error}"
    )


async def reverse_geocode(lat: float, lon: float) -> dict[str, Any]:
    """Reverse geocode coordinates to an address.

    Returns:
        dict with lat, lon, display_name, type etc.

    Raises:
        NominatimServiceError: if the upstream service is unreachable or returns an error.
        NominatimNoResults: if no results found for the given coordinates.
    """
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
            data = resp.json()

            if not data or "error" in data:
                logger.warning(
                    "Nominatim reverse geocode returned no results for lat=%s, lon=%s",
                    lat, lon,
                )
                raise NominatimNoResults(
                    f"No results for coordinates lat={lat}, lon={lon}"
                )

            return data

    except httpx.TimeoutException as exc:
        logger.error("Nominatim reverse geocode timed out: %s", exc)
        raise NominatimServiceError(
            f"Nominatim reverse geocode timed out after {NOMINATIM_TIMEOUT}s"
        ) from exc

    except httpx.ConnectError as exc:
        logger.error("Nominatim reverse geocode connection failed: %s", exc)
        raise NominatimServiceError(
            f"Nominatim reverse geocode connection failed: {exc}"
        ) from exc

    except httpx.HTTPStatusError as exc:
        logger.error(
            "Nominatim reverse geocode returned HTTP %d: %s",
            exc.response.status_code, exc.response.text[:200],
        )
        raise NominatimServiceError(
            f"Nominatim reverse geocode returned HTTP {exc.response.status_code}"
        ) from exc

    except NominatimNoResults:
        raise

    except Exception as exc:
        logger.error("Nominatim reverse geocode unexpected error: %s", exc)
        raise NominatimServiceError(
            f"Nominatim reverse geocode unexpected error: {exc}"
        ) from exc

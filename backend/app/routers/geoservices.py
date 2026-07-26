"""Geoservices API — geocoding and routing endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.schemas import (
    GeocodeRequest,
    GeocodeResponse,
    RouteRequest,
    RouteResponse,
)
from app.services.nominatim import geocode_address, reverse_geocode
from app.services.osrm import get_route

router = APIRouter(prefix="/api/geo", tags=["geoservices"])


@router.post("/geocode", response_model=GeocodeResponse)
async def geocode(
    data: GeocodeRequest,
    session: AsyncSession = Depends(get_session),
):
    """Geocode an address via Nominatim (through backend).

    Returns 502 if both primary and fallback Nominatim are unavailable.
    Returns 404 if the address was not found.
    """
    result = await geocode_address(session, data.address)
    if not result:
        raise HTTPException(status_code=502, detail="Geocoding service unavailable")
    return GeocodeResponse(**result)


@router.get("/reverse", response_model=GeocodeResponse)
async def reverse(lat: float, lon: float):
    """Reverse geocode coordinates via Nominatim.

    Returns 502 if both primary and fallback Nominatim are unavailable.
    Returns 404 if coordinates were not found.
    """
    result = await reverse_geocode(lat, lon)
    if not result:
        raise HTTPException(status_code=502, detail="Geocoding service unavailable")
    return GeocodeResponse(
        lat=result.get("lat"),
        lon=result.get("lon"),
        display_name=result.get("display_name"),
        type=result.get("type"),
    )


@router.post("/route", response_model=RouteResponse)
async def route(data: RouteRequest):
    """Get route between two points via OSRM."""
    result = await get_route(
        data.origin_lat, data.origin_lon,
        data.dest_lat, data.dest_lon,
        profile=data.profile,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Route not found")
    return RouteResponse(**result)

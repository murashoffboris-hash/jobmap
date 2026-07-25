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
from app.services.nominatim import (
    geocode_address,
    reverse_geocode,
    NominatimNoResults,
    NominatimServiceError,
)
from app.services.osrm import get_route

router = APIRouter(prefix="/api/geo", tags=["geoservices"])


@router.post("/geocode", response_model=GeocodeResponse)
async def geocode(
    data: GeocodeRequest,
    session: AsyncSession = Depends(get_session),
):
    """Geocode an address via Nominatim (through backend)."""
    try:
        result = await geocode_address(session, data.address)
    except NominatimServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    if not result:
        raise HTTPException(status_code=404, detail="Address not found")
    return GeocodeResponse(**result)


@router.get("/reverse", response_model=GeocodeResponse)
async def reverse(lat: float, lon: float):
    """Reverse geocode coordinates via Nominatim."""
    try:
        result = await reverse_geocode(lat, lon)
    except NominatimNoResults:
        raise HTTPException(status_code=404, detail="Coordinates not found")
    except NominatimServiceError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
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

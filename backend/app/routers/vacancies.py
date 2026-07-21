"""Vacancies API — CRUD + geospatial search."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from geoalchemy2.functions import ST_Distance, ST_DWithin
from geoalchemy2.types import Geography
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import literal

from app.database import async_session_factory
from app.models import Vacancy, VacancyStatus, GeocodingLog
from app.schemas import (
    VacancyCreate,
    VacancyUpdate,
    VacancyResponse,
    VacancySearchRequest,
    VacancyGeoResult,
)
from app.services.nominatim import geocode_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vacancies", tags=["vacancies"])


def get_session():
    """Yield async database session."""
    return async_session_factory


def _vacancy_to_response(v: Vacancy) -> VacancyResponse:
    return VacancyResponse(
        id=v.id,
        title=v.title,
        description=v.description,
        status=v.status,
        address_normalized=v.address_normalized,
        location_lat=v.location_lat,
        location_lon=v.location_lon,
        salary_from=v.salary_from,
        salary_to=v.salary_to,
        salary_currency=v.salary_currency,
        schedule_type=v.schedule_type,
        contact_phone=v.contact_phone,
        exact_location_public=v.exact_location_public,
        created_at=v.created_at,
    )


@router.get("", response_model=list[VacancyGeoResult])
async def list_vacancies(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=500),
    category_id: Optional[int] = None,
    status: VacancyStatus = VacancyStatus.ACTIVE,
    session: AsyncSession = Depends(get_session),
):
    """Find vacancies within radius using PostGIS ST_DWithin.

    Uses geography type for accurate distance calculation.
    """
    point = f"POINT({lon} {lat})"
    radius_m = radius_km * 1000

    stmt = (
        select(
            Vacancy,
            func.round(
                ST_Distance(
                    Vacancy.location,
                    func.ST_GeogFromText(point),
                ).cast(Geography),
                1,
            ).label("distance_m"),
        )
        .where(
            ST_DWithin(
                Vacancy.location,
                func.ST_GeogFromText(point),
                radius_m,
            ),
            Vacancy.status == status,
        )
        .order_by(func.ST_Distance(Vacancy.location, func.ST_GeogFromText(point)))
    )

    if category_id:
        stmt = stmt.where(Vacancy.category_id == category_id)

    results = await session.execute(stmt)
    rows = results.all()

    return [
        VacancyGeoResult(
            id=v.id,
            title=v.title,
            location_lat=v.location_lat,
            location_lon=v.location_lon,
            distance_m=dist,
            salary_from=v.salary_from,
            salary_to=v.salary_to,
        )
        for v, dist in rows
    ]


@router.post("", response_model=VacancyResponse, status_code=201)
async def create_vacancy(
    data: VacancyCreate,
    session: AsyncSession = Depends(get_session),
    owner_id: int = Query(...),  # TODO: replace with auth dependency
):
    """Create a vacancy with optional geocoding of the address."""
    vacancy = Vacancy(
        owner_id=owner_id,
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        salary_from=data.salary_from,
        salary_to=data.salary_to,
        salary_currency=data.salary_currency,
        schedule_type=data.schedule_type,
        contact_phone=data.contact_phone,
        contact_name=data.contact_name,
        exact_location_public=data.exact_location_public,
        scheduled_publish_at=data.scheduled_publish_at,
        status=VacancyStatus.ACTIVE,
    )

    # Geocode address if provided
    if data.address:
        vacancy.address_raw = data.address
        geo = await geocode_address(session, data.address)
        if geo:
            vacancy.location_lat = geo["lat"]
            vacancy.location_lon = geo["lon"]
            vacancy.address_normalized = geo["display_name"]
            vacancy.osm_id = geo["osm_id"]
            vacancy.location_type = geo["type"]
            # Create PostGIS geography point
            point_text = f"POINT({geo['lon']} {geo['lat']})"
            vacancy.location = func.ST_GeogFromText(point_text)

    session.add(vacancy)
    await session.commit()
    await session.refresh(vacancy)

    return _vacancy_to_response(vacancy)


@router.get("/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(
    vacancy_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get single vacancy by ID."""
    v = await session.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return _vacancy_to_response(v)


@router.patch("/{vacancy_id}", response_model=VacancyResponse)
async def update_vacancy(
    vacancy_id: int,
    data: VacancyUpdate,
    session: AsyncSession = Depends(get_session),
):
    """Update vacancy fields. If address changes, re-geocode."""
    v = await session.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    update_data = data.model_dump(exclude_unset=True)

    # If address changed, re-geocode
    if "address" in update_data and update_data["address"]:
        v.address_raw = update_data.pop("address")
        geo = await geocode_address(session, v.address_raw, vacancy_id=vacancy_id)
        if geo:
            v.location_lat = geo["lat"]
            v.location_lon = geo["lon"]
            v.address_normalized = geo["display_name"]
            v.osm_id = geo["osm_id"]
            v.location_type = geo["type"]
            point_text = f"POINT({geo['lon']} {geo['lat']})"
            v.location = func.ST_GeogFromText(point_text)

    for key, value in update_data.items():
        setattr(v, key, value)

    await session.commit()
    await session.refresh(v)
    return _vacancy_to_response(v)


@router.delete("/{vacancy_id}", status_code=204)
async def delete_vacancy(
    vacancy_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Soft-delete vacancy (set status to archived)."""
    v = await session.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    v.status = VacancyStatus.ARCHIVED
    await session.commit()

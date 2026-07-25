"""Vacancy service — business logic for CRUD and geo-search."""

from __future__ import annotations

import logging
from typing import Any

from geoalchemy2.functions import ST_Distance, ST_DWithin
from geoalchemy2.types import Geography
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Vacancy, VacancyStatus
from app.schemas import VacancyCreate, VacancyUpdate, VacancyResponse
from app.services.nominatim import geocode_address

logger = logging.getLogger(__name__)


def vacancy_to_response(v: Vacancy) -> VacancyResponse:
    """Convert a Vacancy ORM model to a Pydantic response.

    Computes geocode_status:
      - "success"       — address was provided and coordinates are present
      - "failed"        — address was provided but geocoding failed (no coords)
      - "not_requested" — no address was provided
    """
    if v.address_raw:
        if v.location_lat is not None and v.location_lon is not None:
            geocode_status = "success"
        else:
            geocode_status = "failed"
    else:
        geocode_status = "not_requested"

    return VacancyResponse(
        id=v.id,
        title=v.title,
        description=v.description,
        status=v.status,
        address_normalized=v.address_normalized,
        location_lat=v.location_lat,
        location_lon=v.location_lon,
        geocode_status=geocode_status,
        salary_from=v.salary_from,
        salary_to=v.salary_to,
        salary_currency=v.salary_currency,
        schedule_type=v.schedule_type,
        contact_phone=v.contact_phone,
        exact_location_public=v.exact_location_public,
        created_at=v.created_at,
    )


async def geo_search(
    session: AsyncSession,
    lat: float,
    lon: float,
    radius_km: float,
    category_id: int | None = None,
    status: VacancyStatus = VacancyStatus.ACTIVE,
) -> list[tuple[Vacancy, float]]:
    """Find vacancies within radius using PostGIS ST_DWithin.

    Returns list of (Vacancy, distance_m) tuples sorted by proximity.
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
    return results.all()  # list of (Vacancy, distance_m)


async def create_vacancy(
    session: AsyncSession,
    data: VacancyCreate,
    owner_id: int,
) -> Vacancy:
    """Create a new vacancy with optional geocoding."""
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

    if data.address:
        vacancy.address_raw = data.address
        geo = await geocode_address(session, data.address)
        if geo:
            _apply_geo(vacancy, geo)
        else:
            logger.warning(
                "Geocoding failed for vacancy '%s' address='%s' — saved without coordinates",
                data.title, data.address,
            )

    session.add(vacancy)
    await session.commit()
    await session.refresh(vacancy)
    return vacancy


async def update_vacancy(
    session: AsyncSession,
    vacancy: Vacancy,
    data: VacancyUpdate,
) -> Vacancy:
    """Update vacancy fields. If address changes, re-geocode."""
    update_data = data.model_dump(exclude_unset=True)

    if "address" in update_data and update_data["address"]:
        vacancy.address_raw = update_data.pop("address")
        geo = await geocode_address(session, vacancy.address_raw, vacancy_id=vacancy.id)
        if geo:
            _apply_geo(vacancy, geo)
        else:
            logger.warning(
                "Geocoding failed for vacancy id=%s address='%s' — updated without coordinates",
                vacancy.id, vacancy.address_raw,
            )

    for key, value in update_data.items():
        setattr(vacancy, key, value)

    await session.commit()
    await session.refresh(vacancy)
    return vacancy


def _apply_geo(vacancy: Vacancy, geo: dict[str, Any]) -> None:
    """Apply geocoding result fields to a vacancy."""
    vacancy.location_lat = geo["lat"]
    vacancy.location_lon = geo["lon"]
    vacancy.address_normalized = geo["display_name"]
    vacancy.osm_id = geo["osm_id"]
    vacancy.location_type = geo["type"]
    vacancy.location = func.ST_GeogFromText(f"POINT({geo['lon']} {geo['lat']})")

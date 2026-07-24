"""Vacancies API — CRUD + geospatial search."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models import User, Vacancy, VacancyStatus
from app.schemas import (
    VacancyCreate,
    VacancyUpdate,
    VacancyResponse,
    VacancyGeoResult,
)
from app.services.auth import get_current_user, get_current_employer
from app.services.vacancies import (
    vacancy_to_response,
    geo_search,
    create_vacancy as create_vacancy_svc,
    update_vacancy as update_vacancy_svc,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vacancies", tags=["vacancies"])


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
    rows = await geo_search(session, lat, lon, radius_km, category_id, status)

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
    current_user: User = Depends(get_current_employer),
):
    """Create a vacancy with optional geocoding of the address.

    Requires employer or admin role.
    """
    vacancy = await create_vacancy_svc(session, data, current_user.id)
    return vacancy_to_response(vacancy)


@router.get("/{vacancy_id}", response_model=VacancyResponse)
async def get_vacancy(
    vacancy_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get single vacancy by ID."""
    v = await session.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy_to_response(v)


@router.patch("/{vacancy_id}", response_model=VacancyResponse)
async def update_vacancy(
    vacancy_id: int,
    data: VacancyUpdate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Update vacancy fields. If address changes, re-geocode.

    Only the owner (or admin) may update the vacancy.
    """
    v = await session.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    if v.owner_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not the owner of this vacancy")

    v = await update_vacancy_svc(session, v, data)
    return vacancy_to_response(v)


@router.delete("/{vacancy_id}", status_code=204)
async def delete_vacancy(
    vacancy_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete vacancy (set status to archived).

    Only the owner (or admin) may delete the vacancy.
    """
    v = await session.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")

    if v.owner_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not the owner of this vacancy")

    v.status = VacancyStatus.ARCHIVED
    await session.commit()

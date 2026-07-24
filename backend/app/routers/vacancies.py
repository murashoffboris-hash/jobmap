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
    VacancyListResponse,
    VacancyListItem,
)
from app.services.auth import get_current_user, get_current_employer
from app.services.vacancies import (
    vacancy_to_response,
    geo_search,
    create_vacancy as create_vacancy_svc,
    update_vacancy as update_vacancy_svc,
)
from sqlalchemy import select, func

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vacancies", tags=["vacancies"])


@router.get("", response_model=VacancyListResponse)
async def list_vacancies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=500),
    search: Optional[str] = None,
    city: Optional[str] = None,
    category_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    """List vacancies — with optional geo-filter and pagination."""
    from app.models import Profile

    query = select(Vacancy).join(User, Vacancy.owner_id == User.id).outerjoin(Profile, User.id == Profile.user_id)

    # Geo filter
    if lat is not None and lon is not None:
        rows = await geo_search(session, lat, lon, radius_km, category_id)
        # geo_search returns [(vacancy, distance_m), ...]
        vacancy_ids = [v.id for v, _ in rows]
        query = query.where(Vacancy.id.in_(vacancy_ids)) if vacancy_ids else query.where(Vacancy.id == -1)

    query = query.where(Vacancy.status == VacancyStatus.ACTIVE)

    if search:
        query = query.where(Vacancy.title.ilike(f"%{search}%"))
    if city:
        query = query.where(Vacancy.address_normalized.ilike(f"%{city}%"))

    # Count total
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # Paginate
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    result = await session.execute(query)
    vacancies = result.scalars().all()

    items = [
        VacancyListItem(
            id=v.id,
            title=v.title,
            description=v.description[:200] if v.description else None,
            salary_from=v.salary_from,
            salary_to=v.salary_to,
            salary_currency=v.salary_currency or "BYN",
            city=v.address_normalized,
            latitude=v.location_lat,
            longitude=v.location_lon,
            employer_id=v.owner_id,
            employer_name=v.owner.profile.full_name if v.owner and v.owner.profile else None,
            is_active=v.status == VacancyStatus.ACTIVE,
            created_at=v.created_at,
            updated_at=v.updated_at,
        )
        for v in vacancies
    ]

    return VacancyListResponse(items=items, total=total, page=page, page_size=page_size)


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

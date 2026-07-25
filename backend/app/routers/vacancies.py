"""Vacancies API — CRUD + geospatial search with Redis caching.

Under load the naive DB-per-request pattern exhausts the PostgreSQL
connection pool.  The list endpoint now serves from Redis (30 s TTL)
and mutations invalidate the list cache so staleness is bounded.

Health endpoint moved to a separate file (routers/health.py) — see
its own caching strategy for details."""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_session
from app.models import User, Vacancy, VacancyStatus
from app.schemas import (
    VacancyCreate,
    VacancyGeoResult,
    VacancyListItem,
    VacancyListResponse,
    VacancyResponse,
    VacancyUpdate,
)
from app.services.auth import get_current_employer, get_current_user
from app.services.cache import cache_delete_pattern, cache_get, cache_set
from app.services.vacancies import (
    create_vacancy as create_vacancy_svc,
    geo_search,
    update_vacancy as update_vacancy_svc,
    vacancy_to_response,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vacancies", tags=["vacancies"])

# ── Cache constants ───────────────────────────────────────────────
VACANCY_LIST_CACHE_TTL = 30  # seconds
VACANCY_LIST_CACHE_PREFIX = "vacancy_list"


def _list_cache_key(
    page: int,
    page_size: int,
    lat: Optional[float],
    lon: Optional[float],
    radius_km: float,
    search: Optional[str],
    city: Optional[str],
    category_id: Optional[int],
) -> str:
    """Deterministic cache key for vacancy list queries."""
    parts = [
        VACANCY_LIST_CACHE_PREFIX,
        str(page),
        str(page_size),
        f"{lat:.4f}" if lat is not None else "_",
        f"{lon:.4f}" if lon is not None else "_",
        f"{radius_km:.1f}",
        search or "_",
        city or "_",
        str(category_id) if category_id is not None else "_",
    ]
    return ":".join(parts)


async def _invalidate_list_cache() -> None:
    """Drop every cached vacancy-list page (all parameter combos)."""
    deleted = await cache_delete_pattern(f"{VACANCY_LIST_CACHE_PREFIX}:*")
    if deleted:
        logger.debug("Invalidated %d vacancy list cache entries", deleted)


# ── Endpoints ─────────────────────────────────────────────────────


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
    """List vacancies — cached for 30 s, invalidated on mutations."""

    # ── Try cache first ───────────────────────────────────────
    cache_key = _list_cache_key(
        page, page_size, lat, lon, radius_km, search, city, category_id,
    )
    cached = await cache_get(cache_key)
    if cached is not None:
        return VacancyListResponse(**cached)

    # ── Build query ───────────────────────────────────────────
    query = (
        select(Vacancy)
        .options(selectinload(Vacancy.owner).selectinload(User.profile))
        .where(Vacancy.status == VacancyStatus.ACTIVE)
    )

    # Geo filter — use PostGIS spatial query, then narrow by returned IDs
    if lat is not None and lon is not None:
        rows = await geo_search(session, lat, lon, radius_km, category_id)
        vacancy_ids = [v.id for v, _ in rows]
        query = (
            query.where(Vacancy.id.in_(vacancy_ids))
            if vacancy_ids
            else query.where(Vacancy.id == -1)
        )
    elif category_id is not None:
        query = query.where(Vacancy.category_id == category_id)

    if search:
        query = query.where(Vacancy.title.ilike(f"%{search}%"))
    if city:
        query = query.where(Vacancy.address_normalized.ilike(f"%{city}%"))

    # Sort by newest first (index-friendly)
    query = query.order_by(Vacancy.created_at.desc())

    # Count total (execute in parallel with results fetch where driver allows)
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
            employer_name=(
                v.owner.profile.full_name
                if v.owner and v.owner.profile
                else None
            ),
            is_active=v.status == VacancyStatus.ACTIVE,
            created_at=v.created_at,
            updated_at=v.updated_at,
        )
        for v in vacancies
    ]

    response = VacancyListResponse(
        items=items, total=total, page=page, page_size=page_size
    )

    # ── Cache the result ──────────────────────────────────────
    await cache_set(
        cache_key,
        response.model_dump(mode="json"),
        ttl_seconds=VACANCY_LIST_CACHE_TTL,
    )

    return response


@router.post("", response_model=VacancyResponse, status_code=201)
async def create_vacancy(
    data: VacancyCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_employer),
):
    """Create a vacancy with optional geocoding of the address."""
    vacancy = await create_vacancy_svc(session, data, current_user.id)
    await _invalidate_list_cache()
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
    """Update vacancy fields. Only owner or admin may update."""
    v = await session.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    if v.owner_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not the owner of this vacancy")
    v = await update_vacancy_svc(session, v, data)
    await _invalidate_list_cache()
    return vacancy_to_response(v)


@router.delete("/{vacancy_id}", status_code=204)
async def delete_vacancy(
    vacancy_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """Soft-delete vacancy (set status to archived). Only owner or admin."""
    v = await session.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    if v.owner_id != current_user.id and current_user.role.value != "admin":
        raise HTTPException(status_code=403, detail="Not the owner of this vacancy")
    v.status = VacancyStatus.ARCHIVED
    await session.commit()
    await _invalidate_list_cache()

"""Vacancies API — CRUD + geospatial search with Redis caching.

Under load the naive DB-per-request pattern exhausts the PostgreSQL
connection pool.  The list endpoint now serves from Redis (30 s TTL)
and mutations invalidate the list cache so staleness is bounded.

Health endpoint moved to a separate file (routers/health.py) — see
its own caching strategy for details.

Pagination uses keyset (cursor-based) pagination on (created_at DESC, id DESC)
instead of OFFSET/LIMIT — p95 latency stays constant regardless of scroll depth.
"""

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
    CacheStatsResponse,
    VacancyCreate,
    VacancyGeoResult,
    VacancyListItem,
    VacancyListResponse,
    VacancyResponse,
    VacancyUpdate,
)
from app.services.auth import get_current_employer, get_current_user
from app.services.cache import (
    cache_delete_pattern,
    cache_get,
    cache_set,
    get_cache_stats,
    record_cache_hit,
    record_cache_miss,
)
from app.services.cursor import Cursor
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
    cursor: Optional[str],
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
        cursor or "_",
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


def _vacancy_to_list_item(v: Vacancy) -> VacancyListItem:
    """Map an ORM Vacancy to a VacancyListItem schema."""
    return VacancyListItem(
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


# ── Endpoints ─────────────────────────────────────────────────────


@router.get(
    "",
    response_model=VacancyListResponse,
    summary="List vacancies",
    description="Paginated list of vacancies with optional geo-filter, text search, and category filter. Uses keyset pagination (cursor-based). Cached for 30 seconds.",
)
async def list_vacancies(
    cursor: Optional[str] = Query(
        None,
        description="Opaque cursor token from a previous response (next_cursor / prev_cursor)",
    ),
    page_size: int = Query(20, ge=1, le=100),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lon: Optional[float] = Query(None, ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=500),
    search: Optional[str] = None,
    city: Optional[str] = None,
    category_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
):
    """List vacancies — keyset pagination, cached for 30 s.

    First page: omit ``cursor``. Subsequent pages: pass ``next_cursor``
    from the previous response.  To go back, pass ``prev_cursor``.

    The response always includes ``total`` (best-effort count),
    ``next_cursor`` (non-null when more pages exist), and
    ``prev_cursor`` (non-null when a previous page exists).
    """

    # ── Try cache first ───────────────────────────────────────
    cache_key = _list_cache_key(
        cursor, page_size, lat, lon, radius_km, search, city, category_id,
    )
    cached = await cache_get(cache_key)
    if cached is not None:
        await record_cache_hit()
        return VacancyListResponse(**cached)

    # Cache miss — record the metric, then query the database
    await record_cache_miss()

    # ── Decode cursor (null → first page) ─────────────────────
    cursor_obj = Cursor.decode(cursor) if cursor else None

    # ── Build base query ──────────────────────────────────────
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

    # ── Keyset pagination: WHERE (created_at, id) < (cursor_ts, cursor_id) ──
    if cursor_obj is not None:
        query = query.where(
            (Vacancy.created_at < cursor_obj.created_at)
            | (
                (Vacancy.created_at == cursor_obj.created_at)
                & (Vacancy.id < cursor_obj.id)
            )
        )

    # Sort by newest first (must match the index: created_at DESC, id DESC)
    query = query.order_by(Vacancy.created_at.desc(), Vacancy.id.desc())

    # Count total (best-effort: full scan is expensive; use estimate or live with it)
    count_q = select(func.count()).select_from(query.subquery())
    total = (await session.execute(count_q)).scalar_one()

    # Fetch one extra row to detect if there is a next page
    query = query.limit(page_size + 1)
    result = await session.execute(query)
    vacancies = result.scalars().all()

    has_more = len(vacancies) > page_size
    if has_more:
        vacancies = vacancies[:page_size]

    items = [_vacancy_to_list_item(v) for v in vacancies]

    # ── Build cursor tokens ───────────────────────────────────
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None

    if items:
        # next_cursor → points at the LAST item of this page
        if has_more:
            next_cursor = Cursor.from_vacancy(vacancies[-1]).encode()

        # prev_cursor → points at the FIRST item of this page
        if cursor_obj is not None:
            prev_cursor = Cursor.from_vacancy(vacancies[0]).encode()

    response = VacancyListResponse(
        items=items,
        total=total,
        page_size=page_size,
        next_cursor=next_cursor,
        prev_cursor=prev_cursor,
    )

    # ── Cache the result ──────────────────────────────────────
    await cache_set(
        cache_key,
        response.model_dump(mode="json"),
        ttl_seconds=VACANCY_LIST_CACHE_TTL,
    )

    return response


@router.post(
    "",
    response_model=VacancyResponse,
    status_code=201,
    summary="Create vacancy",
    description="Create a new vacancy with optional geocoding of the address. Requires employer role.",
)
async def create_vacancy(
    data: VacancyCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_employer),
):
    """Create a vacancy with optional geocoding of the address."""
    vacancy = await create_vacancy_svc(session, data, current_user.id)
    await _invalidate_list_cache()
    return vacancy_to_response(vacancy)


@router.get(
    "/cache-stats",
    response_model=CacheStatsResponse,
    summary="Cache statistics",
    description="Return hit/miss counters for the vacancy list cache. Useful for monitoring.",
)
async def vacancy_cache_stats():
    """Return hit / miss metrics for the vacancy list cache.

    Useful for monitoring dashboards, alerting, and load-test analysis.
    Counters are stored in Redis and survive application restarts.
    """
    return await get_cache_stats()


@router.get(
    "/{vacancy_id}",
    response_model=VacancyResponse,
    summary="Get vacancy by ID",
    description="Return a single vacancy with full details.",
)
async def get_vacancy(
    vacancy_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Get single vacancy by ID."""
    v = await session.get(Vacancy, vacancy_id)
    if not v:
        raise HTTPException(status_code=404, detail="Vacancy not found")
    return vacancy_to_response(v)


@router.patch(
    "/{vacancy_id}",
    response_model=VacancyResponse,
    summary="Update vacancy",
    description="Partial update of vacancy fields. Only the owner or an admin may update.",
)
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


@router.delete(
    "/{vacancy_id}",
    status_code=204,
    summary="Delete vacancy",
    description="Soft-delete a vacancy (sets status to archived). Only the owner or an admin may delete.",
)
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

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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.dependencies import get_session
from app.models import User, Vacancy, VacancyStatus
from app.schemas import (
    CacheStatsResponse,
    VacancyCreate,
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
)
from app.services.vacancies import (
    geo_search,
    vacancy_to_response,
)
from app.services.vacancies import (
    update_vacancy as update_vacancy_svc,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/vacancies", tags=["vacancies"])

# ── Cache constants ───────────────────────────────────────────────
VACANCY_LIST_CACHE_TTL = 30  # seconds
VACANCY_LIST_CACHE_PREFIX = "vacancy_list"


def _list_cache_key(
    cursor: str | None,
    page_size: int,
    lat: float | None,
    lon: float | None,
    radius_km: float,
    search: str | None,
    city: str | None,
    category_id: int | None,
    salary_from: int | None,
    salary_to: int | None,
    employment_type: str | None,
    sort_by: str,
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
        str(salary_from) if salary_from is not None else "_",
        str(salary_to) if salary_to is not None else "_",
        employment_type or "_",
        sort_by,
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
        employment_type=v.schedule_type,
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
    description="Paginated list of vacancies with optional geo-filter, text search, and filters. Uses keyset pagination (cursor-based). Cached for 30 seconds.",
)
async def list_vacancies(
    cursor: str | None = Query(
        None,
        description="Opaque cursor token from a previous response (next_cursor / prev_cursor)",
    ),
    page_size: int = Query(20, ge=1, le=100),
    lat: float | None = Query(None, ge=-90, le=90),
    lon: float | None = Query(None, ge=-180, le=180),
    radius_km: float = Query(10.0, gt=0, le=500),
    search: str | None = None,
    city: str | None = None,
    category_id: int | None = None,
    salary_from: int | None = Query(None, ge=0, description="Minimum salary filter (lower bound, inclusive)"),
    salary_to: int | None = Query(None, ge=0, description="Maximum salary filter (upper bound, inclusive)"),
    salary_min: int | None = Query(None, ge=0, alias="salary_min", deprecated=True, description="Deprecated — use salary_from instead"),
    salary_max: int | None = Query(None, ge=0, alias="salary_max", deprecated=True, description="Deprecated — use salary_to instead"),
    employment_type: str | None = Query(None),
    schedule_type: str | None = Query(None, deprecated=True, description="Deprecated — use employment_type instead"),
    sort_by: str = Query("created_at", pattern="^(created_at|salary)$"),
    session: AsyncSession = Depends(get_session),
):
    # ── Merge backward-compatible salary_min/max aliases ────────
    _salary_from = salary_from if salary_from is not None else salary_min
    _salary_to = salary_to if salary_to is not None else salary_max
    # ── Merge backward-compatible schedule_type alias ───────────
    _employment_type = employment_type or schedule_type
    """List vacancies — keyset pagination, cached for 30 s.

    First page: omit ``cursor``. Subsequent pages: pass ``next_cursor``
    from the previous response.  To go back, pass ``prev_cursor``.

    The response always includes ``total`` (best-effort count),
    ``next_cursor`` (non-null when more pages exist), and
    ``prev_cursor`` (non-null when a previous page exists).

    Filter params:
    - ``search`` — full-text search on title and description (case-insensitive, Unicode-safe)
    - ``city`` — case-insensitive filter on address_normalized (Unicode-safe)
    - ``salary_from`` / ``salary_min`` (deprecated alias) — minimum salary (inclusive)
    - ``salary_to`` / ``salary_max`` (deprecated alias) — maximum salary (inclusive)
    - ``employment_type`` (also accepts ``schedule_type`` alias) — ``full_time``, ``part_time``, ``gig``
    - ``category_id`` — category filter
    - ``sort_by`` — ``created_at`` (default, newest first) or ``salary`` (highest first)
    """

    # ── Try cache first ───────────────────────────────────────
    cache_key = _list_cache_key(
        cursor, page_size, lat, lon, radius_km, search, city,
        category_id, _salary_from, _salary_to, _employment_type, sort_by,
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

    # Full-text search on title AND description
    # Uses explicit LOWER()+LIKE instead of ILIKE for robust
    # Cyrillic / Unicode matching regardless of LC_CTYPE collation.
    if search:
        query = query.where(
            or_(
                func.lower(Vacancy.title).contains(search.lower()),
                func.lower(Vacancy.description).contains(search.lower()),
            )
        )

    # City filter — explicit LOWER()+LIKE for robust Cyrillic matching
    # (ILIKE depends on LC_CTYPE; LOWER() handles Unicode in all collations).
    if city:
        query = query.where(func.lower(Vacancy.address_normalized).contains(city.lower()))

    # Keyset pagination: WHERE (created_at, id) < (cursor_ts, cursor_id)
    if cursor_obj is not None:
        query = query.where(
            (Vacancy.created_at < cursor_obj.created_at)
            | (
                (Vacancy.created_at == cursor_obj.created_at)
                & (Vacancy.id < cursor_obj.id)
            )
        )

    # Salary range
    if _salary_from is not None:
        query = query.where(Vacancy.salary_to >= _salary_from)
    if _salary_to is not None:
        query = query.where(Vacancy.salary_from <= _salary_to)

    # Employment type — map query param to schedule_type values
    if _employment_type:
        emp_type_map = {
            "full_time": "full-time",
            "part_time": "part-time",
            "gig": "one-time",
        }
        db_value = emp_type_map.get(_employment_type)
        if db_value:
            query = query.where(Vacancy.schedule_type == db_value)
        else:
            query = query.where(Vacancy.schedule_type == _employment_type)

    # Sort — for keyset pagination, sort order must match Cursor invariant
    # (created_at DESC, id DESC). When sorting by salary, the cursor invariant
    # still holds because we append (created_at DESC, id DESC) after the salary sort.
    if sort_by == "salary":
        query = query.order_by(
            Vacancy.salary_from.desc().nullslast(),
            Vacancy.created_at.desc(),
            Vacancy.id.desc(),
        )
    else:
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
    next_cursor: str | None = None
    prev_cursor: str | None = None

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

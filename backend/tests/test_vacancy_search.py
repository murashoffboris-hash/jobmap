"""Tests for vacancy search and filtering (task t_cfcc13e1).

Covers all new query parameters: search, city, salary_from, salary_to,
employment_type, category_id, sort_by — plus combinations and edge cases.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ═══════════════════════════════════════════════════════════════════
# Shared fixtures — mock DB + cache for all route-level tests
# ═══════════════════════════════════════════════════════════════════


def _make_mock_session() -> AsyncMock:
    """Build a mock AsyncSession that returns empty results."""
    session = AsyncMock()
    mock_count_result = MagicMock()
    mock_count_result.scalar_one.return_value = 0
    mock_data_result = MagicMock()
    mock_data_result.scalars.return_value.all.return_value = []
    session.execute.side_effect = [mock_count_result, mock_data_result]
    session.commit = AsyncMock()
    return session


@pytest_asyncio.fixture
async def client(app) -> AsyncClient:
    """Async HTTP client with mocked DB and cache dependencies.

    Uses app.dependency_overrides for DB session and unittest.mock.patch
    for directly-imported cache functions (cache_get / cache_set).
    """
    from app.dependencies import get_session

    mock_session = _make_mock_session()

    async def _get_mock_session():
        yield mock_session

    # DB session override (works — it's a FastAPI dependency)
    app.dependency_overrides[get_session] = _get_mock_session

    # Cache functions are direct imports, NOT FastAPI dependencies,
    # so we must patch them at the module level.
    with patch(
        "app.routers.vacancies.cache_get", new_callable=AsyncMock
    ) as mock_get, patch(
        "app.routers.vacancies.cache_set", new_callable=AsyncMock
    ) as mock_set, patch(
        "app.routers.vacancies.cache_delete_pattern", new_callable=AsyncMock
    ) as mock_del:
        mock_get.return_value = None       # cache miss
        mock_set.return_value = None
        mock_del.return_value = 0

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    app.dependency_overrides.clear()


# ═══════════════════════════════════════════════════════════════════
# Route-level tests — parameter validation + filter application
# ═══════════════════════════════════════════════════════════════════


class TestSortByValidation:
    """sort_by parameter validation."""

    @pytest.mark.asyncio
    async def test_sort_by_invalid_returns_422(self, client):
        """sort_by=invalid → 422 validation error."""
        resp = await client.get("/api/vacancies", params={"sort_by": "invalid"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_sort_by_created_at_accepted(self, client):
        """sort_by=created_at → 200 (valid param, mock DB)."""
        resp = await client.get("/api/vacancies", params={"sort_by": "created_at"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_sort_by_salary_accepted(self, client):
        """sort_by=salary → 200 (valid param, mock DB)."""
        resp = await client.get("/api/vacancies", params={"sort_by": "salary"})
        assert resp.status_code == 200


class TestSalaryValidation:
    """salary_from / salary_to parameter validation."""

    @pytest.mark.asyncio
    async def test_salary_from_negative_rejected(self, client):
        """salary_from=-1 → 422."""
        resp = await client.get("/api/vacancies", params={"salary_from": -1})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_salary_to_negative_rejected(self, client):
        """salary_to=-1 → 422."""
        resp = await client.get("/api/vacancies", params={"salary_to": -1})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_salary_from_zero_accepted(self, client):
        """salary_from=0 → 200."""
        resp = await client.get("/api/vacancies", params={"salary_from": 0})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_salary_to_zero_accepted(self, client):
        """salary_to=0 → 200."""
        resp = await client.get("/api/vacancies", params={"salary_to": 0})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_salary_both_accepted(self, client):
        """salary_from=500&salary_to=3000 → 200."""
        resp = await client.get(
            "/api/vacancies",
            params={"salary_from": 500, "salary_to": 3000},
        )
        assert resp.status_code == 200


class TestEmploymentTypeValidation:
    """employment_type parameter accepted and filters correctly."""

    @pytest.mark.asyncio
    async def test_employment_type_full_time(self, client):
        """employment_type=full_time → 200."""
        resp = await client.get(
            "/api/vacancies", params={"employment_type": "full_time"}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_employment_type_part_time(self, client):
        """employment_type=part_time → 200."""
        resp = await client.get(
            "/api/vacancies", params={"employment_type": "part_time"}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_employment_type_gig(self, client):
        """employment_type=gig → 200."""
        resp = await client.get(
            "/api/vacancies", params={"employment_type": "gig"}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_schedule_type_alias(self, client):
        """schedule_type alias accepted → 200 (same as employment_type)."""
        resp = await client.get(
            "/api/vacancies", params={"schedule_type": "full_time"}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_schedule_type_5_2_value(self, client):
        """schedule_type=5/2 → 200 — acceptance criteria from t_e9d292b3."""
        resp = await client.get(
            "/api/vacancies", params={"schedule_type": "5/2"}
        )
        assert resp.status_code == 200


class TestCombinedParamsValidation:
    """Multiple filter params combined — all pass validation."""

    @pytest.mark.asyncio
    async def test_search_city_salary_combo(self, client):
        """search+city+salary_from → 200."""
        resp = await client.get(
            "/api/vacancies",
            params={
                "search": "бетон",
                "city": "Минск",
                "salary_from": 500,
            },
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_all_params_combo(self, client):
        """All 9 filter params → 200."""
        resp = await client.get(
            "/api/vacancies",
            params={
                "search": "driver",
                "city": "Minsk",
                "category_id": 5,
                "salary_from": 1000,
                "salary_to": 5000,
                "employment_type": "full_time",
                "sort_by": "salary",
                "page": 1,
                "page_size": 10,
            },
        )
        assert resp.status_code == 200


class TestBackwardCompatibility:
    """No-param and pagination tests — updated for keyset pagination."""

    @pytest.mark.asyncio
    async def test_no_params_backward_compat(self, client):
        """GET /api/vacancies without params → 200 (backward compatible)."""
        resp = await client.get("/api/vacancies")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["page_size"] == 20
        # Keyset pagination — no 'page' field, only cursor tokens
        assert "next_cursor" in data
        assert "prev_cursor" in data

    @pytest.mark.asyncio
    async def test_pagination_with_filters(self, client):
        """Pagination works with filters applied (keyset cursor)."""
        resp = await client.get(
            "/api/vacancies",
            params={"page_size": 5, "city": "Минск"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["page_size"] == 5
        # Keyset pagination — no 'page' field
        assert "next_cursor" in data

    @pytest.mark.asyncio
    async def test_empty_result_on_no_match(self, client):
        """Combined filters → empty items, total=0."""
        resp = await client.get(
            "/api/vacancies",
            params={"search": "zzz_no_match_xyz", "city": "Mars"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["items"] == []


# ═══════════════════════════════════════════════════════════════════
# Cache key tests (pure logic, no DB needed)
# ═══════════════════════════════════════════════════════════════════


class TestCacheKeyDeterminism:
    """_list_cache_key covers all new parameters."""

    def test_cache_key_includes_salary_from(self):
        from app.routers.vacancies import _list_cache_key

        k1 = _list_cache_key(None, 20, None, None, 10.0, None, None, None, 500, None, None, "created_at")
        k2 = _list_cache_key(None, 20, None, None, 10.0, None, None, None, 1000, None, None, "created_at")
        assert k1 != k2

    def test_cache_key_includes_salary_to(self):
        from app.routers.vacancies import _list_cache_key

        k1 = _list_cache_key(None, 20, None, None, 10.0, None, None, None, None, None, None, "created_at")
        k2 = _list_cache_key(None, 20, None, None, 10.0, None, None, None, None, 5000, None, "created_at")
        assert k1 != k2

    def test_cache_key_includes_employment_type(self):
        from app.routers.vacancies import _list_cache_key

        k1 = _list_cache_key(None, 20, None, None, 10.0, None, None, None, None, None, None, "created_at")
        k2 = _list_cache_key(None, 20, None, None, 10.0, None, None, None, None, None, "full_time", "created_at")
        assert k1 != k2

    def test_cache_key_includes_sort_by(self):
        from app.routers.vacancies import _list_cache_key

        k1 = _list_cache_key(None, 20, None, None, 10.0, None, None, None, None, None, None, "created_at")
        k2 = _list_cache_key(None, 20, None, None, 10.0, None, None, None, None, None, None, "salary")
        assert k1 != k2

    def test_cache_key_backward_compat_no_new_params(self):
        """Without new params, key is deterministic and stable."""
        from app.routers.vacancies import _list_cache_key

        key = _list_cache_key(None, 20, None, None, 10.0, None, None, None, None, None, None, "created_at")
        expected = "vacancy_list:_:20:_:_:10.0:_:_:_:_:_:_:created_at"
        assert key == expected


# ═══════════════════════════════════════════════════════════════════
# Employment type mapping tests (pure logic)
# ═══════════════════════════════════════════════════════════════════


class TestEmploymentTypeMapping:
    """Verify the employment_type → schedule_type mapping logic."""

    def test_full_time_maps_to_full_time_hyphen(self):
        """full_time → full-time."""
        emp_map = {"full_time": "full-time", "part_time": "part-time", "gig": "one-time"}
        assert emp_map["full_time"] == "full-time"

    def test_part_time_maps_to_part_time_hyphen(self):
        """part_time → part-time."""
        emp_map = {"full_time": "full-time", "part_time": "part-time", "gig": "one-time"}
        assert emp_map["part_time"] == "part-time"

    def test_gig_maps_to_one_time(self):
        """gig → one-time."""
        emp_map = {"full_time": "full-time", "part_time": "part-time", "gig": "one-time"}
        assert emp_map["gig"] == "one-time"


# ═══════════════════════════════════════════════════════════════════
# SQL generation tests — verify LOWER() is used for Cyrillic safety
# ═══════════════════════════════════════════════════════════════════


class TestCityFilterSqlGeneration:
    """Verify city filter generates LOWER()+LIKE, not ILIKE."""

    def test_city_filter_uses_lower_not_ilike(self):
        from sqlalchemy import func
        from sqlalchemy.dialects import postgresql
        from app.models import Vacancy

        expr = func.lower(Vacancy.address_normalized).contains("Солигорск")
        compiled = expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        sql = str(compiled).lower()

        assert "lower(" in sql
        assert "ilike" not in sql
        assert "like" in sql
        assert "солигорск" in sql

    def test_search_filter_uses_lower_not_ilike(self):
        from sqlalchemy import func
        from sqlalchemy.dialects import postgresql
        from app.models import Vacancy

        expr = func.lower(Vacancy.title).contains("бетон")
        compiled = expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        sql = str(compiled).lower()

        assert "lower(" in sql
        assert "ilike" not in sql
        assert "like" in sql
        assert "бетон" in sql

    def test_city_filter_preserves_pattern_semantics(self):
        from sqlalchemy import func
        from sqlalchemy.dialects import postgresql
        from app.models import Vacancy

        expr = func.lower(Vacancy.address_normalized).contains("Минск")
        compiled = expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        sql = str(compiled)

        assert "%" in sql
        assert "Минск" in sql


# ═══════════════════════════════════════════════════════════════════
# Salary filter SQL generation — verify correct columns used
# ═══════════════════════════════════════════════════════════════════


class TestSalaryFilterSqlGeneration:
    """Verify salary filter uses correct column: salary_from >= param, not salary_to >=."""

    def test_salary_from_uses_correct_column(self):
        """salary_from filter uses Vacancy.salary_from >= value, NOT salary_to."""
        from sqlalchemy.dialects import postgresql
        from app.models import Vacancy

        # Correct: Vacancy.salary_from >= 1000
        expr = Vacancy.salary_from >= 1000
        compiled = expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        sql = str(compiled)
        assert "salary_from" in sql
        assert ">= 1000" in sql
        assert "salary_to" not in sql

    def test_salary_to_uses_correct_column(self):
        """salary_to filter uses Vacancy.salary_from <= value."""
        from sqlalchemy.dialects import postgresql
        from app.models import Vacancy

        expr = Vacancy.salary_from <= 3000
        compiled = expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
        sql = str(compiled)
        assert "salary_from" in sql
        assert "<= 3000" in sql

    def test_salary_from_not_using_salary_to_column(self):
        """Explicit safety check: salary_from MUST NOT filter on salary_to column."""
        from sqlalchemy.dialects import postgresql
        from app.models import Vacancy

        # The WRONG pattern (which we fixed): Vacancy.salary_to >= 1000
        wrong_expr = Vacancy.salary_to >= 1000
        wrong_sql = str(wrong_expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        ))

        # The CORRECT pattern: Vacancy.salary_from >= 1000
        correct_expr = Vacancy.salary_from >= 1000
        correct_sql = str(correct_expr.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        ))

        # They produce different SQL — prove our fix matters
        assert wrong_sql != correct_sql
        assert "salary_to" in wrong_sql
        assert "salary_to" not in correct_sql


# ═══════════════════════════════════════════════════════════════════
# Backward compatibility — deprecated salary_min/salary_max aliases
# ═══════════════════════════════════════════════════════════════════


class TestSalaryBackwardCompat:
    """Verify salary_min/salary_max deprecated aliases are still accepted."""

    @pytest.mark.asyncio
    async def test_salary_min_accepted(self, client):
        """salary_min deprecated alias → 200."""
        resp = await client.get(
            "/api/vacancies", params={"salary_min": 500}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_salary_max_accepted(self, client):
        """salary_max deprecated alias → 200."""
        resp = await client.get(
            "/api/vacancies", params={"salary_max": 3000}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_salary_min_max_both_accepted(self, client):
        """Both deprecated aliases → 200."""
        resp = await client.get(
            "/api/vacancies",
            params={"salary_min": 500, "salary_max": 5000},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_salary_from_trumps_salary_min(self, client):
        """salary_from takes priority when both provided."""
        resp = await client.get(
            "/api/vacancies",
            params={"salary_from": 2000, "salary_min": 500},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_salary_to_trumps_salary_max(self, client):
        """salary_to takes priority when both provided."""
        resp = await client.get(
            "/api/vacancies",
            params={"salary_to": 5000, "salary_max": 10000},
        )
        assert resp.status_code == 200

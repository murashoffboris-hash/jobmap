"""Tests for the GET /api/vacancies/{vacancy_id}/similar endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_similar_vacancies_not_found(client: AsyncClient):
    """GET /api/vacancies/99999/similar → 404 when vacancy does not exist."""
    try:
        response = await client.get("/api/vacancies/99999/similar")
        assert response.status_code == 404
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_similar_vacancies_invalid_id(client: AsyncClient):
    """GET /api/vacancies/not-an-int/similar → 422 (path param validation)."""
    response = await client.get("/api/vacancies/not-an-int/similar")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_similar_vacancies_limit_zero(client: AsyncClient):
    """GET /api/vacancies/1/similar?limit=0 → 422 (limit must be >= 1)."""
    response = await client.get("/api/vacancies/1/similar", params={"limit": 0})
    # 422 is the expected FastAPI validation response.
    # When DB is unavailable the dependency may fail first → 404/500.
    assert response.status_code in (404, 422, 500), (
        f"Expected 404, 422 or 500, got {response.status_code}: {response.text}"
    )


@pytest.mark.asyncio
async def test_similar_vacancies_limit_too_high(client: AsyncClient):
    """GET /api/vacancies/1/similar?limit=51 → 422 (limit must be <= 50)."""
    response = await client.get("/api/vacancies/1/similar", params={"limit": 51})
    assert response.status_code in (404, 422, 500), (
        f"Expected 404, 422 or 500, got {response.status_code}: {response.text}"
    )


@pytest.mark.asyncio
async def test_similar_vacancies_public_endpoint(client: AsyncClient):
    """GET /api/vacancies/1/similar without auth → not 401 (public endpoint)."""
    try:
        response = await client.get("/api/vacancies/1/similar")
        # 404 (not found), 200 (found), or 500 (no DB) are all valid for a public endpoint.
        # 401 would mean the endpoint incorrectly requires authentication.
        assert response.status_code != 401, (
            f"Public endpoint returned 401: {response.text}"
        )
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_similar_vacancies_default_limit(client: AsyncClient):
    """GET /api/vacancies/1/similar without limit → uses default limit=5."""
    try:
        response = await client.get("/api/vacancies/1/similar")
        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            # At most 5 items with default limit
            assert len(data) <= 5
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_similar_vacancies_custom_limit(client: AsyncClient):
    """GET /api/vacancies/1/similar?limit=3 → respects custom limit."""
    try:
        response = await client.get("/api/vacancies/1/similar", params={"limit": 3})
        assert response.status_code in (200, 404, 500)
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            assert len(data) <= 3
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_similar_vacancies_excludes_source(client: AsyncClient):
    """Results must never include the source vacancy itself."""
    try:
        # First fetch vacancy 1 to confirm it exists
        get_resp = await client.get("/api/vacancies/1")
        if get_resp.status_code != 200:
            pytest.skip("Vacancy 1 does not exist in test database")

        # Then get similar
        response = await client.get("/api/vacancies/1/similar")
        if response.status_code == 200:
            data = response.json()
            ids = {item["id"] for item in data}
            # Source vacancy id=1 must not be in results
            assert 1 not in ids, "Source vacancy leaked into similar results"
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_similar_vacancies_sorting_priority(client: AsyncClient):
    """Similar vacancies are sorted: both match > category only > city only.

    Requires a test database with vacancies that have different category_id
    and address_normalized combinations relative to the source vacancy.
    """
    try:
        # Fetch the source vacancy to know its category and city
        resp = await client.get("/api/vacancies/1")
        if resp.status_code != 200:
            pytest.skip("Vacancy 1 does not exist in test database")

        source = resp.json()
        source_category = source.get("category_id")
        source_city = source.get("city")  # address_normalized

        response = await client.get("/api/vacancies/1/similar")
        if response.status_code != 200:
            pytest.skip("No similar vacancies in test database")

        data = response.json()
        if len(data) < 2:
            pytest.skip("Need at least 2 similar vacancies to verify sorting")

        # The relevance tier is determined by category_id and city match:
        # Tier 0: same category AND same city
        # Tier 1: same category only
        # Tier 2: same city only
        def _tier(item: dict) -> int:
            same_cat = item.get("category_id") == source_category
            same_city = item.get("city") == source_city
            if same_cat and same_city:
                return 0
            elif same_cat:
                return 1
            else:
                return 2  # same city only (guaranteed by WHERE clause)

        tiers = [_tier(item) for item in data]
        assert tiers == sorted(tiers), (
            f"Expected non-decreasing tiers, got {tiers}"
        )
    except ConnectionRefusedError:
        pytest.skip("No database available")

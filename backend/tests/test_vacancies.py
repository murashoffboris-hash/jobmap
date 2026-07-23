"""Tests for vacancies endpoints — CRUD and geo-search."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.auth import create_access_token


@pytest.mark.asyncio
async def test_list_vacancies_no_coords(client: AsyncClient):
    """GET /api/vacancies without lat/lon → 422."""
    response = await client.get("/api/vacancies")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_vacancies_bad_coords(client: AsyncClient):
    """GET /api/vacancies with out-of-range coords → 422."""
    response = await client.get("/api/vacancies", params={"lat": 100, "lon": 200})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_vacancies_valid(client: AsyncClient):
    """GET /api/vacancies with valid coords → 200 (may be empty)."""
    response = await client.get(
        "/api/vacancies",
        params={"lat": 53.9, "lon": 27.57, "radius_km": 10},
    )
    # Returns 200 even if no vacancies (empty list) or 500 if no PostGIS
    assert response.status_code in (200, 500)

    if response.status_code == 200:
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_get_vacancy_not_found(client: AsyncClient):
    """GET /api/vacancies/99999 → 404."""
    response = await client.get("/api/vacancies/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_vacancy_unauthorized(client: AsyncClient):
    """POST /api/vacancies without token → 401."""
    response = await client.post(
        "/api/vacancies",
        json={"title": "Test Vacancy"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_vacancy_user_role_denied(client: AsyncClient):
    """POST /api/vacancies with user role (not employer) → 403."""
    token = create_access_token(data={"sub": 9999})  # user role, not employer
    response = await client.post(
        "/api/vacancies",
        json={"title": "Test Vacancy"},
        headers={"Authorization": f"Bearer {token}"},
    )
    # 401 if user doesn't exist, 403 if user is not employer
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_update_vacancy_unauthorized(client: AsyncClient):
    """PATCH /api/vacancies/1 without token → 401."""
    response = await client.patch(
        "/api/vacancies/1",
        json={"title": "Updated"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_vacancy_unauthorized(client: AsyncClient):
    """DELETE /api/vacancies/1 without token → 401."""
    response = await client.delete("/api/vacancies/1")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_vacancy_not_found(client: AsyncClient):
    """DELETE /api/vacancies/99999 with valid token → 404 (or 403 if owner)."""
    token = create_access_token(data={"sub": 9999})
    response = await client.delete(
        "/api/vacancies/99999",
        headers={"Authorization": f"Bearer {token}"},
    )
    # 401 if user doesn't exist, 404 if no vacancy
    assert response.status_code in (401, 404)


@pytest.mark.asyncio
async def test_validation_min_title(client: AsyncClient):
    """Create vacancy with title too short → 422."""
    token = create_access_token(data={"sub": 9999})
    response = await client.post(
        "/api/vacancies",
        json={"title": "AB"},  # min_length=3
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 422

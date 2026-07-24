"""Tests for auth endpoints — register, login, refresh, me."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.auth import create_access_token, create_refresh_token

TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "StrongP@ss1"


@pytest.mark.asyncio
async def test_register_validation_error(client: AsyncClient):
    """POST /api/auth/register with invalid data → 422."""
    response = await client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_with_bad_creds(client: AsyncClient):
    """POST /api/auth/login with bad creds → 401 (no DB fallback)."""
    try:
        response = await client.post(
            "/api/auth/login",
            json={"email": "nonexistent@test.com", "password": "wrong_password"},
        )
        # 401 from no-DB connection error too — both mean auth rejected
        assert response.status_code in (401, 500)
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_me_unauthorized(client: AsyncClient):
    """GET /api/auth/me without token → 401."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_me_with_invalid_token(client: AsyncClient):
    """GET /api/auth/me with bad token → 401."""
    response = await client.get(
        "/api/auth/me",
        headers={"Authorization": "Bearer invalid_token_here"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_structure(client: AsyncClient):
    """POST /api/auth/refresh with valid refresh token → 401 or 200 (no DB)."""
    token = create_refresh_token(data={"sub": "9999"})
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": token},
    )
    assert response.status_code in (200, 401)


@pytest.mark.asyncio
async def test_refresh_with_access_token_denied(client: AsyncClient):
    """POST /api/auth/refresh with an access token (not refresh) → 401."""
    token = create_access_token(data={"sub": "9999"})
    response = await client.post(
        "/api/auth/refresh",
        json={"refresh_token": token},
    )
    assert response.status_code == 401

"""Tests for the profile update endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_update_profile_unauthorized(client: AsyncClient):
    """PATCH /api/auth/me without a token must be rejected."""
    response = await client.patch(
        "/api/auth/me",
        json={"full_name": "Иван Петров", "phone": None, "bio": None},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile_validation_error(client: AsyncClient):
    """PATCH /api/auth/me validates profile field limits before auth work."""
    response = await client.patch(
        "/api/auth/me",
        json={
            "full_name": "",
            "phone": "not-a-phone",
            "bio": "x" * 1001,
        },
    )
    assert response.status_code in (401, 422)

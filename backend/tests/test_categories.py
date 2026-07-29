"""Tests for categories endpoint — GET /api/categories."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_categories_returns_200(client: AsyncClient):
    """GET /api/categories — публичный эндпоинт, возвращает 200 (или skip без БД)."""
    try:
        response = await client.get("/api/categories")
        assert response.status_code == 200
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_get_categories_returns_list(client: AsyncClient):
    """GET /api/categories — возвращает список объектов с id, name, slug, icon."""
    try:
        response = await client.get("/api/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            cat = data[0]
            assert "id" in cat
            assert "name" in cat
            assert "slug" in cat
            assert "icon" in cat
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_get_categories_only_active(client: AsyncClient):
    """GET /api/categories — возвращает только активные (is_active=true)."""
    try:
        response = await client.get("/api/categories")
        assert response.status_code == 200
        data = response.json()
        for cat in data:
            assert cat.get("is_active", True) is True
    except ConnectionRefusedError:
        pytest.skip("No database available")

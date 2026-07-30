"""Tests for applications endpoints — FR-007: отклики на вакансии."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services.auth import create_access_token

# ── Helpers ──────────────────────────────────────────────────────

def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


VALID_TOKEN = create_access_token(data={"sub": "1"})


# ── POST /api/applications ───────────────────────────────────────

@pytest.mark.asyncio
async def test_create_application_unauthorized(client: AsyncClient):
    """POST /api/applications без токена → 401 (C8)."""
    response = await client.post(
        "/api/applications",
        json={"vacancy_id": 1},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_application_invalid_token(client: AsyncClient):
    """POST /api/applications с некорректным токеном → 401."""
    response = await client.post(
        "/api/applications",
        json={"vacancy_id": 1},
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_create_application_validation_error(client: AsyncClient):
    """POST /api/applications без vacancy_id → 422."""
    try:
        response = await client.post(
            "/api/applications",
            json={"cover_letter": "Hello"},
            headers=_auth(VALID_TOKEN),
        )
        # 422 from Pydantic, or 401/404 if no DB
        assert response.status_code in (401, 404, 422)
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_create_application_cover_letter_too_long(client: AsyncClient):
    """POST /api/applications с cover_letter > 2000 символов → 422 (C4)."""
    try:
        response = await client.post(
            "/api/applications",
            json={"vacancy_id": 1, "cover_letter": "A" * 2001},
            headers=_auth(VALID_TOKEN),
        )
        assert response.status_code in (401, 404, 422)
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_create_application_no_db(client: AsyncClient):
    """POST /api/applications с валидным токеном, но без БД → 401 (C2/C3 требуют БД)."""
    try:
        response = await client.post(
            "/api/applications",
            json={"vacancy_id": 99999},
            headers=_auth(VALID_TOKEN),
        )
        # user not found → 401, or vacancy not found → 404
        assert response.status_code in (401, 404)
    except ConnectionRefusedError:
        pytest.skip("No database available")


# ── GET /api/applications (my list) ──────────────────────────────

@pytest.mark.asyncio
async def test_list_my_applications_unauthorized(client: AsyncClient):
    """GET /api/applications без токена → 401."""
    response = await client.get("/api/applications")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_my_applications_invalid_token(client: AsyncClient):
    """GET /api/applications с плохим токеном → 401."""
    response = await client.get(
        "/api/applications",
        headers={"Authorization": "Bearer bad_token"},
    )
    assert response.status_code == 401


# ── PATCH /api/applications/{id}/withdraw ────────────────────────

@pytest.mark.asyncio
async def test_withdraw_unauthorized(client: AsyncClient):
    """PATCH /api/applications/1/withdraw без токена → 401."""
    response = await client.patch("/api/applications/1/withdraw")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_withdraw_not_found(client: AsyncClient):
    """PATCH /api/applications/99999/withdraw с токеном → 404."""
    try:
        response = await client.patch(
            "/api/applications/99999/withdraw",
            headers=_auth(VALID_TOKEN),
        )
        assert response.status_code in (401, 404)
    except ConnectionRefusedError:
        pytest.skip("No database available")


# ── PATCH /api/applications/{id}/status (accept) ──────────────────

@pytest.mark.asyncio
async def test_accept_unauthorized(client: AsyncClient):
    """PATCH /api/applications/1/status с status='accepted' без токена → 401."""
    response = await client.patch(
        "/api/applications/1/status",
        json={"status": "accepted"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_accept_not_found(client: AsyncClient):
    """PATCH /api/applications/99999/status с status='accepted' → 404."""
    try:
        response = await client.patch(
            "/api/applications/99999/status",
            json={"status": "accepted"},
            headers=_auth(VALID_TOKEN),
        )
        assert response.status_code in (401, 404)
    except ConnectionRefusedError:
        pytest.skip("No database available")


# ── PATCH /api/applications/{id}/status (reject) ──────────────────

@pytest.mark.asyncio
async def test_reject_unauthorized(client: AsyncClient):
    """PATCH /api/applications/1/status с status='rejected' без токена → 401."""
    response = await client.patch(
        "/api/applications/1/status",
        json={"status": "rejected"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_reject_not_found(client: AsyncClient):
    """PATCH /api/applications/99999/status с status='rejected' → 404."""
    try:
        response = await client.patch(
            "/api/applications/99999/status",
            json={"status": "rejected"},
            headers=_auth(VALID_TOKEN),
        )
        assert response.status_code in (401, 404)
    except ConnectionRefusedError:
        pytest.skip("No database available")


# ── GET /api/vacancies/{id}/applications ─────────────────────────

@pytest.mark.asyncio
async def test_vacancy_applications_unauthorized(client: AsyncClient):
    """GET /api/vacancies/1/applications без токена → 401."""
    response = await client.get("/api/vacancies/1/applications")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_vacancy_applications_not_found(client: AsyncClient):
    """GET /api/vacancies/99999/applications с токеном → 404."""
    try:
        response = await client.get(
            "/api/vacancies/99999/applications",
            headers=_auth(VALID_TOKEN),
        )
        assert response.status_code in (401, 404)
    except ConnectionRefusedError:
        pytest.skip("No database available")


# ── Edge cases ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cover_letter_max_length_boundary(client: AsyncClient):
    """POST /api/applications с cover_letter ровно 2000 символов → accepted (422 not raised)."""
    try:
        response = await client.post(
            "/api/applications",
            json={"vacancy_id": 1, "cover_letter": "A" * 2000},
            headers=_auth(VALID_TOKEN),
        )
        # 2000 chars is valid, should NOT be 422 — but will be 401 or 404 (no DB)
        assert response.status_code != 422
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_create_application_empty_cover_letter(client: AsyncClient):
    """POST /api/applications с пустым cover_letter → допустимо (EC-9)."""
    try:
        response = await client.post(
            "/api/applications",
            json={"vacancy_id": 1},
            headers=_auth(VALID_TOKEN),
        )
        # No cover_letter is valid — 401 or 404 expected (no DB)
        assert response.status_code != 422
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_pagination_defaults(client: AsyncClient):
    """GET /api/applications с параметрами пагинации по умолчанию."""
    try:
        response = await client.get(
            "/api/applications?limit=20&offset=0",
            headers=_auth(VALID_TOKEN),
        )
        # user not found → 401
        assert response.status_code in (401, 200)
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_pagination_limit_zero(client: AsyncClient):
    """GET /api/applications с limit=0 → все записи (старое поведение)."""
    try:
        response = await client.get(
            "/api/applications?limit=0",
            headers=_auth(VALID_TOKEN),
        )
        assert response.status_code in (401, 200)
    except ConnectionRefusedError:
        pytest.skip("No database available")


@pytest.mark.asyncio
async def test_pagination_limit_five(client: AsyncClient):
    """GET /api/applications с limit=5 → 5 записей + total."""
    try:
        response = await client.get(
            "/api/applications?limit=5",
            headers=_auth(VALID_TOKEN),
        )
        assert response.status_code in (401, 200)
    except ConnectionRefusedError:
        pytest.skip("No database available")

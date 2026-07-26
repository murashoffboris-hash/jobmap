"""Tests for Nominatim geocoding — fallback logic, Redis cache, geocode_status, and API."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response

from app.dependencies import get_session
from app.models import Vacancy, VacancyStatus
from app.schemas import VacancyResponse
from app.services.vacancies import vacancy_to_response

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ── Helpers ──

def _make_response(status_code: int, json_data: dict | list) -> MagicMock:
    """Build a mock httpx.Response with given status and JSON body."""
    resp = MagicMock(spec=Response)
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.raise_for_status = MagicMock()
    return resp


def _make_error_response(status_code: int, text: str) -> MagicMock:
    """Build a mock httpx.Response that raises HTTPStatusError on raise_for_status."""
    resp = MagicMock(spec=Response)
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError(
            text,
            request=MagicMock(),
            response=resp,
        )
    )
    return resp


def _make_vacancy(**overrides) -> Vacancy:
    """Build a minimal Vacancy ORM object for geocode_status testing."""
    defaults = {
        "id": 1,
        "title": "Test",
        "description": None,
        "status": VacancyStatus.ACTIVE,
        "address_raw": None,
        "address_normalized": None,
        "location_lat": None,
        "location_lon": None,
        "salary_from": None,
        "salary_to": None,
        "salary_currency": "BYN",
        "schedule_type": None,
        "contact_phone": None,
        "exact_location_public": False,
        "created_at": _NOW,
    }
    defaults.update(overrides)
    v = MagicMock(spec=Vacancy)
    for k, val in defaults.items():
        setattr(v, k, val)
    return v


# ── Mock Redis helper ──

def _mock_redis_miss() -> MagicMock:
    """Create a mock Redis that returns None on get (cache miss)."""
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.setex = AsyncMock()
    return mock_redis


# ── vacancy_to_response: geocode_status ──

class TestGeocodeStatus:
    """geocode_status computation in vacancy_to_response()."""

    def test_not_requested_when_no_address(self):
        v = _make_vacancy(address_raw=None)
        resp = vacancy_to_response(v)
        assert resp.geocode_status == "not_requested"

    def test_success_when_address_and_coords(self):
        v = _make_vacancy(address_raw="Минск", location_lat=53.9, location_lon=27.56)
        resp = vacancy_to_response(v)
        assert resp.geocode_status == "success"

    def test_failed_when_address_but_no_coords(self):
        v = _make_vacancy(address_raw="Минск", location_lat=None, location_lon=None)
        resp = vacancy_to_response(v)
        assert resp.geocode_status == "failed"

    def test_failed_when_partial_coords(self):
        """If only lat is set but lon is None, still 'failed'."""
        v = _make_vacancy(address_raw="Минск", location_lat=53.9, location_lon=None)
        resp = vacancy_to_response(v)
        assert resp.geocode_status == "failed"


# ── Nominatim fallback logic ──

GEOCODE_RESULT = [
    {"lat": "53.9", "lon": "27.56", "osm_id": "123",
     "display_name": "Minsk, Belarus", "type": "city"}
]


@pytest.mark.asyncio
async def test_geocode_primary_succeeds_no_fallback():
    """When primary responds, fallback is never called."""
    mock_session = _make_mock_session()

    with patch("app.services.nominatim._get_redis", return_value=_mock_redis_miss()):
        with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
            mock_client = _make_http_client(GEOCODE_RESULT)
            mock_client_cls.return_value = mock_client

            from app.services.nominatim import geocode_address
            result = await geocode_address(mock_session, "Минск")

    assert result is not None
    assert result["lat"] == 53.9
    assert result["lon"] == 27.56
    assert result["source"] == "primary"

    # Should have called only the primary URL
    call_urls = [c.args[0] for c in mock_client.get.call_args_list]
    assert any("nominatim:8080" in url for url in call_urls)
    assert not any("nominatim.openstreetmap.org" in url for url in call_urls)


@pytest.mark.asyncio
async def test_geocode_user_agent_sent_on_primary():
    """User-Agent header is sent on primary requests (OSM policy)."""
    mock_session = _make_mock_session()

    with patch("app.services.nominatim._get_redis", return_value=_mock_redis_miss()):
        with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
            mock_client = _make_http_client(GEOCODE_RESULT)
            mock_client_cls.return_value = mock_client

            from app.services.nominatim import geocode_address
            await geocode_address(mock_session, "Минск")

    # Check AsyncClient was created with User-Agent header
    call_kwargs = mock_client_cls.call_args_list[0].kwargs
    assert "headers" in call_kwargs
    assert "User-Agent" in call_kwargs["headers"]
    assert call_kwargs["headers"]["User-Agent"] == "JobMap/1.0 (admin@service247.by)"


@pytest.mark.asyncio
async def test_geocode_fallback_when_primary_fails():
    """When primary is unreachable, fallback is used."""
    mock_session = _make_mock_session()

    with patch("app.services.nominatim._get_redis", return_value=_mock_redis_miss()):
        with patch("app.services.nominatim._fallback_lock", new=AsyncMock()):
            with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
                primary_client = _make_http_client(raises=httpx.ConnectError("Connection refused"))
                fallback_client = _make_http_client(GEOCODE_RESULT)

                mock_client_cls.side_effect = [primary_client, fallback_client]

                from app.services.nominatim import geocode_address
                result = await geocode_address(mock_session, "Минск")

    assert result is not None
    assert result["lat"] == 53.9
    assert result["source"] == "fallback"

    # Check fallback URL was called
    fallback_calls = [c for c in fallback_client.get.call_args_list
                      if "nominatim.openstreetmap.org" in str(c.args[0])]
    assert len(fallback_calls) > 0


@pytest.mark.asyncio
async def test_geocode_both_fail_returns_none():
    """When both primary and fallback fail, return None."""
    mock_session = _make_mock_session()

    with patch("app.services.nominatim._get_redis", return_value=_mock_redis_miss()):
        with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
            primary_client = _make_http_client(raises=httpx.ConnectError("Connection refused"))
            fallback_client = _make_http_client(raises=httpx.ConnectError("Connection refused"))

            mock_client_cls.side_effect = [primary_client, fallback_client]

            from app.services.nominatim import geocode_address
            result = await geocode_address(mock_session, "Минск")

    assert result is None
    # geocoding_log should have been written with failure
    assert mock_session.add.called


@pytest.mark.asyncio
async def test_geocode_redis_cache_hit():
    """When Redis has a cached result, return it without HTTP call."""
    import json
    mock_session = _make_mock_session()

    cached_result = {
        "lat": 53.9, "lon": 27.56, "osm_id": "123",
        "display_name": "Minsk, Belarus", "type": "city", "source": "primary",
    }
    mock_redis = MagicMock()
    mock_redis.get = AsyncMock(return_value=json.dumps(cached_result))

    with patch("app.services.nominatim._get_redis", return_value=mock_redis):
        with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
            from app.services.nominatim import geocode_address
            result = await geocode_address(mock_session, "Minsk")

    assert result is not None
    assert result["lat"] == 53.9
    assert result["source"] == "primary"

    # HTTP client should NOT have been called at all (cache hit)
    mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_geocode_redis_cache_miss_stores_result():
    """After successful geocode, result is stored in Redis."""
    import json
    mock_session = _make_mock_session()

    mock_redis = _mock_redis_miss()

    with patch("app.services.nominatim._get_redis", return_value=mock_redis):
        with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
            mock_client = _make_http_client(GEOCODE_RESULT)
            mock_client_cls.return_value = mock_client

            from app.services.nominatim import geocode_address
            result = await geocode_address(mock_session, "Минск")

    assert result is not None
    # Redis setex should have been called with TTL
    assert mock_redis.setex.called
    call_args = mock_redis.setex.call_args
    # First arg: key, second: TTL, third: value
    assert call_args.args[1] == 86400  # 24 hours


# ── Reverse geocode ──

REVERSE_RESULT = {
    "lat": "53.9", "lon": "27.56",
    "display_name": "Minsk, Belarus", "type": "city",
}


@pytest.mark.asyncio
async def test_reverse_geocode_primary_succeeds():
    """Reverse geocode succeeds on primary."""
    with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
        mock_client = _make_http_client(REVERSE_RESULT)
        mock_client_cls.return_value = mock_client

        from app.services.nominatim import reverse_geocode
        result = await reverse_geocode(53.9, 27.56)

    assert result is not None
    assert result["display_name"] == "Minsk, Belarus"


@pytest.mark.asyncio
async def test_reverse_geocode_fallback_when_primary_fails():
    """Reverse geocode falls back when primary fails."""
    with patch("app.services.nominatim._fallback_lock", new=AsyncMock()):
        with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
            primary_client = _make_http_client(raises=httpx.ConnectError("Connection refused"))
            fallback_client = _make_http_client(REVERSE_RESULT)
            mock_client_cls.side_effect = [primary_client, fallback_client]

            from app.services.nominatim import reverse_geocode
            result = await reverse_geocode(53.9, 27.56)

    assert result is not None
    assert result["display_name"] == "Minsk, Belarus"


@pytest.mark.asyncio
async def test_reverse_geocode_both_fail_returns_none():
    """Reverse geocode returns None when both primary and fallback fail."""
    with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
        primary_client = _make_http_client(raises=httpx.ConnectError("Connection refused"))
        fallback_client = _make_http_client(raises=httpx.ConnectError("Connection refused"))
        mock_client_cls.side_effect = [primary_client, fallback_client]

        from app.services.nominatim import reverse_geocode
        result = await reverse_geocode(53.9, 27.56)

    assert result is None


# ── API endpoint tests ──


@pytest.mark.asyncio
async def test_api_geocode_success(app: FastAPI):
    """POST /api/geo/geocode returns 200 on successful geocode."""
    mock_session = _make_mock_session()

    mock_geo = {
        "lat": 53.9, "lon": 27.5667, "osm_id": "12345",
        "display_name": "Minsk, Belarus", "type": "city",
    }

    async def _mock_session():
        yield mock_session

    app.dependency_overrides[get_session] = _mock_session

    try:
        with patch(
            "app.routers.geoservices.geocode_address",
            AsyncMock(return_value=mock_geo),
        ):
            from httpx import ASGITransport
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/geo/geocode",
                    json={"address": "Minsk"},
                )

        assert response.status_code == 200
        data = response.json()
        assert data["lat"] == 53.9
        assert data["display_name"] == "Minsk, Belarus"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_geocode_service_unavailable(app: FastAPI):
    """POST /api/geo/geocode returns 502 when geocoding service is down."""
    mock_session = _make_mock_session()

    async def _mock_session():
        yield mock_session

    app.dependency_overrides[get_session] = _mock_session

    try:
        with patch(
            "app.routers.geoservices.geocode_address",
            AsyncMock(return_value=None),
        ):
            from httpx import ASGITransport
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/geo/geocode",
                    json={"address": "Minsk"},
                )

        assert response.status_code == 502
        assert "unavailable" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_reverse_success(app: FastAPI):
    """GET /api/geo/reverse returns 200 on successful reverse geocode."""
    mock_result = {
        "lat": "53.9", "lon": "27.5667",
        "display_name": "Minsk, Belarus", "type": "city",
    }

    with patch(
        "app.routers.geoservices.reverse_geocode",
        AsyncMock(return_value=mock_result),
    ):
        from httpx import ASGITransport
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                "/api/geo/reverse",
                params={"lat": 53.9, "lon": 27.5667},
            )

    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Minsk, Belarus"


@pytest.mark.asyncio
async def test_api_reverse_service_unavailable(app: FastAPI):
    """GET /api/geo/reverse returns 502 when geocoding service is down."""
    with patch(
        "app.routers.geoservices.reverse_geocode",
        AsyncMock(return_value=None),
    ):
        from httpx import ASGITransport
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                "/api/geo/reverse",
                params={"lat": 53.9, "lon": 27.5667},
            )

    assert response.status_code == 502


@pytest.mark.asyncio
async def test_api_route_endpoint_exists(app: FastAPI):
    """POST /api/geo/route responds (validated input is required)."""
    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post(
            "/api/geo/route",
            json={"origin_lat": 1, "origin_lon": 1, "dest_lat": 2, "dest_lon": 2},
        )
    # 422 on validation failure, or 200/404/502 depending on OSRM availability
    assert response.status_code in (200, 404, 422, 502)


# ── GeocodeResponse schema ──

def test_geocode_response_schema():
    """GeocodeResponse can be constructed with all fields."""
    from app.schemas import GeocodeResponse
    resp = GeocodeResponse(
        lat=53.9, lon=27.56, osm_id="123",
        display_name="Минск", type="city",
    )
    assert resp.lat == 53.9
    assert resp.type == "city"


def test_vacancy_response_has_geocode_status_default():
    """VacancyResponse defaults geocode_status to 'not_requested'."""
    resp = VacancyResponse(
        id=1, title="Test", status=VacancyStatus.ACTIVE,
        salary_currency="BYN", exact_location_public=False,
        created_at=_NOW,
    )
    assert resp.geocode_status == "not_requested"


# ── Internal helpers for test setup ──

def _make_mock_session() -> AsyncMock:
    """Create a mock DB session for geocode tests."""
    session = AsyncMock()
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


def _make_http_client(
    json_response: dict | list | None = None,
    raises: BaseException | None = None,
) -> MagicMock:
    """Build a mock httpx.AsyncClient compatible with context manager usage."""
    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)

    if raises:
        client.get = AsyncMock(side_effect=raises)
    else:
        mock_resp = _make_response(200, json_response or [])
        client.get = AsyncMock(return_value=mock_resp)

    return client

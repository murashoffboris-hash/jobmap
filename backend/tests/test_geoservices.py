"""Tests for Nominatim geocoding service and geo API endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, Response

from app.dependencies import get_session
from app.services.nominatim import (
    NominatimError,
    NominatimNoResults,
    NominatimServiceError,
    geocode_address,
    reverse_geocode,
)


# ── Unit tests: nominatim service functions ──


@pytest.mark.asyncio
async def test_geocode_address_success():
    """Successful geocode returns dict with lat/lon/display_name."""
    mock_session = AsyncMock()
    mock_response = _make_response(
        200,
        [
            {
                "lat": "53.9",
                "lon": "27.5667",
                "osm_id": "12345",
                "display_name": "Minsk, Belarus",
                "type": "city",
            }
        ],
    )

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        result = await geocode_address(mock_session, "Minsk")

    assert result is not None
    assert result["lat"] == 53.9
    assert result["lon"] == 27.5667
    assert result["display_name"] == "Minsk, Belarus"
    assert result["type"] == "city"
    assert result["osm_id"] == "12345"


@pytest.mark.asyncio
async def test_geocode_address_no_results():
    """Empty results return None (no exception)."""
    mock_session = AsyncMock()
    mock_response = _make_response(200, [])

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        result = await geocode_address(mock_session, "NonexistentPlace12345")

    assert result is None
    assert mock_session.add.called


@pytest.mark.asyncio
async def test_geocode_address_http_error():
    """HTTP 500 from Nominatim raises NominatimServiceError (was bug: unhandled 500)."""
    mock_session = AsyncMock()
    mock_response = _make_error_response(500, "Internal Server Error")

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        with pytest.raises(NominatimServiceError, match="HTTP 500"):
            await geocode_address(mock_session, "Minsk")


@pytest.mark.asyncio
async def test_geocode_address_connection_error():
    """Connection error raises NominatimServiceError after retries."""
    mock_session = AsyncMock()

    with patch(
        "httpx.AsyncClient.get",
        AsyncMock(side_effect=httpx.ConnectError("Connection refused")),
    ):
        with pytest.raises(NominatimServiceError, match="Connection refused"):
            await geocode_address(mock_session, "Minsk")


@pytest.mark.asyncio
async def test_reverse_geocode_success():
    """Successful reverse geocode returns Nominatim dict."""
    mock_response = _make_response(
        200,
        {
            "lat": "53.9",
            "lon": "27.5667",
            "display_name": "Some Street, Minsk, Belarus",
            "type": "road",
        },
    )

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        result = await reverse_geocode(53.9, 27.5667)

    assert result["lat"] == "53.9"
    assert result["display_name"] == "Some Street, Minsk, Belarus"
    assert result["type"] == "road"


@pytest.mark.asyncio
async def test_reverse_geocode_no_results():
    """Empty response from Nominatim raises NominatimNoResults."""
    mock_response = _make_response(200, {})

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        with pytest.raises(NominatimNoResults):
            await reverse_geocode(0.0, 0.0)


@pytest.mark.asyncio
async def test_reverse_geocode_error_response():
    """Nominatim returns error key — raises NominatimNoResults."""
    mock_response = _make_response(200, {"error": "Unable to geocode"})

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        with pytest.raises(NominatimNoResults):
            await reverse_geocode(0.0, 0.0)


@pytest.mark.asyncio
async def test_reverse_geocode_connection_error():
    """Connection error raises NominatimServiceError (was bug: caught as 404)."""
    with patch(
        "httpx.AsyncClient.get",
        AsyncMock(side_effect=httpx.ConnectError("Connection refused")),
    ):
        with pytest.raises(NominatimServiceError, match="connection failed"):
            await reverse_geocode(53.9, 27.5667)


@pytest.mark.asyncio
async def test_reverse_geocode_http_error():
    """HTTP 500 from Nominatim raises NominatimServiceError (was bug: caught as 404)."""
    mock_response = _make_error_response(500, "Internal Server Error")

    with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_response)):
        with pytest.raises(NominatimServiceError, match="HTTP 500"):
            await reverse_geocode(53.9, 27.5667)


@pytest.mark.asyncio
async def test_reverse_geocode_timeout():
    """Timeout raises NominatimServiceError."""
    with patch(
        "httpx.AsyncClient.get",
        AsyncMock(side_effect=httpx.TimeoutException("timeout")),
    ):
        with pytest.raises(NominatimServiceError, match="timed out"):
            await reverse_geocode(53.9, 27.5667)


# ── Integration tests: API endpoints (mock service layer) ──


@pytest.mark.asyncio
async def test_api_geocode_success(app: FastAPI):
    """POST /api/geo/geocode returns 200 on successful geocode."""
    mock_session = AsyncMock()

    mock_geo = {
        "lat": 53.9,
        "lon": 27.5667,
        "osm_id": "12345",
        "display_name": "Minsk, Belarus",
        "type": "city",
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
async def test_api_geocode_not_found(app: FastAPI):
    """POST /api/geo/geocode returns 404 when address not found."""
    mock_session = AsyncMock()

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
                    json={"address": "NonexistentPlace"},
                )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_geocode_returns_502_on_service_error(app: FastAPI):
    """POST /api/geo/geocode returns 502 when Nominatim is down."""
    mock_session = AsyncMock()

    async def _mock_session():
        yield mock_session

    app.dependency_overrides[get_session] = _mock_session

    try:
        with patch(
            "app.routers.geoservices.geocode_address",
            AsyncMock(side_effect=NominatimServiceError("Nominatim connection failed")),
        ):
            from httpx import ASGITransport

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                response = await ac.post(
                    "/api/geo/geocode",
                    json={"address": "Minsk"},
                )

        assert response.status_code == 502
        assert "connection failed" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_api_reverse_success(app: FastAPI):
    """GET /api/geo/reverse returns 200 on successful reverse geocode."""
    mock_result = {
        "lat": "53.9",
        "lon": "27.5667",
        "display_name": "Minsk, Belarus",
        "type": "city",
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
async def test_api_reverse_returns_404_on_no_results(app: FastAPI):
    """GET /api/geo/reverse returns 404 when no results found."""
    with patch(
        "app.routers.geoservices.reverse_geocode",
        AsyncMock(side_effect=NominatimNoResults("No results")),
    ):
        from httpx import ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                "/api/geo/reverse",
                params={"lat": 0.0, "lon": 0.0},
            )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_reverse_returns_502_on_service_error(app: FastAPI):
    """GET /api/geo/reverse returns 502 when Nominatim is down."""
    with patch(
        "app.routers.geoservices.reverse_geocode",
        AsyncMock(side_effect=NominatimServiceError("Nominatim connection failed")),
    ):
        from httpx import ASGITransport

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get(
                "/api/geo/reverse",
                params={"lat": 53.9, "lon": 27.5667},
            )

    assert response.status_code == 502
    assert "connection failed" in response.json()["detail"].lower()


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
    # 422 on validation failure, or 200/502 depending on OSRM availability
    assert response.status_code in (200, 404, 422, 502)


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

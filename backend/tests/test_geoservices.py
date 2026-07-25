"""Tests for geoservices — fallback logic, geocode_status, health endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.models import Vacancy, VacancyStatus
from app.schemas import VacancyResponse
from app.services.vacancies import vacancy_to_response

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ── vacancy_to_response: geocode_status ──


def _make_vacancy(**overrides) -> Vacancy:
    """Build a minimal Vacancy ORM object for testing."""
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


@pytest.mark.asyncio
async def test_geocode_primary_succeeds_no_fallback():
    """When primary responds, fallback is never called."""
    with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Primary responds successfully
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = [
            {"lat": "53.9", "lon": "27.56", "osm_id": "123", "display_name": "Минск", "type": "city"}
        ]
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()

        from app.services.nominatim import geocode_address
        result = await geocode_address(session, "Минск")

        assert result is not None
        assert result["lat"] == 53.9
        assert result["lon"] == 27.56
        assert result["source"] == "primary"

        # Should have called only the primary URL
        call_urls = [c.args[0] for c in mock_client.get.call_args_list]
        assert any("nominatim:8080" in url for url in call_urls)
        assert not any("nominatim.openstreetmap.org" in url for url in call_urls)


@pytest.mark.asyncio
async def test_geocode_fallback_when_primary_fails():
    """When primary is unreachable, fallback is used."""
    with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
        # We need two separate client instances — one for primary (fails), one for fallback (succeeds)
        primary_client = MagicMock()
        primary_client.__aenter__ = AsyncMock(return_value=primary_client)
        primary_client.__aexit__ = AsyncMock(return_value=None)

        fallback_client = MagicMock()
        fallback_client.__aenter__ = AsyncMock(return_value=fallback_client)
        fallback_client.__aexit__ = AsyncMock(return_value=None)

        # Primary raises ConnectError
        from httpx import ConnectError
        primary_client.get = AsyncMock(side_effect=ConnectError("Connection refused"))
        # Fallback succeeds
        fallback_resp = MagicMock()
        fallback_resp.raise_for_status.return_value = None
        fallback_resp.json.return_value = [
            {"lat": "53.9", "lon": "27.56", "osm_id": "456", "display_name": "Minsk, Belarus", "type": "city"}
        ]
        fallback_client.get = AsyncMock(return_value=fallback_resp)

        # Return primary first, then fallback
        mock_client_cls.side_effect = [primary_client, fallback_client]

        # Also mock the rate limiter to skip sleep
        with patch("app.services.nominatim._fallback_lock", new=AsyncMock()):
            with patch("app.services.nominatim._rate_limited_fallback_request") as mock_rl_req:
                mock_rl_req.return_value = fallback_resp

                session = AsyncMock()
                session.add = MagicMock()
                session.commit = AsyncMock()

                from app.services.nominatim import geocode_address
                result = await geocode_address(session, "Минск")

                assert result is not None
                assert result["lat"] == 53.9
                assert result["lon"] == 27.56
                assert result["source"] == "fallback"


@pytest.mark.asyncio
async def test_geocode_both_fail_returns_none():
    """When both primary and fallback fail, return None."""
    with patch("app.services.nominatim.httpx.AsyncClient") as mock_client_cls:
        from httpx import ConnectError

        primary_client = MagicMock()
        primary_client.__aenter__ = AsyncMock(return_value=primary_client)
        primary_client.__aexit__ = AsyncMock(return_value=None)
        primary_client.get = AsyncMock(side_effect=ConnectError("Connection refused"))

        fallback_client = MagicMock()
        fallback_client.__aenter__ = AsyncMock(return_value=fallback_client)
        fallback_client.__aexit__ = AsyncMock(return_value=None)
        fallback_client.get = AsyncMock(side_effect=ConnectError("Connection refused"))

        mock_client_cls.side_effect = [primary_client, fallback_client]

        session = AsyncMock()
        session.add = MagicMock()
        session.commit = AsyncMock()

        from app.services.nominatim import geocode_address
        result = await geocode_address(session, "Минск")

        assert result is None


# ── OSRM fallback logic ──


@pytest.mark.asyncio
async def test_osrm_primary_succeeds():
    """OSRM primary responds — no fallback."""
    with patch("app.services.osrm.httpx.AsyncClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "code": "Ok",
            "routes": [{"distance": 5000, "duration": 300, "geometry": "abc"}],
        }
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client_cls.return_value = mock_client

        from app.services.osrm import get_route
        result = await get_route(53.9, 27.56, 53.91, 27.57)

        assert result is not None
        assert result["distance_m"] == 5000

        call_urls = [c.args[0] for c in mock_client.get.call_args_list]
        assert any("osrm:5000" in url for url in call_urls)
        assert not any("router.project-osrm.org" in url for url in call_urls)


@pytest.mark.asyncio
async def test_osrm_fallback_when_primary_fails():
    """OSRM primary fails → fallback succeeds."""
    with patch("app.services.osrm.httpx.AsyncClient") as mock_client_cls:
        from httpx import ConnectError

        primary_client = MagicMock()
        primary_client.__aenter__ = AsyncMock(return_value=primary_client)
        primary_client.__aexit__ = AsyncMock(return_value=None)
        primary_client.get = AsyncMock(side_effect=ConnectError("Connection refused"))

        fallback_client = MagicMock()
        fallback_client.__aenter__ = AsyncMock(return_value=fallback_client)
        fallback_client.__aexit__ = AsyncMock(return_value=None)
        fallback_resp = MagicMock()
        fallback_resp.raise_for_status.return_value = None
        fallback_resp.json.return_value = {
            "code": "Ok",
            "routes": [{"distance": 5000, "duration": 300}],
        }
        fallback_client.get = AsyncMock(return_value=fallback_resp)

        mock_client_cls.side_effect = [primary_client, fallback_client]

        from app.services.osrm import get_route
        result = await get_route(53.9, 27.56, 53.91, 27.57)

        assert result is not None
        assert result["distance_m"] == 5000

        # Check fallback URL was called
        fallback_calls = [c for c in fallback_client.get.call_args_list
                          if "router.project-osrm.org" in str(c.args[0])]
        assert len(fallback_calls) > 0


# ── Health endpoint ──


@pytest.mark.asyncio
async def test_health_endpoint_returns_optional_components(client: AsyncClient):
    """GET /health returns both mandatory (dependencies) and optional keys."""
    try:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "dependencies" in data
        assert "optional" in data
        assert "postgresql" in data["dependencies"]
        assert "redis" in data["dependencies"]
        # Optional components may be degraded but must be present
        assert "nominatim" in data["optional"]
        assert "osrm" in data["optional"]
    except ConnectionRefusedError:
        pytest.skip("No database available")


# ── GeocodeResponse schema ──


def test_geocode_response_schema():
    """GeocodeResponse can be constructed with all fields."""
    from app.schemas import GeocodeResponse
    resp = GeocodeResponse(
        lat=53.9,
        lon=27.56,
        osm_id="123",
        display_name="Минск",
        type="city",
    )
    assert resp.lat == 53.9
    assert resp.lon == 27.56
    assert resp.osm_id == "123"


def test_vacancy_response_has_geocode_status_default():
    """VacancyResponse defaults geocode_status to 'not_requested'."""
    resp = VacancyResponse(
        id=1,
        title="Test",
        status=VacancyStatus.ACTIVE,
        salary_currency="BYN",
        exact_location_public=False,
        created_at=_NOW,
    )
    assert resp.geocode_status == "not_requested"

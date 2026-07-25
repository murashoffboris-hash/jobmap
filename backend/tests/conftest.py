"""Test configuration — fixtures for auth and API testing."""

from __future__ import annotations

from typing import AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.models import User, UserRole


@pytest.fixture(scope="session")
def app() -> FastAPI:
    """Create the FastAPI application for testing."""
    return create_app()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client against the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def mock_user_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP client with mocked auth and DB dependencies.

    Uses dependency_overrides to replace get_current_user and get_session
    so tests don't need a real database or JWT.
    """
    from unittest.mock import AsyncMock, MagicMock

    from app.routers.auth import get_current_user as auth_get_current_user
    from app.dependencies import get_session
    from app.models import Profile, UserRole

    # Build a mock authenticated user with a profile
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "mock@example.com"
    mock_user.role = UserRole.USER
    mock_user.is_active = True

    mock_profile = MagicMock(spec=Profile)
    mock_profile.user_id = 1
    mock_profile.full_name = "Mock User"
    mock_profile.phone = None
    mock_profile.bio = None
    mock_profile.avatar_url = None
    mock_user.profile = mock_profile

    mock_session = AsyncMock()
    # Set up execute() to return a result with scalar_one_or_none()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_profile
    mock_session.execute.return_value = mock_result
    # For the upload endpoint, session.execute is called twice (profile query + commit)
    # For simplicity, always return the same result

    def _get_mock_user():
        return mock_user

    async def _get_mock_session():
        yield mock_session

    app.dependency_overrides[auth_get_current_user] = _get_mock_user
    app.dependency_overrides[get_session] = _get_mock_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.clear()


def make_auth_header(token: str) -> dict[str, str]:
    """Build an Authorization header from a Bearer token string."""
    return {"Authorization": f"Bearer {token}"}

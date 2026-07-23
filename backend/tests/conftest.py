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


def make_auth_header(token: str) -> dict[str, str]:
    """Build an Authorization header from a Bearer token string."""
    return {"Authorization": f"Bearer {token}"}

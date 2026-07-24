"""Common FastAPI dependencies — session, pagination, etc."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory


async def get_session() -> AsyncSession:
    """Provide an async database session for request handlers.

    Yields a session that is automatically closed when the handler returns.
    """
    async with async_session_factory() as session:
        yield session

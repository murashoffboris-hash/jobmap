"""Database engine, session, and base model — production-tuned pool."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.APP_ENV == "development",
    # ── Connection pool ─────────────────────────────────────────
    pool_size=10,             # steady-state connections per worker
    max_overflow=20,          # burst capacity (10 + 20 = 30 max)
    pool_pre_ping=True,       # detect stale connections before use
    pool_recycle=3600,        # recycle connections hourly (prevents leaks)
    pool_timeout=30,          # seconds to wait for a connection (fail fast)
    # ── asyncpg server settings ─────────────────────────────────
    connect_args={
        "server_settings": {
            "application_name": "jobmap-backend",
            "statement_timeout": "15000",  # 15 s — kill runaway queries
        },
    },
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base model with common audit fields."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    @classmethod
    async def get_by_id(cls, session: AsyncSession, record_id: int):
        return await session.get(cls, record_id)

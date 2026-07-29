"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.config import settings
from app.monitoring import setup_metrics
from app.routers.applications import (
    router as applications_router,
)
from app.routers.applications import (
    vacancy_applications_router,
)
from app.routers.auth import router as auth_router
from app.routers.geoservices import router as geo_router
from app.routers.health import router as health_router
from app.routers.vacancies import router as vacancies_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown hooks."""
    # Guard: refuse to start with a weak or missing JWT secret
    if not settings.JWT_SECRET or settings.JWT_SECRET == "CHANGE_ME":
        raise RuntimeError(
            "CRITICAL: JWT_SECRET is not set or is the insecure default ('CHANGE_ME'). "
            "Generate a strong secret (e.g. `openssl rand -hex 32`) and set it "
            "via the JWT_SECRET environment variable or .env file."
        )
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.SERVICE_NAME,
        version="0.1.0",
        lifespan=lifespan,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
    )

    # ── CORS ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Rate limiting ──
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    # ── Prometheus metrics ──
    setup_metrics(app)

    # ── Routers ──
    app.include_router(health_router)
    app.include_router(vacancies_router)
    app.include_router(geo_router)
    app.include_router(auth_router)
    app.include_router(applications_router)
    app.include_router(vacancy_applications_router)

    return app


app = create_app()

"""Application configuration — loads from .env / environment variables."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """All configurable values for the application."""

    # Service identity
    SERVICE_NAME: str = "JobMap"
    APP_ENV: str = "development"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "job_service"
    POSTGRES_USER: str = "job_service"
    POSTGRES_PASSWORD: str = ""

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def sync_database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Geoservices — primary (internal Docker / VPN) + public fallback
    NOMINATIM_URL: str = "http://nominatim:8080"
    NOMINATIM_FALLBACK_URL: str = "https://nominatim.openstreetmap.org"
    NOMINATIM_TIMEOUT: int = 5  # seconds for primary, before falling back
    NOMINATIM_USER_AGENT: str = "JobMap/1.0 (admin@service247.by)"

    OSRM_URL: str = "http://osrm:5000"
    OSRM_FALLBACK_URL: str = "https://router.project-osrm.org"
    OSRM_TIMEOUT: int = 5  # seconds for primary, before falling back

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # Auth
    JWT_SECRET: str = ""
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    BCRYPT_ROUNDS: int = 12

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # S3 storage
    S3_ENDPOINT: str = ""
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BUCKET_NAME: str = "job-service"

    model_config = {
        "env_file": str(Path(__file__).resolve().parents[2] / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()

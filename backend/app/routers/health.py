"""Health-check endpoint — no secrets, no stack traces."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/health")


class HealthResponse(BaseModel):
    status: str
    service: str
    dependencies: dict[str, str]


@router.get("", response_model=HealthResponse)
async def health_check():
    """Simple health probe."""
    deps: dict[str, str] = {}
    # TODO: add real dependency checks (PostgreSQL, Redis, Nominatim, OSRM)
    deps["postgresql"] = "pending"
    deps["redis"] = "pending"
    deps["nominatim"] = "pending"
    deps["osrm"] = "pending"

    return HealthResponse(
        status="ok",
        service="jobmap-backend",
        dependencies=deps,
    )

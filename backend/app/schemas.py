"""Schemas — Pydantic models for API request/response."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import UserRole, VacancyStatus, ResponseStatus


# ── Auth ──

class RegisterRequest(BaseModel):
    email: EmailStr = Field(..., example="user@example.com")
    password: str = Field(..., min_length=8, max_length=128, example="securePass123")

class LoginRequest(BaseModel):
    email: EmailStr = Field(..., example="employer@example.com")
    password: str = Field(..., example="securePass123")

class TokenResponse(BaseModel):
    access_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIs...")
    refresh_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIs...")
    token_type: str = Field(default="bearer", example="bearer")

class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., example="eyJhbGciOiJIUzI1NiIs...")

class UserResponse(BaseModel):
    id: int = Field(..., example=1)
    email: str = Field(..., example="user@example.com")
    full_name: str | None = Field(default=None, example="Иван Иванов")
    phone: str | None = Field(default=None, example="+375291234567")
    bio: str | None = Field(default=None, example="Опытный разработчик Python")
    avatar_url: str | None = Field(default=None, example="https://storage.example.com/avatars/1.jpg")
    role: UserRole = Field(..., example="user")
    is_active: bool = Field(..., example=True)

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255, example="Иван Иванов")
    phone: str | None = Field(default=None, max_length=32, example="+375291234567")
    bio: str | None = Field(default=None, max_length=1000, example="Люблю программировать")

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("full_name must not be empty")
        return value

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not all(char.isdigit() or char in "+() -" for char in value):
            raise ValueError("phone contains invalid characters")
        return value

    @field_validator("bio")
    @classmethod
    def normalize_bio(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value or None


# ── Vacancies ──

class VacancyCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=255, example="Python Backend Developer")
    description: Optional[str] = Field(default=None, example="Разработка и поддержка микросервисов на FastAPI")
    category_id: Optional[int] = Field(default=None, example=1)
    address: Optional[str] = Field(default=None, example="Минск, ул. Ленина, 10")
    salary_from: Optional[int] = Field(default=None, example=2500)
    salary_to: Optional[int] = Field(default=None, example=4000)
    salary_currency: str = Field(default="BYN", example="BYN")
    schedule_type: Optional[str] = Field(default=None, example="full-time")
    contact_phone: Optional[str] = Field(default=None, example="+375291234567")
    contact_name: Optional[str] = Field(default=None, example="Анна Петрова")
    exact_location_public: bool = Field(default=False, example=False)
    scheduled_publish_at: Optional[datetime] = None

class VacancyUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None
    address: Optional[str] = None
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    salary_currency: Optional[str] = None
    schedule_type: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_name: Optional[str] = None
    status: Optional[VacancyStatus] = None
    exact_location_public: Optional[bool] = None

class VacancyResponse(BaseModel):
    id: int = Field(..., example=42)
    title: str = Field(..., example="Python Backend Developer")
    description: Optional[str] = Field(default=None, example="Разработка микросервисов...")
    status: VacancyStatus = Field(..., example="active")
    address_normalized: Optional[str] = Field(default=None, example="Минск")
    location_lat: Optional[float] = Field(default=None, example=53.9000)
    location_lon: Optional[float] = Field(default=None, example=27.5667)
    geocode_status: str = Field(default="not_requested", example="success")
    salary_from: Optional[int] = Field(default=None, example=2500)
    salary_to: Optional[int] = Field(default=None, example=4000)
    salary_currency: str = Field(default="BYN", example="BYN")
    schedule_type: Optional[str] = Field(default=None, example="full-time")
    contact_phone: Optional[str] = Field(default=None, example="+375291234567")
    exact_location_public: bool = Field(default=False, example=False)
    created_at: datetime = Field(..., example="2026-07-28T12:00:00Z")

    model_config = {"from_attributes": True}


# ── Geospatial search ──

class VacancySearchRequest(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    radius_km: float = Field(gt=0, le=500, default=10.0)
    category_id: Optional[int] = None
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None

class VacancyGeoResult(BaseModel):
    id: int
    title: str
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    distance_m: Optional[float] = None
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None

    model_config = {"from_attributes": True}


# ── Vacancy list (paginated) ──

class VacancyListItem(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    salary_currency: str = Field("BYN", serialization_alias="currency")
    employment_type: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    employer_id: Optional[int] = None
    employer_name: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VacancyListResponse(BaseModel):
    items: list[VacancyListItem]
    total: int
    page_size: int
    next_cursor: str | None = None
    prev_cursor: str | None = None


# ── Route ──

class RouteRequest(BaseModel):
    origin_lat: float = Field(ge=-90, le=90)
    origin_lon: float = Field(ge=-180, le=180)
    dest_lat: float = Field(ge=-90, le=90)
    dest_lon: float = Field(ge=-180, le=180)
    profile: str = "car"

class RouteResponse(BaseModel):
    distance_m: Optional[float] = None
    duration_min: Optional[float] = None
    geometry: Optional[str] = None


# ── Geocoding ──

class GeocodeRequest(BaseModel):
    address: str = Field(..., min_length=2, max_length=512, example="Минск, ул. Ленина, 10")

class GeocodeResponse(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    osm_id: Optional[str] = None
    display_name: Optional[str] = None
    type: Optional[str] = None


# ── Applications (FR-007) ──

class ApplicationCreate(BaseModel):
    vacancy_id: int = Field(..., example=42)
    cover_letter: str | None = Field(default=None, max_length=2000, example="Я очень заинтересован в этой позиции...")


class ApplicationResponse(BaseModel):
    id: int = Field(..., example=100)
    user_id: int = Field(..., example=5)
    vacancy_id: int = Field(..., example=42)
    cover_letter: str | None = Field(default=None, example="Я очень заинтересован...")
    status: str = Field(..., example="pending")
    vacancy_title: str | None = Field(default=None, example="Python Backend Developer")
    employer_name: str | None = Field(default=None, example="ООО ТехноГрупп")
    applicant_name: str | None = Field(default=None, example="Иван Иванов")
    created_at: datetime = Field(..., example="2026-07-28T12:00:00Z")
    updated_at: datetime = Field(..., example="2026-07-28T12:00:00Z")

    model_config = {"from_attributes": True}


class ApplicationListResponse(BaseModel):
    items: list[ApplicationResponse]
    total: int
    page: int
    page_size: int

class ApplicationStatusUpdate(BaseModel):
    """Request body for PATCH /api/applications/{id}/status."""
    status: str = Field(..., example="accepted")  # "accepted" | "rejected"

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        allowed = {"accepted", "rejected"}
        if value.strip().lower() not in allowed:
            raise ValueError(
                f"Status must be one of: {', '.join(sorted(allowed))}"
            )
        return value.strip().lower()


class ResponseCreate(BaseModel):
    message: Optional[str] = None

class ResponseUpdate(BaseModel):
    status: ResponseStatus


# ── Cache metrics ─────────────────────────────────────────────────

class CacheStatsResponse(BaseModel):
    """Hit/miss counters for the vacancy list cache."""
    hits: int
    misses: int

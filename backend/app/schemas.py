"""Schemas — Pydantic models for API request/response."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.models import UserRole, VacancyStatus, ResponseStatus


# ── Auth ──

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str | None = None
    phone: str | None = None
    bio: str | None = None
    avatar_url: str | None = None
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=32)
    bio: str | None = Field(default=None, max_length=1000)

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
    title: str = Field(min_length=3, max_length=255)
    description: Optional[str] = None
    category_id: Optional[int] = None
    address: Optional[str] = None  # raw address for geocoding
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    salary_currency: str = "BYN"
    schedule_type: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_name: Optional[str] = None
    exact_location_public: bool = False
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
    id: int
    title: str
    description: Optional[str] = None
    status: VacancyStatus
    address_normalized: Optional[str] = None
    location_lat: Optional[float] = None
    location_lon: Optional[float] = None
    geocode_status: str = "not_requested"  # "success", "failed", "not_requested"
    salary_from: Optional[int] = None
    salary_to: Optional[int] = None
    salary_currency: str
    schedule_type: Optional[str] = None
    contact_phone: Optional[str] = None
    exact_location_public: bool
    created_at: datetime

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
    page: int
    page_size: int


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
    address: str = Field(min_length=2, max_length=512)

class GeocodeResponse(BaseModel):
    lat: Optional[float] = None
    lon: Optional[float] = None
    osm_id: Optional[str] = None
    display_name: Optional[str] = None
    type: Optional[str] = None


# ── Responses ──

class ResponseCreate(BaseModel):
    message: Optional[str] = None

class ResponseUpdate(BaseModel):
    status: ResponseStatus

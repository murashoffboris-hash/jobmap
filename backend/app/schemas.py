"""Schemas — Pydantic models for API request/response."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field

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
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}


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

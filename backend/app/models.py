"""SQLAlchemy models — all MVP entities."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from geoalchemy2 import Geography
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

# ── Enums ──

class UserRole(str, Enum):
    USER = "user"
    EMPLOYER = "employer"
    ADMIN = "admin"
    MODERATOR = "moderator"


class VacancyStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    FILLED = "filled"
    EXPIRED = "expired"
    ARCHIVED = "archived"


class ResponseStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class NotificationType(str, Enum):
    NEW_RESPONSE = "new_response"
    RESPONSE_STATUS = "response_status"
    NEW_MESSAGE = "new_message"
    VACANCY_EXPIRED = "vacancy_expired"
    SYSTEM = "system"


# ── Models ──

class User(Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, values_callable=lambda obj: [e.value for e in obj]),
        default=UserRole.USER,
        server_default="user",
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    profile = relationship("Profile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    vacancies = relationship("Vacancy", back_populates="owner", cascade="all, delete-orphan")
    responses_sent = relationship("Response", foreign_keys="Response.requester_id", back_populates="requester")


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(32))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    bio: Mapped[str | None] = mapped_column(Text)
    # Точка поиска пользователя — для уведомлений
    search_lat: Mapped[float | None] = mapped_column(Float)
    search_lon: Mapped[float | None] = mapped_column(Float)
    search_radius_km: Mapped[float] = mapped_column(Float, default=10.0, server_default="10.0")

    user = relationship("User", back_populates="profile")


class Category(Base):
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    icon: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    children = relationship("Category", backref="parent", remote_side="Category.id")
    vacancies = relationship("Vacancy", back_populates="category")


class Vacancy(Base):
    __tablename__ = "vacancies"

    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[VacancyStatus] = mapped_column(
        SAEnum(VacancyStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=VacancyStatus.ACTIVE,
        server_default="active",
        index=True,
    )

    # Location — PostGIS geography point
    location = Column(Geography("POINT", srid=4326), nullable=True, index=True)
    location_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    location_lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Address details (stored for display and re-geocoding)
    address_raw: Mapped[str | None] = mapped_column(String(512))
    address_normalized: Mapped[str | None] = mapped_column(String(512))
    osm_id: Mapped[str | None] = mapped_column(String(64))
    location_type: Mapped[str | None] = mapped_column(String(64))
    location_accuracy: Mapped[float | None] = mapped_column(Float)

    # Salary
    salary_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[str] = mapped_column(String(8), default="BYN", server_default="BYN")

    # Scheduling
    schedule_type: Mapped[str | None] = mapped_column(String(64))  # full-time, part-time, one-time
    contact_phone: Mapped[str | None] = mapped_column(String(32))
    contact_name: Mapped[str | None] = mapped_column(String(128))

    # Visibility
    exact_location_public: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    # Delayed publishing (free tier)
    scheduled_publish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="vacancies")
    category = relationship("Category", back_populates="vacancies")
    media = relationship("VacancyMedia", back_populates="vacancy", cascade="all, delete-orphan")
    vacancy_responses = relationship("Response", foreign_keys="Response.vacancy_id", back_populates="vacancy")

    __table_args__ = (
        # Spatial index is created via Geography column index
    )


class VacancyMedia(Base):
    """Фотографии и видео вакансий — хранятся в S3, здесь только ссылки."""
    __tablename__ = "vacancy_media"

    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), index=True)
    media_type: Mapped[str] = mapped_column(String(16))  # image, video
    file_url: Mapped[str] = mapped_column(String(512), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(512))
    s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    vacancy = relationship("Vacancy", back_populates="media")


class Application(Base):
    """Отклик соискателя на вакансию — FR-007."""
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("user_id", "vacancy_id", name="uq_application_user_vacancy"),)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), index=True)
    cover_letter: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ApplicationStatus] = mapped_column(
        SAEnum(ApplicationStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ApplicationStatus.PENDING,
        server_default="pending",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, server_default="now()"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, server_default="now()"
    )

    user = relationship("User", foreign_keys=[user_id], backref="applications")
    vacancy = relationship("Vacancy", foreign_keys=[vacancy_id], backref="applications")


class Response(Base):
    __tablename__ = "responses"
    __table_args__ = (UniqueConstraint("vacancy_id", "requester_id", name="uq_response_vacancy_user"),)

    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"), index=True)
    requester_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[ResponseStatus] = mapped_column(
        SAEnum(ResponseStatus), default=ResponseStatus.PENDING, server_default="pending"
    )
    message: Mapped[str | None] = mapped_column(Text)

    vacancy = relationship("Vacancy", foreign_keys=[vacancy_id], back_populates="vacancy_responses")
    requester = relationship("User", foreign_keys=[requester_id], back_populates="responses_sent")


class Chat(Base):
    """Чат между двумя участниками по отклику."""
    __tablename__ = "chats"

    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"))
    user_one_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    user_two_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    chat_id: Mapped[int] = mapped_column(ForeignKey("chats.id", ondelete="CASCADE"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    text: Mapped[str | None] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User")


class WorkStatusEvent(Base):
    """Автозавершение работы через 24 часа — трекинг статуса."""
    __tablename__ = "work_status_events"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancies.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64))  # started, completed, cancelled
    notes: Mapped[str | None] = mapped_column(Text)


class Review(Base):
    __tablename__ = "reviews"

    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reviewed_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancies.id"), nullable=True)
    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    reviewer = relationship("User", foreign_keys=[reviewer_id])
    reviewed_user = relationship("User", foreign_keys=[reviewed_user_id])


class Subscription(Base):
    __tablename__ = "subscriptions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    location_lat: Mapped[float | None] = mapped_column(Float)
    location_lon: Mapped[float | None] = mapped_column(Float)
    radius_km: Mapped[float] = mapped_column(Float, default=10.0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Promotion(Base):
    __tablename__ = "promotions"

    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancies.id", ondelete="CASCADE"))
    promo_type: Mapped[str] = mapped_column(String(64))  # featured, highlight, urgent
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")


class Notification(Base):
    __tablename__ = "notifications"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    notification_type: Mapped[NotificationType] = mapped_column(SAEnum(NotificationType))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    payload: Mapped[dict | None] = mapped_column(JSONB)


class GeocodingLog(Base):
    """Журнал геокодирования — аудит и кеширование."""
    __tablename__ = "geocoding_log"

    address_raw: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    address_normalized: Mapped[str | None] = mapped_column(String(512))
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    osm_id: Mapped[str | None] = mapped_column(String(64))
    result_type: Mapped[str | None] = mapped_column(String(64))
    accuracy: Mapped[float | None] = mapped_column(Float)
    raw_response: Mapped[dict | None] = mapped_column(JSONB)
    success: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancies.id"), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512))

    __table_args__ = (
        UniqueConstraint("address_raw", "vacancy_id", name="uq_geocode_addr_vacancy"),
    )


class AuditLog(Base):
    """Лог административных действий."""
    __tablename__ = "audit_log"

    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64))  # vacancy, user, etc.
    target_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    details: Mapped[dict | None] = mapped_column(JSONB)
    ip_address: Mapped[str | None] = mapped_column(String(64))

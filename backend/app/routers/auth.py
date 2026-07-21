"""Auth API — registration, login, profile management (skeleton)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models import User, Profile
from app.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_session():
    return async_session_factory


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest, session: AsyncSession = Depends(get_session)):
    """Register a new user."""
    # Check if email already exists
    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=pwd_context.hash(data.password),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest, session: AsyncSession = Depends(get_session)):
    """Login and get JWT token."""
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # TODO: implement JWT token generation
    return TokenResponse(access_token="TODO_implement_jwt", token_type="bearer")


@router.get("/me", response_model=UserResponse)
async def get_current_user(session: AsyncSession = Depends(get_session)):
    """Get current user profile."""
    # TODO: implement JWT auth dependency
    return UserResponse(id=0, email="placeholder", role="user", is_active=True)

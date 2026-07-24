"""JWT token creation, decoding, and dependency injection.

Uses HS256 via python-jose (PyJWT wrapper). Secret and expiry
are configured in app.config.Settings.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session_factory
from app.models import User

security_scheme = HTTPBearer()


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed HS256 JWT access token.

    Args:
        data: Claims to embed (must include 'sub' as int or str).
        expires_delta: Token lifetime override (default from config).

    Returns:
        Encoded JWT string.
    """
    to_encode = data.copy()
    # python-jose requires 'sub' to be a string
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a longer-lived refresh token."""
    to_encode = data.copy()
    if "sub" in to_encode:
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
    )
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and verify a JWT token.

    Raises:
        HTTPException(401): If token is invalid or expired.

    Returns:
        Decoded payload dict.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=["HS256"]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> User:
    """FastAPI dependency: extract and return the current authenticated user.

    Reads the Bearer token from the Authorization header, decodes it,
    and loads the matching User from the database.

    Raises:
        HTTPException(401): If token missing, invalid, or user not found.
    """
    payload = decode_token(credentials.credentials)
    user_id_str: str | None = payload.get("sub")
    if user_id_str is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    user_id = int(user_id_str)

    async with async_session_factory() as session:
        user = await session.get(User, user_id)
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
            )
        return user


async def get_current_employer(
    current_user: User = Depends(get_current_user),
) -> User:
    """FastAPI dependency: require the authenticated user to have employer role."""
    if current_user.role.value not in ("employer", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Employer or admin role required",
        )
    return current_user

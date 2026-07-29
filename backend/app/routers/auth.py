"""Auth API — registration, login, token refresh, profile."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_session
from app.models import Profile, User
from app.schemas import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UpdateProfileRequest,
    UserResponse,
)
from app.services.auth import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)
from app.services.security import hash_password, verify_password
from app.services.storage import (
    delete_avatar,
    ensure_bucket_exists,
    get_avatar_presigned_url,
    upload_avatar,
    validate_avatar,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

login_limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=201,
    summary="Register new user",
    description="Create a new user account with email and password. An empty profile is automatically created.",
)
async def register(data: RegisterRequest, session: AsyncSession = Depends(get_session)):
    # Check if email already exists
    result = await session.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    session.add(user)
    await session.flush()  # get user.id

    # Create empty profile
    profile = Profile(user_id=user.id)
    session.add(profile)

    await session.commit()
    await session.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login",
    description="Authenticate with email and password. Returns access + refresh JWT tokens. Rate-limited: 5 requests/minute per IP.",
)
@login_limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": user.id})
    refresh_token = create_refresh_token(data={"sub": user.id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
    description="Exchange a valid refresh token for a new access + refresh token pair.",
)
async def refresh(data: RefreshRequest):
    payload = decode_token(data.refresh_token)

    # Ensure this is a refresh-type token
    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    user_id: int = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    access_token = create_access_token(data={"sub": user_id})
    refresh_token = create_refresh_token(data={"sub": user_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
    description="Return the authenticated user's profile including avatar, full name, phone, and bio.",
)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.profile.full_name if current_user.profile else None,
        phone=current_user.profile.phone if current_user.profile else None,
        bio=current_user.profile.bio if current_user.profile else None,
        avatar_url=current_user.profile.avatar_url if current_user.profile else None,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user profile",
    description="Update the authenticated user's editable fields: full_name, phone, bio.",
)
async def update_me(
    data: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile_result = await session.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=current_user.id)
        session.add(profile)

    profile.full_name = data.full_name
    profile.phone = data.phone
    profile.bio = data.bio
    await session.commit()
    await session.refresh(profile)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        bio=profile.bio,
        avatar_url=profile.avatar_url,
        role=current_user.role,
        is_active=current_user.is_active,
    )


# ── Avatar endpoints ──


@router.post(
    "/me/avatar",
    response_model=UserResponse,
    summary="Upload avatar",
    description="Upload a profile avatar image (JPEG, PNG, WebP; max 5 MB). Content is validated by magic bytes, not file extension.",
)
async def upload_me_avatar(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Read file content
    content = await file.read()

    # Validate content
    try:
        content_type = validate_avatar(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Determine extension from detected MIME type
    ext_map = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
    ext = ext_map[content_type]

    # Ensure bucket exists
    await ensure_bucket_exists()

    # Upload to MinIO
    key = await upload_avatar(current_user.id, content, ext)

    # Update profile
    profile_result = await session.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()
    if profile is None:
        profile = Profile(user_id=current_user.id)
        session.add(profile)
        await session.flush()

    profile.avatar_url = key
    await session.commit()
    await session.refresh(profile)

    presigned = await get_avatar_presigned_url(key)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        bio=profile.bio,
        avatar_url=presigned or key,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.get(
    "/me/avatar",
    summary="Get avatar redirect",
    description="Redirect to a presigned URL for the current user's avatar. Returns 404 if no avatar set.",
)
async def get_me_avatar(
    current_user: User = Depends(get_current_user),
):
    if not current_user.profile or not current_user.profile.avatar_url:
        raise HTTPException(status_code=404, detail="No avatar set")

    presigned = await get_avatar_presigned_url(current_user.profile.avatar_url)
    if not presigned:
        raise HTTPException(status_code=404, detail="Avatar file not found")

    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=presigned, status_code=307)


@router.delete(
    "/me/avatar",
    response_model=UserResponse,
    summary="Delete avatar",
    description="Delete the current user's avatar from storage and clear the avatar_url field.",
)
async def delete_me_avatar(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    profile_result = await session.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
    profile = profile_result.scalar_one_or_none()

    if profile and profile.avatar_url:
        await delete_avatar(profile.avatar_url)
        profile.avatar_url = None
        await session.commit()
        await session.refresh(profile)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=profile.full_name if profile else None,
        phone=profile.phone if profile else None,
        bio=profile.bio if profile else None,
        avatar_url=None,
        role=current_user.role,
        is_active=current_user.is_active,
    )

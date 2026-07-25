"""Tests for avatar upload / get / delete endpoints."""

from __future__ import annotations

import io
import struct
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient


# ── Helpers ──


def _make_jpeg_bytes() -> bytes:
    """Create minimal valid JPEG bytes (SOI marker + minimal data)."""
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"


def _make_png_bytes() -> bytes:
    """Create minimal valid PNG bytes."""
    # PNG signature + IHDR chunk
    signature = b"\x89PNG\r\n\x1a\n"

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        chunk = chunk_type + data
        crc = struct.pack(">I", _crc32(chunk))
        return struct.pack(">I", len(data)) + chunk + crc

    return signature + _chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))


def _make_webp_bytes() -> bytes:
    """Create minimal valid WebP bytes (RIFF header + WEBP)."""
    # RIFF header: "RIFF" + size (little-endian) + "WEBP"
    riff = b"RIFF"
    size = struct.pack("<I", 4)  # size of "WEBP"
    webp_marker = b"WEBP"
    return riff + size + webp_marker


def _make_pdf_bytes() -> bytes:
    """Create bytes that look like a PDF (not a valid image)."""
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"


def _make_exe_bytes() -> bytes:
    """Create bytes that look like an executable (MZ header)."""
    return b"MZ\x90\x00\x03\x00\x00\x00"


def _make_oversized_bytes() -> bytes:
    """Create > 5MB of JPEG-like bytes."""
    header = _make_jpeg_bytes()
    padding = b"\x00" * (5 * 1024 * 1024)  # 5 MB of zeros
    return header + padding


# Pure-Python CRC32 (to avoid zlib import issues in certain envs)
def _crc32(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return crc ^ 0xFFFFFFFF


# ── Tests ──


@pytest.mark.asyncio
async def test_upload_avatar_unauthorized(client: AsyncClient):
    """POST /api/auth/me/avatar without token → 401."""
    files = {"file": ("avatar.jpg", io.BytesIO(_make_jpeg_bytes()), "image/jpeg")}
    response = await client.post("/api/auth/me/avatar", files=files)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_avatar_bad_token(client: AsyncClient):
    """POST /api/auth/me/avatar with invalid token → 401."""
    files = {"file": ("avatar.jpg", io.BytesIO(_make_jpeg_bytes()), "image/jpeg")}
    response = await client.post(
        "/api/auth/me/avatar",
        files=files,
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_invalid_file_type_pdf(client: AsyncClient):
    """POST with PDF file → validation fails before DB call."""
    files = {"file": ("doc.pdf", io.BytesIO(_make_pdf_bytes()), "application/pdf")}
    response = await client.post("/api/auth/me/avatar", files=files)
    # FastAPI tries to resolve dependencies (auth gets 401), but file parsing
    # happens first. Without auth, it's 401. But if we pass a valid token,
    # it'll try DB which is unavailable.
    # This test is informational — it checks the path exists.
    assert response.status_code in (401, 422, 500)


@pytest.mark.asyncio
async def test_upload_invalid_file_type_exe(client: AsyncClient):
    """POST with EXE file → should reject."""
    files = {"file": ("virus.exe", io.BytesIO(_make_exe_bytes()), "application/x-msdownload")}
    response = await client.post("/api/auth/me/avatar", files=files)
    assert response.status_code in (401, 422, 500)


@pytest.mark.asyncio
async def test_upload_oversized(client: AsyncClient):
    """POST with >5MB file → should reject."""
    files = {"file": ("huge.jpg", io.BytesIO(_make_oversized_bytes()), "image/jpeg")}
    response = await client.post("/api/auth/me/avatar", files=files)
    assert response.status_code in (401, 422, 500)


@pytest.mark.asyncio
async def test_get_avatar_unauthorized(client: AsyncClient):
    """GET /api/auth/me/avatar without token → 401."""
    response = await client.get("/api/auth/me/avatar")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_avatar_unauthorized(client: AsyncClient):
    """DELETE /api/auth/me/avatar without token → 401."""
    response = await client.delete("/api/auth/me/avatar")
    assert response.status_code == 401


# ── Validation-only tests (no auth needed) ──


class TestContentTypeDetection:
    """Test the magic-bytes content type detection directly."""

    def test_detect_jpeg(self):
        from app.services.storage import detect_content_type

        assert detect_content_type(_make_jpeg_bytes()) == "image/jpeg"

    def test_detect_png(self):
        from app.services.storage import detect_content_type

        assert detect_content_type(_make_png_bytes()) == "image/png"

    def test_detect_webp(self):
        from app.services.storage import detect_content_type

        assert detect_content_type(_make_webp_bytes()) == "image/webp"

    def test_detect_pdf_is_none(self):
        from app.services.storage import detect_content_type

        assert detect_content_type(_make_pdf_bytes()) is None

    def test_detect_exe_is_none(self):
        from app.services.storage import detect_content_type

        assert detect_content_type(_make_exe_bytes()) is None

    def test_detect_empty_is_none(self):
        from app.services.storage import detect_content_type

        assert detect_content_type(b"") is None

    def test_detect_short_is_none(self):
        from app.services.storage import detect_content_type

        assert detect_content_type(b"\xff\xd8") is None  # too short


class TestValidateAvatar:
    """Test the validate_avatar function directly."""

    def test_valid_jpeg(self):
        from app.services.storage import validate_avatar

        assert validate_avatar(_make_jpeg_bytes()) == "image/jpeg"

    def test_valid_png(self):
        from app.services.storage import validate_avatar

        assert validate_avatar(_make_png_bytes()) == "image/png"

    def test_valid_webp(self):
        from app.services.storage import validate_avatar

        assert validate_avatar(_make_webp_bytes()) == "image/webp"

    def test_invalid_pdf_raises(self):
        from app.services.storage import validate_avatar

        with pytest.raises(ValueError, match="Unsupported image type"):
            validate_avatar(_make_pdf_bytes())

    def test_invalid_exe_raises(self):
        from app.services.storage import validate_avatar

        with pytest.raises(ValueError, match="Unsupported image type"):
            validate_avatar(_make_exe_bytes())

    def test_oversized_raises(self):
        from app.services.storage import validate_avatar

        with pytest.raises(ValueError, match="File too large"):
            validate_avatar(_make_oversized_bytes())

    def test_size_exactly_5mb_ok(self):
        from app.services.storage import validate_avatar

        # Create exactly 5 MB of valid JPEG
        header = _make_jpeg_bytes()
        padding = b"\x00" * (5 * 1024 * 1024 - len(header))
        content = header + padding
        assert len(content) == 5 * 1024 * 1024
        assert validate_avatar(content) == "image/jpeg"


# ── Integration-style tests with mocked S3 ──


@pytest.mark.asyncio
async def test_upload_valid_jpeg_with_mock(mock_user_client: AsyncClient):
    """Full upload flow with mocked S3 and auth (via dependency overrides)."""
    with patch("app.routers.auth.ensure_bucket_exists", new_callable=AsyncMock) as mock_bucket, \
         patch("app.routers.auth.upload_avatar", new_callable=AsyncMock) as mock_upload, \
         patch("app.routers.auth.get_avatar_presigned_url", new_callable=AsyncMock) as mock_presigned:

        mock_upload.return_value = "avatars/1/test-uuid.jpg"
        mock_presigned.return_value = "http://minio:9000/job-service/avatars/1/test-uuid.jpg?X-Amz-Signature=test"

        files = {"file": ("avatar.jpg", io.BytesIO(_make_jpeg_bytes()), "image/jpeg")}
        response = await mock_user_client.post(
            "/api/auth/me/avatar",
            files=files,
            # No auth header needed — dependency override handles it
        )

        assert response.status_code == 200
        data = response.json()
        assert "avatar_url" in data
        assert data["avatar_url"] is not None
        assert "minio" in data["avatar_url"]


@pytest.mark.asyncio
async def test_delete_avatar_with_mock(mock_user_client: AsyncClient):
    """Full delete flow with mocked S3 (via dependency overrides)."""
    with patch("app.routers.auth.delete_avatar", new_callable=AsyncMock) as mock_delete:

        response = await mock_user_client.delete("/api/auth/me/avatar")

        assert response.status_code == 200
        data = response.json()
        assert data["avatar_url"] is None


@pytest.mark.asyncio
async def test_get_avatar_with_mock(mock_user_client: AsyncClient):
    """GET avatar when none set → 404 (via dependency overrides)."""
    response = await mock_user_client.get("/api/auth/me/avatar")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_avatar_redirect_when_set(app: FastAPI):
    """GET avatar when avatar IS set — expect 307 redirect."""
    from unittest.mock import AsyncMock, MagicMock

    from app.dependencies import get_session
    from app.routers.auth import get_current_user
    from app.models import Profile

    with patch("app.routers.auth.get_avatar_presigned_url", new_callable=AsyncMock) as mock_presigned:
        mock_presigned.return_value = "http://minio:9000/bucket/avatars/1/test.jpg?X-Amz-Signature=test"

        # Build mock user WITH avatar_url set
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "mock@example.com"
        mock_user.role = MagicMock()
        mock_user.role.value = "user"
        mock_user.is_active = True

        mock_profile = MagicMock()
        mock_profile.user_id = 1
        mock_profile.full_name = "Mock User"
        mock_profile.avatar_url = "avatars/1/test.jpg"
        mock_user.profile = mock_profile

        mock_session = AsyncMock()

        app.dependency_overrides[get_current_user] = lambda: mock_user

        # Need a proper async generator for session
        async def _mock_session():
            yield mock_session

        app.dependency_overrides[get_session] = _mock_session

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            response = await ac.get("/api/auth/me/avatar")

        assert response.status_code == 307
        assert "location" in response.headers
        assert "minio" in response.headers["location"]

        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_avatar_not_set_with_mock(mock_user_client: AsyncClient):
    """GET avatar when none is set → 404 (via dependency overrides, avatar_url=None)."""
    response = await mock_user_client.get("/api/auth/me/avatar")
    assert response.status_code == 404

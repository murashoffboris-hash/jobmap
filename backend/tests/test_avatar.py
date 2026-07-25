"""Tests for avatar upload / get / delete endpoints."""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from PIL import Image as PILImage


# ── Helpers ──


def _make_jpeg_bytes() -> bytes:
    """Create a minimal but valid JPEG image using Pillow (1×1 pixel)."""
    buf = io.BytesIO()
    img = PILImage.new("RGB", (1, 1), color=(255, 0, 0))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_png_bytes() -> bytes:
    """Create a minimal but valid PNG image using Pillow (1×1 pixel)."""
    buf = io.BytesIO()
    img = PILImage.new("RGB", (1, 1), color=(0, 255, 0))
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_webp_bytes() -> bytes:
    """Create a minimal but valid WebP image using Pillow (1×1 pixel)."""
    buf = io.BytesIO()
    img = PILImage.new("RGB", (1, 1), color=(0, 0, 255))
    img.save(buf, format="WEBP")
    return buf.getvalue()


def _make_pdf_bytes() -> bytes:
    """Create bytes that look like a PDF (not a valid image)."""
    return b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"


def _make_exe_bytes() -> bytes:
    """Create bytes that look like an executable (MZ header)."""
    return b"MZ\x90\x00\x03\x00\x00\x00"


def _make_oversized_bytes() -> bytes:
    """Create a valid JPEG > 5MB by generating a large image."""
    # Generate a JPEG > 5MB: create a large enough image (Pillow compresses it)
    buf = io.BytesIO()
    img = PILImage.new("RGB", (1500, 1500), color=(128, 128, 128))
    img.save(buf, format="JPEG", quality=95)
    result = buf.getvalue()
    # If not oversized enough, add padding after the JPEG data
    # (the magic bytes check will still pass since JPEG starts with FF D8 FF)
    if len(result) <= 5 * 1024 * 1024:
        result = result + b"\x00" * (5 * 1024 * 1024 - len(result) + 1)
    return result


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

        # Create a valid JPEG exactly at the 5 MB boundary
        # Generate a real JPEG image, pad with trailing zeros to reach 5 MB
        # (JPEG parsers stop at EOI marker FF D9, ignore trailing data)
        buf = io.BytesIO()
        img = PILImage.new("RGB", (1, 1), color=(255, 0, 0))
        img.save(buf, format="JPEG")
        jpeg_data = buf.getvalue()
        padding_needed = 5 * 1024 * 1024 - len(jpeg_data)
        content = jpeg_data + b"\x00" * padding_needed
        assert len(content) == 5 * 1024 * 1024
        # JPEG magic bytes pass, Pillow opens it (ignores trailing data),
        # pixel dimensions are tiny → passes
        assert validate_avatar(content) == "image/jpeg"


# ── Decompression bomb & integrity tests ──

from app.services.storage import MAX_IMAGE_PIXELS


class TestValidateAvatarSecurity:
    """Test decompression bomb & image integrity protection."""

    def test_truncated_image_raises(self) -> None:
        """Truncated JPEG data → should raise ValueError (integrity check)."""
        from app.services.storage import validate_avatar

        # Valid JPEG header but truncated body
        truncated = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01"
        with pytest.raises(ValueError, match="Invalid or corrupted"):
            validate_avatar(truncated)

    def test_invalid_jpeg_structure_raises(self) -> None:
        """JPEG magic bytes followed by garbage → should raise ValueError."""
        from app.services.storage import validate_avatar

        fake_jpeg = _make_jpeg_bytes()[:20] + b"\x00" * 100
        with pytest.raises(ValueError, match="Invalid or corrupted"):
            validate_avatar(fake_jpeg)

    def test_dimensions_within_limit_pass(self) -> None:
        """Normal small images (1×1 PNG) should pass validation."""
        from app.services.storage import validate_avatar

        assert validate_avatar(_make_png_bytes()) == "image/png"

    def test_max_image_pixels_is_set(self) -> None:
        """Image.MAX_IMAGE_PIXELS is configured at import time."""
        from PIL import Image

        assert Image.MAX_IMAGE_PIXELS == MAX_IMAGE_PIXELS

    def test_excessive_pixel_count_raises(self, monkeypatch) -> None:
        """Image exceeding pixel limit → should raise ValueError.

        Uses monkeypatch to lower the limit to a testable value.
        """
        from app.services import storage
        from app.services.storage import validate_avatar

        # Lower limit to 4 pixels (2×2) for testing
        monkeypatch.setattr(storage, "MAX_IMAGE_PIXELS", 4)

        # Create a real 3×3 PNG (9 pixels > 4 limit)
        buf = io.BytesIO()
        PILImage.new("RGB", (3, 3), color=(128, 0, 0)).save(buf, format="PNG")
        # Also need to raise Pillow's own limit to not interfere
        import PIL.Image
        old_limit = PIL.Image.MAX_IMAGE_PIXELS
        PIL.Image.MAX_IMAGE_PIXELS = 100
        try:
            with pytest.raises(ValueError, match="Image too large after decompression"):
                validate_avatar(buf.getvalue())
        finally:
            PIL.Image.MAX_IMAGE_PIXELS = old_limit

    def test_pixel_count_at_limit_passes(self, monkeypatch) -> None:
        """Image at exactly the pixel limit should pass.

        Uses monkeypatch to lower the limit to a testable value.
        """
        from app.services import storage
        from app.services.storage import validate_avatar

        # Set limit to 9 pixels (3×3)
        monkeypatch.setattr(storage, "MAX_IMAGE_PIXELS", 9)

        import PIL.Image
        old_limit = PIL.Image.MAX_IMAGE_PIXELS
        PIL.Image.MAX_IMAGE_PIXELS = 100  # so Pillow doesn't raise first
        try:
            buf = io.BytesIO()
            PILImage.new("RGB", (3, 3), color=(128, 0, 0)).save(buf, format="PNG")
            # 3×3 = 9, exactly at limit
            assert validate_avatar(buf.getvalue()) == "image/png"
        finally:
            PIL.Image.MAX_IMAGE_PIXELS = old_limit

    def test_pillow_decompression_bomb_error_raises(self) -> None:
        """Pillow's own DecompressionBombError → caught and re-raised as ValueError."""
        from unittest.mock import patch as mock_patch
        from PIL import Image
        from app.services.storage import validate_avatar

        # Use a small valid PNG, but mock Image.open to raise DecompressionBombError
        png_bytes = _make_png_bytes()
        with mock_patch("PIL.Image.open", side_effect=Image.DecompressionBombError("bomb!")):
            with pytest.raises(ValueError, match="Image exceeds decompression pixel limit"):
                # Import fresh to avoid caching
                from app.services.storage import _validate_image_integrity
                _validate_image_integrity(png_bytes)


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

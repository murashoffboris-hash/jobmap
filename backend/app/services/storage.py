"""MinIO / S3 storage service — upload, presigned URLs, delete.

Uses boto3 with S3-compatible MinIO endpoint from app.config.
"""

from __future__ import annotations

import uuid
from io import BytesIO

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError
from PIL import Image

from app.config import settings

ALLOWED_IMAGE_TYPES: frozenset[str] = frozenset(
    {"image/jpeg", "image/png", "image/webp"}
)
MAX_AVATAR_SIZE: int = 5 * 1024 * 1024  # 5 MB

# ── Decompression bomb protection ──
# Pillow will raise DecompressionBombError if an image exceeds this many pixels
# during decompression. 50M pixels ≈ 7071×7071 — more than enough for an avatar.
MAX_IMAGE_PIXELS: int = 50_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# ── Magic bytes for image type detection ──
_MAGIC_SIGNATURES: dict[bytes, str] = {
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
    b"RIFF": "image/webp",  # RIFF....WEBP
}


def detect_content_type(content: bytes) -> str | None:
    """Detect image MIME type from magic bytes (first 12 bytes of file).

    Returns the MIME type string or None if not a recognized image format.
    """
    if len(content) < 12:
        return None

    # JPEG — starts with FF D8 FF
    if content[:3] == b"\xff\xd8\xff":
        return "image/jpeg"

    # PNG — starts with 89 50 4E 47 0D 0A 1A 0A
    if content[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"

    # WebP — RIFF header + WEBP at offset 8
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"

    return None


def validate_avatar(content: bytes, *, max_size: int = MAX_AVATAR_SIZE) -> str:
    """Validate avatar image content and return the detected MIME type.

    Args:
        content: Raw file bytes.
        max_size: Maximum allowed size in bytes.

    Returns:
        Detected MIME type string (e.g. 'image/jpeg').

    Raises:
        ValueError: If content exceeds max_size, is not a recognized image,
            or fails decompression bomb / integrity checks.
    """
    if len(content) > max_size:
        raise ValueError(
            f"File too large: {len(content)} bytes (max {max_size})"
        )

    content_type = detect_content_type(content)
    if content_type is None or content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(
            f"Unsupported image type. Allowed: {', '.join(sorted(ALLOWED_IMAGE_TYPES))}"
        )

    # ── Decompression bomb & integrity protection ──
    _validate_image_integrity(content)

    return content_type


def _validate_image_integrity(content: bytes) -> None:
    """Validate that the image is not a decompression bomb and has a valid structure.

    Uses Pillow to:
      1. Verify the image file structure (header integrity, truncated files).
      2. Check that decompressed pixel count is within safe bounds.

    Raises:
        ValueError: If the image is corrupted, truncated, or exceeds pixel limits.
    """
    try:
        # Open the image (lazy — only parses headers, no full decompression)
        img = Image.open(BytesIO(content))

        # Check dimensions from the header BEFORE verify() (which invalidates
        # the image object). This catches decompression bombs where the header
        # claims a reasonable size but verify() would later decompress to
        # something huge — Pillow's MAX_IMAGE_PIXELS handles that case.
        pixel_count = img.width * img.height
        if pixel_count > MAX_IMAGE_PIXELS:
            raise ValueError(
                f"Image too large after decompression: {pixel_count} pixels "
                f"(max {MAX_IMAGE_PIXELS})"
            )

        # verify() checks file structure integrity (corrupted headers,
        # truncated streams, etc.) without full pixel data decompression
        img.verify()

    except ValueError:
        # Re-raise our own ValueError (pixel count exceeded)
        raise
    except Image.DecompressionBombError as exc:
        raise ValueError(
            f"Image exceeds decompression pixel limit ({MAX_IMAGE_PIXELS}): {exc}"
        )
    except Exception as exc:
        # Any Pillow error (corrupt, truncated, unidentified format, etc.)
        raise ValueError(f"Invalid or corrupted image: {exc}")


def _get_s3_client():
    """Create and return a boto3 S3 client configured for MinIO."""
    endpoint_url = settings.S3_ENDPOINT or "http://minio:9000"
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
        config=BotoConfig(signature_version="s3v4"),
        region_name="us-east-1",
    )


def _get_bucket_name() -> str:
    return settings.S3_BUCKET_NAME or "job-service"


async def ensure_bucket_exists() -> None:
    """Create the avatars bucket if it does not already exist."""
    client = _get_s3_client()
    bucket = _get_bucket_name()
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "404":
            client.create_bucket(Bucket=bucket)
        else:
            raise


async def upload_avatar(user_id: int, content: bytes, ext: str) -> str:
    """Upload avatar image to MinIO, return the object key.

    Args:
        user_id: The owning user's database ID.
        content: Raw image bytes (already validated).
        ext: File extension without dot (e.g. 'jpg', 'png', 'webp').

    Returns:
        The S3 object key, e.g. 'avatars/42/a1b2c3d4.jpg'.
    """
    key = f"avatars/{user_id}/{uuid.uuid4()}.{ext}"
    client = _get_s3_client()
    bucket = _get_bucket_name()

    content_type = detect_content_type(content) or "application/octet-stream"
    client.put_object(
        Bucket=bucket,
        Key=key,
        Body=BytesIO(content),
        ContentType=content_type,
        ContentLength=len(content),
    )
    return key


async def delete_avatar(key: str) -> None:
    """Delete an avatar object from S3.

    Does nothing if the key is empty or the object does not exist.
    """
    if not key:
        return
    client = _get_s3_client()
    bucket = _get_bucket_name()
    try:
        client.delete_object(Bucket=bucket, Key=key)
    except ClientError:
        # Object already gone — that's fine
        pass


async def get_presigned_url(key: str, *, expires: int = 300) -> str | None:
    """Generate a presigned GET URL for an S3 object.

    Args:
        key: The S3 object key.
        expires: URL lifetime in seconds (default 5 min).

    Returns:
        Presigned URL string, or None if the object does not exist.
    """
    if not key:
        return None
    client = _get_s3_client()
    bucket = _get_bucket_name()
    try:
        client.head_object(Bucket=bucket, Key=key)
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires,
        )
    except ClientError:
        return None


async def get_avatar_presigned_url(avatar_url: str | None) -> str | None:
    """Convert a stored avatar key to a presigned URL.

    If avatar_url is already a full URL (e.g. starts with http), return as-is.
    Otherwise treat it as an S3 key and generate a presigned URL.
    """
    if not avatar_url:
        return None
    if avatar_url.startswith("http://") or avatar_url.startswith("https://"):
        return avatar_url
    return await get_presigned_url(avatar_url)

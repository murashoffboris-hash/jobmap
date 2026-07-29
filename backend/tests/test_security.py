"""Tests for password hashing and JWT token services."""

from __future__ import annotations

from datetime import timedelta

import pytest
from jose import jwt

from app.config import settings
from app.services.auth import create_access_token, create_refresh_token, decode_token
from app.services.security import hash_password, verify_password

# ── Password hashing ──────────────────────────────────────────────

class TestPasswordHashing:
    def test_hash_and_verify(self):
        """Hash a password and verify it matches."""
        plain = "my_secret_p@ss!"
        hashed = hash_password(plain)
        assert hashed != plain
        assert hashed.startswith("$2b$")  # bcrypt hash marker
        assert verify_password(plain, hashed)

    def test_verify_wrong_password(self):
        """Verify returns False for the wrong password."""
        hashed = hash_password("correct_password")
        assert not verify_password("wrong_password", hashed)

    def test_verify_wrong_hash(self):
        """Verify returns False for corrupted hash."""
        assert not verify_password("password", "not-a-valid-hash")


# ── JWT tokens ───────────────────────────────────────────────────

class TestJWT:
    def test_create_access_token(self):
        """Create and decode an access token with string sub."""
        token = create_access_token(data={"sub": "42"})
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert "exp" in payload

    def test_access_token_accepts_int_sub(self):
        """Sub is auto-converted to string."""
        token = create_access_token(data={"sub": 1}, expires_delta=timedelta(hours=1))
        payload = decode_token(token)
        assert payload["sub"] == "1"

    def test_invalid_token_raises(self):
        """Decoding a tampered token raises 401-like exception."""
        with pytest.raises(Exception):
            decode_token("invalid.token.here")

    def test_refresh_token_has_type_refresh(self):
        """Refresh token carries type='refresh' claim."""
        token = create_refresh_token(data={"sub": "10"})
        payload = decode_token(token)
        assert payload["sub"] == "10"
        assert payload["type"] == "refresh"

    def test_expired_token_raises(self):
        """Expired token raises exception."""
        expired = jwt.encode(
            {"sub": "1", "exp": 0},  # already expired
            settings.JWT_SECRET,
            algorithm="HS256",
        )
        with pytest.raises(Exception):
            decode_token(expired)

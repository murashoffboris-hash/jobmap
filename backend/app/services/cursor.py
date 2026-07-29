"""Keyset-pagination cursor helpers.

Cursors are base64-encoded JSON blobs that encode the last-seen
(created_at, id) tuple so the next page can continue from where
the previous one left off.

Encoding: base64url(JSON({"c": "2026-07-27T12:00:00+00:00", "i": 42}))
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class Cursor:
    """A decoded keyset-pagination cursor pointing at one row."""

    created_at: datetime
    id: int

    def encode(self) -> str:
        """Encode cursor to a URL-safe token string (no padding)."""
        payload = json.dumps(
            {"c": self.created_at.isoformat(), "i": self.id},
            separators=(",", ":"),
        )
        return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, token: str | None) -> Cursor | None:
        """Decode a cursor token, or return None if it is invalid.

        Never raises — silently returns None on any decode failure
        so the caller can safely fall back to the first page.
        """
        if not token:
            return None
        try:
            # Add back padding if stripped (base64url without padding)
            padded = token + "=" * (4 - len(token) % 4) if len(token) % 4 else token
            raw = base64.urlsafe_b64decode(padded.encode())
            data = json.loads(raw)
            created_at = datetime.fromisoformat(data["c"])
            return cls(created_at=created_at, id=data["i"])
        except (ValueError, KeyError, TypeError, base64.binascii.Error):
            return None

    @classmethod
    def from_vacancy(cls, vacancy) -> Cursor:
        """Build a cursor from an ORM Vacancy instance."""
        return cls(created_at=vacancy.created_at, id=vacancy.id)

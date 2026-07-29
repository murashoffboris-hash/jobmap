"""Keyset pagination cursor for vacancy listing.

Encodes (created_at, id) as a compact URL-safe base64 token.
Ordering invariant: ``created_at DESC, id DESC`` — so the WHERE
clause uses ``<`` to fetch older / lower-id rows.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime


class Cursor:
    """Opaque token encoding a position in a keyset-paginated list."""

    __slots__ = ("created_at", "id")

    def __init__(self, created_at: datetime, id: int) -> None:
        self.created_at: datetime = created_at
        self.id: int = id

    # ── Serialisation ──────────────────────────────────────────

    def encode(self) -> str:
        """Return a URL-safe base64-encoded cursor string."""
        payload = json.dumps(
            {"c": self.created_at.isoformat(), "i": self.id},
            separators=(",", ":"),
        )
        return base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")

    @classmethod
    def decode(cls, token: str) -> Cursor:
        """Parse a previously-encoded cursor token back into a Cursor."""
        # Restore base64 padding
        padding = 4 - len(token) % 4
        if padding != 4:
            token += "=" * padding
        raw = base64.urlsafe_b64decode(token).decode()
        data = json.loads(raw)
        return cls(
            created_at=datetime.fromisoformat(data["c"]),
            id=data["i"],
        )

    # ── Factory ─────────────────────────────────────────────────

    @classmethod
    def from_vacancy(cls, vacancy) -> Cursor:
        """Build a cursor pointing at a specific Vacancy ORM object."""
        return cls(created_at=vacancy.created_at, id=vacancy.id)

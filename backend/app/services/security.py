"""Password hashing — bcrypt via passlib."""

from __future__ import annotations

import logging

from passlib.context import CryptContext
from passlib.exc import UnknownHashError

logger = logging.getLogger(__name__)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Hash a plain-text password using bcrypt (cost factor default=12)."""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash.

    Returns False for unrecognized hash formats instead of raising.
    """
    try:
        return pwd_context.verify(plain, hashed)
    except UnknownHashError:
        logger.warning("verify_password called with unrecognized hash format")
        return False

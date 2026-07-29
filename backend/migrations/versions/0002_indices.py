"""Add missing performance indices for production workload.

- vacancies.category_id (FK lookup)
- vacancies.created_at (sort by date)
- subscriptions.user_id (FK lookup, already exists as ix_subscriptions_user_id)
- composite indices for chat, responses, and reviews

Revision ID: 0002_indices
Revises: a8217e2f773e
Create Date: 2026-07-23 08:30:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0002_indices"
down_revision: str | None = "a8217e2f773e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── Vacancies ──────────────────────────────────────────────

    # FK lookup — already has owner_id, but category_id is NOT indexed
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vacancies_category_id "
        "ON vacancies (category_id)"
    )

    # Common sort (home page, search results)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vacancies_created_at "
        "ON vacancies (created_at DESC)"
    )

    # ── Responses ──────────────────────────────────────────────

    # Composite: employer filters responses by vacancy + status
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_responses_vacancy_status "
        "ON responses (vacancy_id, status)"
    )

    # ── Chats ──────────────────────────────────────────────────

    # User's active chats lookup
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chats_user_one_id "
        "ON chats (user_one_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_chats_user_two_id "
        "ON chats (user_two_id)"
    )

    # ── Messages ───────────────────────────────────────────────

    # Chat messages sorted by creation time (already has chat_id index)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_chat_id_created_at "
        "ON messages (chat_id, created_at)"
    )

    # ── Reviews ────────────────────────────────────────────────

    # Composite: find all reviews for a specific user (most common query)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_reviews_reviewed_user_rating "
        "ON reviews (reviewed_user_id, rating)"
    )

    # ── Notifications ──────────────────────────────────────────

    # User's unread notifications lookup
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_notifications_user_unread "
        "ON notifications (user_id, is_read)"
    )

    # ── Geocoding log ──────────────────────────────────────────

    # For dedup: same address, different vacancy
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_geocoding_log_addr_result "
        "ON geocoding_log (address_raw, success)"
    )

    # ── Audit log ──────────────────────────────────────────────

    # Admin queries: find actions by user or target
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_log_user_action "
        "ON audit_log (user_id, action)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_log_target "
        "ON audit_log (target_type, target_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_vacancies_category_id")
    op.execute("DROP INDEX IF EXISTS idx_vacancies_created_at")
    op.execute("DROP INDEX IF EXISTS idx_responses_vacancy_status")
    op.execute("DROP INDEX IF EXISTS idx_chats_user_one_id")
    op.execute("DROP INDEX IF EXISTS idx_chats_user_two_id")
    op.execute("DROP INDEX IF EXISTS idx_messages_chat_id_created_at")
    op.execute("DROP INDEX IF EXISTS idx_reviews_reviewed_user_rating")
    op.execute("DROP INDEX IF EXISTS idx_notifications_user_unread")
    op.execute("DROP INDEX IF EXISTS idx_geocoding_log_addr_result")
    op.execute("DROP INDEX IF EXISTS idx_audit_log_user_action")
    op.execute("DROP INDEX IF EXISTS idx_audit_log_target")

"""Keyset pagination index for vacancy list queries.

The new query pattern:
  SELECT ... FROM vacancies
  WHERE status = 'active'
    AND (created_at, id) < (:cursor_ts, :cursor_id)
  ORDER BY created_at DESC, id DESC
  LIMIT :page_size

A composite B-tree index on (created_at DESC, id DESC) lets
PostgreSQL use an index scan that is O(log N + page_size)
regardless of scroll depth, unlike OFFSET which degrades to
O(N + page_size).

Revision ID: 0004_keyset_index
Revises: 0003_nfr001_perf
Create Date: 2026-07-27 11:00:00
"""
from collections.abc import Sequence

from alembic import op

revision: str = "0004_keyset_index"
down_revision: str | Sequence[str] | None = ("0003_nfr001_perf", "0003_applications")
branch_labels: str | Sequence[str] | None = None


def upgrade() -> None:
    # Composite index for keyset pagination: (created_at DESC, id DESC)
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vacancies_keyset "
        "ON vacancies (created_at DESC, id DESC)"
    )

    # Partial variant: only active rows, smaller and even faster
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vacancies_keyset_active "
        "ON vacancies (created_at DESC, id DESC) WHERE status = 'active'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_vacancies_keyset")
    op.execute("DROP INDEX IF EXISTS idx_vacancies_keyset_active")

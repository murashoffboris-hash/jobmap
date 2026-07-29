"""Search and filter indices — pg_trgm for ILIKE search, city index.

Adds:
- pg_trgm extension (required for GIN indexes on ILIKE patterns)
- GIN index on title with trigram ops — speeds up ``ILIKE '%keyword%'``
- GIN index on description with trigram ops
- B-tree index on address_normalized — speeds up city filter

These indexes reduce full-table scans for search/filter queries from
O(n) to O(log n), critical for the vacancy list endpoint under load.

Revision ID: 0005_search_indices
Revises: 0003_nfr001_perf
Create Date: 2026-07-28 23:00:00
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0005_search_indices"
down_revision: Union[str, None] = "0003_nfr001_perf"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pg_trgm extension for trigram-based GIN indexes
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # GIN index on title for ILIKE search
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vacancies_title_trgm "
        "ON vacancies USING gin (title gin_trgm_ops)"
    )

    # GIN index on description for ILIKE search
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vacancies_description_trgm "
        "ON vacancies USING gin (description gin_trgm_ops)"
    )

    # B-tree index on address_normalized for city filter
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_vacancies_city "
        "ON vacancies (address_normalized)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_vacancies_title_trgm")
    op.execute("DROP INDEX IF EXISTS idx_vacancies_description_trgm")
    op.execute("DROP INDEX IF EXISTS idx_vacancies_city")
    # Don't drop the extension — it may be used by other features

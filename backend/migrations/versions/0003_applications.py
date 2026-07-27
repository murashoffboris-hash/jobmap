"""Add applications table for FR-007 — отклики на вакансии.

Revision ID: 0003_applications
Revises: 0002_indices
Create Date: 2026-07-25 17:30:00
"""
from typing import Sequence, Union

from alembic import op


revision: str = "0003_applications"
down_revision: Union[str, None] = "0002_indices"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ENUM type
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE applicationstatus AS ENUM ('pending', 'accepted', 'rejected', 'withdrawn'); "
        "EXCEPTION WHEN duplicate_object THEN null; "
        "END $$"
    )

    # Create applications table
    op.execute("""
        CREATE TABLE applications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE NOT NULL,
            vacancy_id INTEGER REFERENCES vacancies(id) ON DELETE CASCADE NOT NULL,
            cover_letter TEXT,
            status applicationstatus DEFAULT 'pending'::applicationstatus NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
            CONSTRAINT uq_application_user_vacancy UNIQUE (user_id, vacancy_id)
        )
    """)

    # Indexes
    op.execute("CREATE INDEX ix_applications_user_id ON applications (user_id)")
    op.execute("CREATE INDEX ix_applications_vacancy_id ON applications (vacancy_id)")
    op.execute(
        "CREATE INDEX ix_applications_vacancy_status "
        "ON applications (vacancy_id, status)"
    )
    op.execute(
        "CREATE INDEX ix_applications_user_created "
        "ON applications (user_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS applications CASCADE")
    op.execute("DROP TYPE IF EXISTS applicationstatus")

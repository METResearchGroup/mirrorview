"""Add model identifiers to submissions and generations.

Revision ID: 0002_model_ids
Revises: 0001_create_persistence_tables
Create Date: 2026-02-13
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0002_model_ids"
down_revision = "0001_create_persistence_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("submissions", sa.Column("selected_model_id", sa.Text(), nullable=True))
    op.add_column("generations", sa.Column("model_id", sa.Text(), nullable=True))

    # Backfill deterministic default for existing submissions.
    op.execute("update submissions set selected_model_id = 'gpt-5-nano' where selected_model_id is null")
    op.alter_column("submissions", "selected_model_id", existing_type=sa.Text(), nullable=False)

    # Best-effort backfill for existing generations.
    op.execute(
        """
        update generations g
        set model_id = coalesce(g.model_name, s.selected_model_id)
        from submissions s
        where g.submission_id = s.id and g.model_id is null
        """
    )


def downgrade() -> None:
    op.drop_column("generations", "model_id")
    op.drop_column("submissions", "selected_model_id")

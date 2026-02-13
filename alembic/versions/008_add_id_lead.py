"""Add id_lead column to leads and backfill existing rows

Revision ID: 008
Revises: 007
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "leads",
        sa.Column("id_lead", sa.Integer(), nullable=True),
    )
    op.create_index("ix_leads_id_lead", "leads", ["id_lead"])

    # Backfill existing leads: assign sequential id_lead per account ordered by created_at
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE leads
        SET id_lead = sub.rn
        FROM (
            SELECT id,
                   ROW_NUMBER() OVER (PARTITION BY cuenta_id ORDER BY created_at) AS rn
            FROM leads
        ) sub
        WHERE leads.id = sub.id
    """))


def downgrade() -> None:
    op.drop_index("ix_leads_id_lead", table_name="leads")
    op.drop_column("leads", "id_lead")

"""Add lotes table and lote_id to leads

Revision ID: 005
Revises: 004
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cuenta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column(
            "lead_base_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lead_bases.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("total_leads", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_lotes_cuenta_id", "lotes", ["cuenta_id"])
    op.create_index("ix_lotes_lead_base_id", "lotes", ["lead_base_id"])
    op.create_index("ix_lotes_created_at", "lotes", ["created_at"])

    op.add_column(
        "leads",
        sa.Column(
            "lote_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lotes.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_leads_lote_id", "leads", ["lote_id"])


def downgrade() -> None:
    op.drop_index("ix_leads_lote_id", table_name="leads")
    op.drop_column("leads", "lote_id")
    op.drop_table("lotes")

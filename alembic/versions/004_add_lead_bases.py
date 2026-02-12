"""Add lead_bases and routing_rules tables

Revision ID: 004
Revises: 003
Create Date: 2026-02-12 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lead_bases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cuenta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("es_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_lead_bases_cuenta_id", "lead_bases", ["cuenta_id"])
    op.create_index("ix_lead_bases_created_at", "lead_bases", ["created_at"])

    op.create_table(
        "routing_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lead_base_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lead_bases.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("campo", sa.String(255), nullable=False),
        sa.Column("operador", sa.String(20), nullable=False),
        sa.Column("valor", sa.String(500), nullable=False),
        sa.Column("prioridad", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_routing_rules_lead_base_id", "routing_rules", ["lead_base_id"])

    op.add_column(
        "leads",
        sa.Column(
            "lead_base_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("lead_bases.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_leads_lead_base_id", "leads", ["lead_base_id"])


def downgrade() -> None:
    op.drop_index("ix_leads_lead_base_id", table_name="leads")
    op.drop_column("leads", "lead_base_id")
    op.drop_table("routing_rules")
    op.drop_table("lead_bases")

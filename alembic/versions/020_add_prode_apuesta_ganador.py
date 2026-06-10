"""Add prode_apuestas_ganador table

Revision ID: 020
Revises: 019
Create Date: 2026-06-10
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prode_apuestas_ganador",
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("prode_users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "equipo_id",
            sa.Integer,
            sa.ForeignKey("prode_equipos.id"),
            nullable=False,
        ),
        sa.Column("puntos", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("prode_apuestas_ganador")

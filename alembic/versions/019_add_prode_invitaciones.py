"""Add prode invitaciones and registros pendientes

Revision ID: 019
Revises: 018
Create Date: 2026-06-09
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "prode_invitaciones",
        sa.Column("token", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "creado_por",
            UUID(as_uuid=True),
            sa.ForeignKey("prode_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("activo", sa.Boolean, nullable=False, server_default=sa.true()),
    )

    op.create_table(
        "prode_registros_pendientes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("nombre", sa.String(100), nullable=False),
        sa.Column("apellido", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "invitacion_token",
            UUID(as_uuid=True),
            sa.ForeignKey("prode_invitaciones.token", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("estado", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("prode_registros_pendientes")
    op.drop_table("prode_invitaciones")

"""add_tipificaciones_externas

Revision ID: 015
Revises: 014
Create Date: 2026-02-23 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Crear tabla tipificaciones_externas
    op.create_table(
        "tipificaciones_externas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cuenta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lead_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("id_neotel", sa.String(100), nullable=False),
        sa.Column("id_subresolucion", sa.String(100), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB, nullable=False),
        sa.Column("matched", sa.Boolean, server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )

    # Índices para búsquedas eficientes
    op.create_index(
        "ix_tipificaciones_externas_cuenta_id",
        "tipificaciones_externas",
        ["cuenta_id"],
    )
    op.create_index(
        "ix_tipificaciones_externas_lead_id",
        "tipificaciones_externas",
        ["lead_id"],
    )
    op.create_index(
        "ix_tipificaciones_externas_created_at",
        "tipificaciones_externas",
        ["created_at"],
    )
    op.create_index(
        "ix_tipificaciones_externas_cuenta_email",
        "tipificaciones_externas",
        ["cuenta_id", "email"],
    )
    op.create_index(
        "ix_tipificaciones_externas_cuenta_matched",
        "tipificaciones_externas",
        ["cuenta_id", "matched"],
    )

    # Agregar columna ultima_tipificacion a leads
    op.add_column(
        "leads",
        sa.Column("ultima_tipificacion", postgresql.JSONB, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leads", "ultima_tipificacion")
    op.drop_index("ix_tipificaciones_externas_cuenta_matched", "tipificaciones_externas")
    op.drop_index("ix_tipificaciones_externas_cuenta_email", "tipificaciones_externas")
    op.drop_index("ix_tipificaciones_externas_created_at", "tipificaciones_externas")
    op.drop_index("ix_tipificaciones_externas_lead_id", "tipificaciones_externas")
    op.drop_index("ix_tipificaciones_externas_cuenta_id", "tipificaciones_externas")
    op.drop_table("tipificaciones_externas")

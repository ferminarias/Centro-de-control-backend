"""add_ficha_configs

Revision ID: 014
Revises: 013
Create Date: 2026-02-19 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ficha_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cuenta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "campania_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("campanias.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
        sa.Column("campos", postgresql.JSONB, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("cuenta_id", "campania_id", name="uq_ficha_config_cuenta_campania"),
    )

    # Partial unique index: only one default config (campania_id IS NULL) per account
    op.execute(
        "CREATE UNIQUE INDEX uq_ficha_config_cuenta_default "
        "ON ficha_configs (cuenta_id) WHERE campania_id IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_ficha_config_cuenta_default")
    op.drop_table("ficha_configs")

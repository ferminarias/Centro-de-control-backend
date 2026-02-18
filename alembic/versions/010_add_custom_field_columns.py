"""Add column_name to custom_fields and create real columns on leads

Revision ID: 010
Revises: 009
Create Date: 2026-02-18 00:00:00.000000

"""
import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _sanitize(nombre_campo: str) -> str:
    clean = re.sub(r"[^a-z0-9]", "_", nombre_campo.lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    return f"cf_{clean}"


def upgrade() -> None:
    # 1. Add column_name to custom_fields
    op.add_column(
        "custom_fields",
        sa.Column("column_name", sa.String(100), nullable=True),
    )

    # 2. Backfill existing custom fields
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT id, nombre_campo FROM custom_fields")
    ).fetchall()

    for row_id, nombre_campo in rows:
        col_name = _sanitize(nombre_campo)

        # Update the custom_fields record
        conn.execute(
            sa.text("UPDATE custom_fields SET column_name = :col WHERE id = :id"),
            {"col": col_name, "id": row_id},
        )

        # Create real column on leads
        conn.execute(
            sa.text(f'ALTER TABLE leads ADD COLUMN IF NOT EXISTS "{col_name}" TEXT')
        )

        # Backfill from JSONB datos
        conn.execute(
            sa.text(
                f'UPDATE leads SET "{col_name}" = datos->>:field_name '
                f"WHERE datos ? :field_name"
            ),
            {"field_name": nombre_campo},
        )


def downgrade() -> None:
    # Drop all cf_ columns from leads
    conn = op.get_bind()
    rows = conn.execute(
        sa.text("SELECT column_name FROM custom_fields WHERE column_name IS NOT NULL")
    ).fetchall()

    for (col_name,) in rows:
        conn.execute(
            sa.text(f'ALTER TABLE leads DROP COLUMN IF EXISTS "{col_name}"')
        )

    op.drop_column("custom_fields", "column_name")

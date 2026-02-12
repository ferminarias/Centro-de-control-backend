"""Change tipo_dato from native enum to varchar

Revision ID: 002
Revises: 001
Create Date: 2025-01-02 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Convert column from enum to varchar, casting existing values
    op.execute(
        "ALTER TABLE custom_fields "
        "ALTER COLUMN tipo_dato TYPE VARCHAR(20) USING tipo_dato::text"
    )
    # Drop the old enum type
    op.execute("DROP TYPE IF EXISTS fieldtype")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE fieldtype AS ENUM "
        "('string', 'number', 'boolean', 'datetime', 'email', 'phone')"
    )
    op.execute(
        "ALTER TABLE custom_fields "
        "ALTER COLUMN tipo_dato TYPE fieldtype USING tipo_dato::fieldtype"
    )

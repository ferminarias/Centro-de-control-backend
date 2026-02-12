"""Initial tables

Revision ID: 001
Revises:
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("api_key", sa.String(64), unique=True, nullable=False),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("auto_crear_campos", sa.Boolean(), server_default=sa.text("true")),
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
    )
    op.create_index("ix_accounts_api_key", "accounts", ["api_key"])

    field_type_enum = postgresql.ENUM(
        "string", "number", "boolean", "datetime", "email", "phone",
        name="fieldtype",
        create_type=True,
    )

    op.create_table(
        "custom_fields",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cuenta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre_campo", sa.String(255), nullable=False),
        sa.Column("tipo_dato", field_type_enum, server_default="string"),
        sa.Column("descripcion", sa.String(500), nullable=True),
        sa.Column("es_requerido", sa.Boolean(), server_default=sa.text("false")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("cuenta_id", "nombre_campo", name="uq_account_field_name"),
    )
    op.create_index("ix_custom_fields_cuenta_id", "custom_fields", ["cuenta_id"])

    op.create_table(
        "records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cuenta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("datos", postgresql.JSONB(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_records_cuenta_id", "records", ["cuenta_id"])
    op.create_index("ix_records_created_at", "records", ["created_at"])
    op.create_index(
        "ix_records_datos_gin",
        "records",
        ["datos"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_table("records")
    op.drop_table("custom_fields")
    op.drop_table("accounts")
    op.execute("DROP TYPE IF EXISTS fieldtype")

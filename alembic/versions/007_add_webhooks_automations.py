"""Add webhooks and automations tables

Revision ID: 007
Revises: 006
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Webhooks ───────────────────────────────────────────────────────────
    op.create_table(
        "webhooks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cuenta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("eventos", postgresql.JSONB(), nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("headers_custom", postgresql.JSONB(), nullable=True),
        sa.Column("secret", sa.String(255), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_webhooks_cuenta_id", "webhooks", ["cuenta_id"])

    op.create_table(
        "webhook_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "webhook_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("webhooks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("evento", sa.String(100), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_webhook_logs_webhook_id", "webhook_logs", ["webhook_id"])
    op.create_index("ix_webhook_logs_created_at", "webhook_logs", ["created_at"])

    # ── Automations ────────────────────────────────────────────────────────
    op.create_table(
        "automations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "cuenta_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("trigger_tipo", sa.String(50), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_automations_cuenta_id", "automations", ["cuenta_id"])

    op.create_table(
        "automation_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "automation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("automations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("campo", sa.String(255), nullable=False),
        sa.Column("operador", sa.String(30), nullable=False),
        sa.Column("valor", sa.String(500), nullable=False, server_default=""),
        sa.Column("orden", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_index("ix_automation_conditions_automation_id", "automation_conditions", ["automation_id"])

    op.create_table(
        "automation_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "automation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("automations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tipo", sa.String(50), nullable=False),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("orden", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )
    op.create_index("ix_automation_actions_automation_id", "automation_actions", ["automation_id"])

    op.create_table(
        "automation_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "automation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("automations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("lead_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("trigger_evento", sa.String(50), nullable=False),
        sa.Column("conditions_passed", sa.Boolean(), nullable=False),
        sa.Column("actions_result", postgresql.JSONB(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_automation_logs_automation_id", "automation_logs", ["automation_id"])
    op.create_index("ix_automation_logs_created_at", "automation_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("automation_logs")
    op.drop_table("automation_actions")
    op.drop_table("automation_conditions")
    op.drop_table("automations")
    op.drop_table("webhook_logs")
    op.drop_table("webhooks")

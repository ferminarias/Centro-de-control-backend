"""Add VoIP / Call Center tables

Revision ID: 009
Revises: 008
Create Date: 2026-02-13 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SIP Providers
    op.create_table(
        "sip_providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cuenta_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("pais", sa.String(10), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sip_providers_cuenta_id", "sip_providers", ["cuenta_id"])

    # SIP Trunks
    op.create_table(
        "sip_trunks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cuenta_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("sip_providers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("port", sa.Integer(), server_default="5060"),
        sa.Column("username", sa.String(255), nullable=True),
        sa.Column("password", sa.String(255), nullable=True),
        sa.Column("transport", sa.String(10), server_default="udp"),
        sa.Column("codecs", sa.String(255), server_default="ulaw,alaw,g729"),
        sa.Column("caller_id", sa.String(50), nullable=True),
        sa.Column("max_concurrent", sa.Integer(), server_default="30"),
        sa.Column("cps", sa.Integer(), server_default="5"),
        sa.Column("prefix", sa.String(20), nullable=True),
        sa.Column("strip_digits", sa.Integer(), server_default="0"),
        sa.Column("activo", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_sip_trunks_cuenta_id", "sip_trunks", ["cuenta_id"])
    op.create_index("ix_sip_trunks_provider_id", "sip_trunks", ["provider_id"])

    # PBX Nodes
    op.create_table(
        "pbx_nodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cuenta_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("host", sa.String(255), nullable=False),
        sa.Column("ami_port", sa.Integer(), server_default="5038"),
        sa.Column("ami_user", sa.String(100), nullable=False),
        sa.Column("ami_password", sa.String(255), nullable=False),
        sa.Column("ari_port", sa.Integer(), server_default="8088"),
        sa.Column("ari_user", sa.String(100), nullable=True),
        sa.Column("ari_password", sa.String(255), nullable=True),
        sa.Column("activo", sa.Boolean(), server_default="true"),
        sa.Column("last_health_check", sa.DateTime(timezone=True), nullable=True),
        sa.Column("health_status", sa.String(20), server_default="unknown"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_pbx_nodes_cuenta_id", "pbx_nodes", ["cuenta_id"])

    # Agents
    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cuenta_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("pbx_node_id", UUID(as_uuid=True), sa.ForeignKey("pbx_nodes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("extension", sa.String(20), nullable=False),
        sa.Column("sip_password", sa.String(255), nullable=False),
        sa.Column("estado", sa.String(20), server_default="offline"),
        sa.Column("pause_reason", sa.String(255), nullable=True),
        sa.Column("current_call_id", UUID(as_uuid=True), nullable=True),
        sa.Column("skills", JSONB(), nullable=True),
        sa.Column("max_concurrent_calls", sa.Integer(), server_default="1"),
        sa.Column("wrap_up_seconds", sa.Integer(), server_default="30"),
        sa.Column("activo", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agents_cuenta_id", "agents", ["cuenta_id"])
    op.create_index("ix_agents_user_id", "agents", ["user_id"])

    # Dispositions
    op.create_table(
        "dispositions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cuenta_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo", sa.String(50), nullable=False),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("es_contacto", sa.Boolean(), server_default="false"),
        sa.Column("es_final", sa.Boolean(), server_default="true"),
        sa.Column("requiere_reagendamiento", sa.Boolean(), server_default="false"),
        sa.Column("activo", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cuenta_id", "codigo", name="uq_account_disposition_code"),
    )
    op.create_index("ix_dispositions_cuenta_id", "dispositions", ["cuenta_id"])

    # Campaigns
    op.create_table(
        "campaigns",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cuenta_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("trunk_id", UUID(as_uuid=True), sa.ForeignKey("sip_trunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("pbx_node_id", UUID(as_uuid=True), sa.ForeignKey("pbx_nodes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("nombre", sa.String(255), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("dialer_mode", sa.String(20), server_default="manual"),
        sa.Column("caller_id", sa.String(50), nullable=True),
        sa.Column("estado", sa.String(20), server_default="draft"),
        sa.Column("hora_inicio", sa.Time(), nullable=True),
        sa.Column("hora_fin", sa.Time(), nullable=True),
        sa.Column("timezone", sa.String(50), server_default="America/Argentina/Buenos_Aires"),
        sa.Column("dias_semana", JSONB(), nullable=True),
        sa.Column("max_concurrent_calls", sa.Integer(), server_default="5"),
        sa.Column("max_retries", sa.Integer(), server_default="3"),
        sa.Column("retry_delay_minutes", sa.Integer(), server_default="60"),
        sa.Column("ring_timeout", sa.Integer(), server_default="30"),
        sa.Column("abandon_timeout", sa.Integer(), server_default="5"),
        sa.Column("predictive_ratio", sa.Float(), server_default="1.2"),
        sa.Column("total_leads", sa.Integer(), server_default="0"),
        sa.Column("leads_contacted", sa.Integer(), server_default="0"),
        sa.Column("leads_pending", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_campaigns_cuenta_id", "campaigns", ["cuenta_id"])
    op.create_index("ix_campaigns_estado", "campaigns", ["estado"])

    # Campaign Agents (M2M)
    op.create_table(
        "campaign_agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("prioridad", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("campaign_id", "agent_id", name="uq_campaign_agent"),
    )
    op.create_index("ix_campaign_agents_campaign_id", "campaign_agents", ["campaign_id"])
    op.create_index("ix_campaign_agents_agent_id", "campaign_agents", ["agent_id"])

    # Campaign Leads
    op.create_table(
        "campaign_leads",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False),
        sa.Column("lead_id", UUID(as_uuid=True), sa.ForeignKey("leads.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telefono", sa.String(50), nullable=False),
        sa.Column("estado", sa.String(20), server_default="pending"),
        sa.Column("intentos", sa.Integer(), server_default="0"),
        sa.Column("ultimo_intento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("proximo_intento", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disposition_id", UUID(as_uuid=True), sa.ForeignKey("dispositions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("disposition_nota", sa.Text(), nullable=True),
        sa.Column("callback_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_lead"),
    )
    op.create_index("ix_campaign_leads_campaign_id", "campaign_leads", ["campaign_id"])
    op.create_index("ix_campaign_leads_lead_id", "campaign_leads", ["lead_id"])
    op.create_index("ix_campaign_leads_estado", "campaign_leads", ["estado"])
    op.create_index("ix_campaign_leads_proximo_intento", "campaign_leads", ["proximo_intento"])

    # Call Records (CDR)
    op.create_table(
        "call_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cuenta_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("campaign_id", UUID(as_uuid=True), sa.ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True),
        sa.Column("campaign_lead_id", UUID(as_uuid=True), sa.ForeignKey("campaign_leads.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True),
        sa.Column("trunk_id", UUID(as_uuid=True), sa.ForeignKey("sip_trunks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uniqueid", sa.String(100), nullable=True),
        sa.Column("linkedid", sa.String(100), nullable=True),
        sa.Column("caller_id", sa.String(50), nullable=True),
        sa.Column("destino", sa.String(50), nullable=False),
        sa.Column("extension", sa.String(20), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration", sa.Integer(), server_default="0"),
        sa.Column("billsec", sa.Integer(), server_default="0"),
        sa.Column("wait_time", sa.Integer(), server_default="0"),
        sa.Column("resultado", sa.String(20), server_default="pending"),
        sa.Column("hangup_cause", sa.Integer(), nullable=True),
        sa.Column("hangup_cause_text", sa.String(100), nullable=True),
        sa.Column("disposition_id", UUID(as_uuid=True), sa.ForeignKey("dispositions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("disposition_nota", sa.Text(), nullable=True),
        sa.Column("recording_path", sa.Text(), nullable=True),
        sa.Column("recording_url", sa.Text(), nullable=True),
        sa.Column("direccion", sa.String(10), server_default="outbound"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_call_records_cuenta_id", "call_records", ["cuenta_id"])
    op.create_index("ix_call_records_campaign_id", "call_records", ["campaign_id"])
    op.create_index("ix_call_records_agent_id", "call_records", ["agent_id"])
    op.create_index("ix_call_records_uniqueid", "call_records", ["uniqueid"])
    op.create_index("ix_call_records_created_at", "call_records", ["created_at"])

    # Call Events
    op.create_table(
        "call_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("call_record_id", UUID(as_uuid=True), sa.ForeignKey("call_records.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evento", sa.String(50), nullable=False),
        sa.Column("detalle", JSONB(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_call_events_call_record_id", "call_events", ["call_record_id"])

    # DNC Entries
    op.create_table(
        "dnc_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cuenta_id", UUID(as_uuid=True), sa.ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("telefono", sa.String(50), nullable=False),
        sa.Column("motivo", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("cuenta_id", "telefono", name="uq_account_dnc_phone"),
    )
    op.create_index("ix_dnc_entries_cuenta_id", "dnc_entries", ["cuenta_id"])
    op.create_index("ix_dnc_entries_telefono", "dnc_entries", ["telefono"])


def downgrade() -> None:
    op.drop_table("call_events")
    op.drop_table("call_records")
    op.drop_table("campaign_leads")
    op.drop_table("campaign_agents")
    op.drop_table("campaigns")
    op.drop_table("dispositions")
    op.drop_table("agents")
    op.drop_table("pbx_nodes")
    op.drop_table("sip_trunks")
    op.drop_table("sip_providers")
    op.drop_table("dnc_entries")

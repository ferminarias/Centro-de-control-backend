"""
VoIP / Call Center models.

Entity hierarchy (all per cuenta_id):
  SipProvider → SipTrunk (carrier credentials)
  PbxNode (Asterisk instance, AMI/ARI creds)
  Agent (user + SIP extension, state, queues)
  Campaign → CampaignLead (links to Lead), dispositions, schedules
  CallRecord (CDR), CallRecording, CallEvent (timeline)
  Disposition (tipificaciones)
  DncEntry (Do-Not-Call blacklist)
"""

import enum
import uuid
from datetime import datetime, time

from sqlalchemy import (
    Boolean, DateTime, Enum, Float, ForeignKey, Integer,
    String, Text, Time, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ═══════════════════════════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════════════════════════

class AgentStatus(str, enum.Enum):
    OFFLINE = "offline"
    AVAILABLE = "available"
    BUSY = "busy"
    RINGING = "ringing"
    ON_CALL = "on_call"
    WRAP_UP = "wrap_up"
    PAUSED = "paused"


class CampaignStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"


class DialerMode(str, enum.Enum):
    MANUAL = "manual"
    PROGRESSIVE = "progressive"
    PREDICTIVE = "predictive"


class CampaignLeadStatus(str, enum.Enum):
    PENDING = "pending"
    DIALING = "dialing"
    CONTACTED = "contacted"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    DNC = "dnc"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class CallResult(str, enum.Enum):
    ANSWERED = "answered"
    NO_ANSWER = "no_answer"
    BUSY = "busy"
    FAILED = "failed"
    CONGESTION = "congestion"
    ABANDONED = "abandoned"
    REJECTED = "rejected"
    TIMEOUT = "timeout"


# ═══════════════════════════════════════════════════════════════════════════
# SIP Provider  (carrier / empresa de telefonía)
# ═══════════════════════════════════════════════════════════════════════════

class SipProvider(Base):
    __tablename__ = "sip_providers"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    pais: Mapped[str | None] = mapped_column(String(10), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship()  # noqa: F821
    trunks: Mapped[list["SipTrunk"]] = relationship(back_populates="provider", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════════════════
# SIP Trunk (troncal, credenciales SIP de salida/entrada)
# ═══════════════════════════════════════════════════════════════════════════

class SipTrunk(Base):
    __tablename__ = "sip_trunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    provider_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sip_providers.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    # PJSIP config
    host: Mapped[str] = mapped_column(String(255), nullable=False, comment="SIP server host/IP")
    port: Mapped[int] = mapped_column(Integer, default=5060)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transport: Mapped[str] = mapped_column(String(10), default="udp", comment="udp/tcp/tls")
    codecs: Mapped[str] = mapped_column(String(255), default="ulaw,alaw,g729", comment="Comma-separated")
    caller_id: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Default CallerID for this trunk")
    # Limits
    max_concurrent: Mapped[int] = mapped_column(Integer, default=30, comment="Max concurrent calls")
    cps: Mapped[int] = mapped_column(Integer, default=5, comment="Calls per second limit")
    # Prefix/routing
    prefix: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Dial prefix to prepend")
    strip_digits: Mapped[int] = mapped_column(Integer, default=0, comment="Digits to strip from number start")
    # State
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    provider: Mapped["SipProvider"] = relationship(back_populates="trunks")


# ═══════════════════════════════════════════════════════════════════════════
# PBX Node (instancia de Asterisk)
# ═══════════════════════════════════════════════════════════════════════════

class PbxNode(Base):
    __tablename__ = "pbx_nodes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False, comment="Asterisk IP/hostname")
    ami_port: Mapped[int] = mapped_column(Integer, default=5038)
    ami_user: Mapped[str] = mapped_column(String(100), nullable=False)
    ami_password: Mapped[str] = mapped_column(String(255), nullable=False)
    ari_port: Mapped[int] = mapped_column(Integer, default=8088)
    ari_user: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ari_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    last_health_check: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    health_status: Mapped[str] = mapped_column(String(20), default="unknown", comment="ok/error/unknown")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship()  # noqa: F821


# ═══════════════════════════════════════════════════════════════════════════
# Agent (agente de call center, linked to User)
# ═══════════════════════════════════════════════════════════════════════════

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    pbx_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pbx_nodes.id", ondelete="SET NULL"), nullable=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    # SIP extension
    extension: Mapped[str] = mapped_column(String(20), nullable=False, comment="SIP extension number (e.g. 1001)")
    sip_password: Mapped[str] = mapped_column(String(255), nullable=False, comment="SIP auth password for MicroSIP")
    # State
    estado: Mapped[str] = mapped_column(String(20), default=AgentStatus.OFFLINE.value)
    pause_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_call_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Skills / queues
    skills: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list, comment='["ventas","soporte"]')
    max_concurrent_calls: Mapped[int] = mapped_column(Integer, default=1)
    wrap_up_seconds: Mapped[int] = mapped_column(Integer, default=30, comment="Seconds of wrap-up after call")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship()  # noqa: F821
    user: Mapped["User | None"] = relationship()  # noqa: F821
    pbx_node: Mapped["PbxNode | None"] = relationship()


# ═══════════════════════════════════════════════════════════════════════════
# Disposition (tipificaciones de llamada)
# ═══════════════════════════════════════════════════════════════════════════

class Disposition(Base):
    __tablename__ = "dispositions"
    __table_args__ = (
        UniqueConstraint("cuenta_id", "codigo", name="uq_account_disposition_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(50), nullable=False, comment="e.g. VENTA, NO_INTERESADO, RELLAMAR")
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    es_contacto: Mapped[bool] = mapped_column(Boolean, default=False, comment="Counts as successful contact")
    es_final: Mapped[bool] = mapped_column(Boolean, default=True, comment="No more retries needed")
    requiere_reagendamiento: Mapped[bool] = mapped_column(Boolean, default=False, comment="Agent must set callback datetime")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship()  # noqa: F821


# ═══════════════════════════════════════════════════════════════════════════
# Campaign
# ═══════════════════════════════════════════════════════════════════════════

class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    trunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sip_trunks.id", ondelete="SET NULL"), nullable=True)
    pbx_node_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("pbx_nodes.id", ondelete="SET NULL"), nullable=True)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Dialer
    dialer_mode: Mapped[str] = mapped_column(String(20), default=DialerMode.MANUAL.value)
    caller_id: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="Override trunk callerID")
    # Status
    estado: Mapped[str] = mapped_column(String(20), default=CampaignStatus.DRAFT.value, index=True)
    # Schedule
    hora_inicio: Mapped[time | None] = mapped_column(Time, nullable=True, comment="Daily start time")
    hora_fin: Mapped[time | None] = mapped_column(Time, nullable=True, comment="Daily end time")
    timezone: Mapped[str] = mapped_column(String(50), default="America/Argentina/Buenos_Aires")
    dias_semana: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=lambda: [1, 2, 3, 4, 5], comment="1=Mon..7=Sun")
    # Limits
    max_concurrent_calls: Mapped[int] = mapped_column(Integer, default=5)
    max_retries: Mapped[int] = mapped_column(Integer, default=3, comment="Max dial attempts per lead")
    retry_delay_minutes: Mapped[int] = mapped_column(Integer, default=60, comment="Min minutes between retries")
    ring_timeout: Mapped[int] = mapped_column(Integer, default=30, comment="Seconds to ring before giving up")
    abandon_timeout: Mapped[int] = mapped_column(Integer, default=5, comment="Seconds before connected call with no agent = abandoned")
    # Predictive params
    predictive_ratio: Mapped[float] = mapped_column(Float, default=1.2, comment="Calls per available agent (predictive mode)")
    # Metrics (cached)
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    leads_contacted: Mapped[int] = mapped_column(Integer, default=0)
    leads_pending: Mapped[int] = mapped_column(Integer, default=0)
    #
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    account: Mapped["Account"] = relationship()  # noqa: F821
    trunk: Mapped["SipTrunk | None"] = relationship()
    pbx_node: Mapped["PbxNode | None"] = relationship()
    campaign_leads: Mapped[list["CampaignLead"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")
    campaign_agents: Mapped[list["CampaignAgent"]] = relationship(back_populates="campaign", cascade="all, delete-orphan")


# ═══════════════════════════════════════════════════════════════════════════
# CampaignAgent (M2M: agents assigned to campaign)
# ═══════════════════════════════════════════════════════════════════════════

class CampaignAgent(Base):
    __tablename__ = "campaign_agents"
    __table_args__ = (
        UniqueConstraint("campaign_id", "agent_id", name="uq_campaign_agent"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    agent_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True)
    prioridad: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    campaign: Mapped["Campaign"] = relationship(back_populates="campaign_agents")
    agent: Mapped["Agent"] = relationship()


# ═══════════════════════════════════════════════════════════════════════════
# CampaignLead (lead dentro de una campaña, con estado de marcación)
# ═══════════════════════════════════════════════════════════════════════════

class CampaignLead(Base):
    __tablename__ = "campaign_leads"
    __table_args__ = (
        UniqueConstraint("campaign_id", "lead_id", name="uq_campaign_lead"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), index=True)
    lead_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), index=True)
    telefono: Mapped[str] = mapped_column(String(50), nullable=False, comment="Phone to dial")
    # Dial state
    estado: Mapped[str] = mapped_column(String(20), default=CampaignLeadStatus.PENDING.value, index=True)
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    ultimo_intento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    proximo_intento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    # Disposition
    disposition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dispositions.id", ondelete="SET NULL"), nullable=True)
    disposition_nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Scheduling
    callback_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    #
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    campaign: Mapped["Campaign"] = relationship(back_populates="campaign_leads")
    lead: Mapped["Lead"] = relationship()  # noqa: F821
    disposition: Mapped["Disposition | None"] = relationship()
    assigned_agent: Mapped["Agent | None"] = relationship()


# ═══════════════════════════════════════════════════════════════════════════
# CallRecord (CDR interno)
# ═══════════════════════════════════════════════════════════════════════════

class CallRecord(Base):
    __tablename__ = "call_records"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    campaign_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="SET NULL"), nullable=True, index=True)
    campaign_lead_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("campaign_leads.id", ondelete="SET NULL"), nullable=True)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True)
    trunk_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sip_trunks.id", ondelete="SET NULL"), nullable=True)
    # Call info
    uniqueid: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True, comment="Asterisk Uniqueid")
    linkedid: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Asterisk Linkedid for bridged calls")
    caller_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    destino: Mapped[str] = mapped_column(String(50), nullable=False, comment="Dialed number")
    extension: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="Agent extension")
    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration: Mapped[int] = mapped_column(Integer, default=0, comment="Total duration seconds")
    billsec: Mapped[int] = mapped_column(Integer, default=0, comment="Billable seconds (after answer)")
    wait_time: Mapped[int] = mapped_column(Integer, default=0, comment="Seconds ringing before answer")
    # Result
    resultado: Mapped[str] = mapped_column(String(20), default="pending", comment="answered/no_answer/busy/failed/abandoned/etc")
    hangup_cause: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="SIP/Asterisk hangup cause code")
    hangup_cause_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # Disposition
    disposition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("dispositions.id", ondelete="SET NULL"), nullable=True)
    disposition_nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Recording
    recording_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    recording_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Direction
    direccion: Mapped[str] = mapped_column(String(10), default="outbound", comment="outbound/inbound")
    #
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    account: Mapped["Account"] = relationship()  # noqa: F821
    campaign: Mapped["Campaign | None"] = relationship()
    campaign_lead: Mapped["CampaignLead | None"] = relationship()
    agent: Mapped["Agent | None"] = relationship()
    disposition: Mapped["Disposition | None"] = relationship()
    events: Mapped[list["CallEvent"]] = relationship(back_populates="call_record", cascade="all, delete-orphan", order_by="CallEvent.timestamp")


# ═══════════════════════════════════════════════════════════════════════════
# CallEvent (timeline de eventos de una llamada)
# ═══════════════════════════════════════════════════════════════════════════

class CallEvent(Base):
    __tablename__ = "call_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    call_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("call_records.id", ondelete="CASCADE"), index=True)
    evento: Mapped[str] = mapped_column(String(50), nullable=False, comment="originate/ringing/answered/bridged/hangup/recording_ready/disposition")
    detalle: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call_record: Mapped["CallRecord"] = relationship(back_populates="events")


# ═══════════════════════════════════════════════════════════════════════════
# DNC (Do Not Call list)
# ═══════════════════════════════════════════════════════════════════════════

class DncEntry(Base):
    __tablename__ = "dnc_entries"
    __table_args__ = (
        UniqueConstraint("cuenta_id", "telefono", name="uq_account_dnc_phone"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cuenta_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True)
    telefono: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    motivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    account: Mapped["Account"] = relationship()  # noqa: F821

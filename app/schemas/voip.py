"""Pydantic schemas for VoIP / Call Center entities."""

import uuid
from datetime import datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict


# ═══════════════════════════════════════════════════════════════════════════
# SIP Provider
# ═══════════════════════════════════════════════════════════════════════════

class SipProviderCreate(BaseModel):
    nombre: str
    pais: str | None = None
    notas: str | None = None

class SipProviderUpdate(BaseModel):
    nombre: str | None = None
    pais: str | None = None
    notas: str | None = None
    activo: bool | None = None

class SipProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cuenta_id: uuid.UUID
    nombre: str
    pais: str | None = None
    notas: str | None = None
    activo: bool
    created_at: datetime

class SipProviderListResponse(BaseModel):
    items: list[SipProviderResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# SIP Trunk
# ═══════════════════════════════════════════════════════════════════════════

class SipTrunkCreate(BaseModel):
    provider_id: uuid.UUID
    nombre: str
    host: str
    port: int = 5060
    username: str | None = None
    password: str | None = None
    transport: str = "udp"
    codecs: str = "ulaw,alaw,g729"
    caller_id: str | None = None
    max_concurrent: int = 30
    cps: int = 5
    prefix: str | None = None
    strip_digits: int = 0

class SipTrunkUpdate(BaseModel):
    nombre: str | None = None
    host: str | None = None
    port: int | None = None
    username: str | None = None
    password: str | None = None
    transport: str | None = None
    codecs: str | None = None
    caller_id: str | None = None
    max_concurrent: int | None = None
    cps: int | None = None
    prefix: str | None = None
    strip_digits: int | None = None
    activo: bool | None = None

class SipTrunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cuenta_id: uuid.UUID
    provider_id: uuid.UUID
    nombre: str
    host: str
    port: int
    username: str | None = None
    transport: str
    codecs: str
    caller_id: str | None = None
    max_concurrent: int
    cps: int
    prefix: str | None = None
    strip_digits: int
    activo: bool
    created_at: datetime

class SipTrunkListResponse(BaseModel):
    items: list[SipTrunkResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# PBX Node
# ═══════════════════════════════════════════════════════════════════════════

class PbxNodeCreate(BaseModel):
    nombre: str
    host: str
    ami_port: int = 5038
    ami_user: str
    ami_password: str
    ari_port: int = 8088
    ari_user: str | None = None
    ari_password: str | None = None

class PbxNodeUpdate(BaseModel):
    nombre: str | None = None
    host: str | None = None
    ami_port: int | None = None
    ami_user: str | None = None
    ami_password: str | None = None
    ari_port: int | None = None
    ari_user: str | None = None
    ari_password: str | None = None
    activo: bool | None = None

class PbxNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cuenta_id: uuid.UUID
    nombre: str
    host: str
    ami_port: int
    ami_user: str
    ari_port: int
    activo: bool
    health_status: str
    last_health_check: datetime | None = None
    created_at: datetime

class PbxNodeListResponse(BaseModel):
    items: list[PbxNodeResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# Agent
# ═══════════════════════════════════════════════════════════════════════════

class AgentCreate(BaseModel):
    user_id: uuid.UUID | None = None
    pbx_node_id: uuid.UUID | None = None
    nombre: str
    extension: str
    sip_password: str
    skills: list[str] = []
    max_concurrent_calls: int = 1
    wrap_up_seconds: int = 30

class AgentUpdate(BaseModel):
    nombre: str | None = None
    extension: str | None = None
    sip_password: str | None = None
    pbx_node_id: uuid.UUID | None = None
    skills: list[str] | None = None
    max_concurrent_calls: int | None = None
    wrap_up_seconds: int | None = None
    activo: bool | None = None

class AgentStatusUpdate(BaseModel):
    estado: str
    pause_reason: str | None = None

class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cuenta_id: uuid.UUID
    user_id: uuid.UUID | None = None
    pbx_node_id: uuid.UUID | None = None
    nombre: str
    extension: str
    estado: str
    pause_reason: str | None = None
    current_call_id: uuid.UUID | None = None
    skills: list[str] | None = None
    max_concurrent_calls: int
    wrap_up_seconds: int
    activo: bool
    created_at: datetime

class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# Disposition
# ═══════════════════════════════════════════════════════════════════════════

class DispositionCreate(BaseModel):
    codigo: str
    nombre: str
    es_contacto: bool = False
    es_final: bool = True
    requiere_reagendamiento: bool = False

class DispositionUpdate(BaseModel):
    codigo: str | None = None
    nombre: str | None = None
    es_contacto: bool | None = None
    es_final: bool | None = None
    requiere_reagendamiento: bool | None = None
    activo: bool | None = None

class DispositionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cuenta_id: uuid.UUID
    codigo: str
    nombre: str
    es_contacto: bool
    es_final: bool
    requiere_reagendamiento: bool
    activo: bool
    created_at: datetime

class DispositionListResponse(BaseModel):
    items: list[DispositionResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# Campaign
# ═══════════════════════════════════════════════════════════════════════════

class CampaignCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    trunk_id: uuid.UUID | None = None
    pbx_node_id: uuid.UUID | None = None
    dialer_mode: str = "manual"
    caller_id: str | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    timezone: str = "America/Argentina/Buenos_Aires"
    dias_semana: list[int] | None = None
    max_concurrent_calls: int = 5
    max_retries: int = 3
    retry_delay_minutes: int = 60
    ring_timeout: int = 30
    abandon_timeout: int = 5
    predictive_ratio: float = 1.2

class CampaignUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    trunk_id: uuid.UUID | None = None
    pbx_node_id: uuid.UUID | None = None
    dialer_mode: str | None = None
    caller_id: str | None = None
    hora_inicio: time | None = None
    hora_fin: time | None = None
    timezone: str | None = None
    dias_semana: list[int] | None = None
    max_concurrent_calls: int | None = None
    max_retries: int | None = None
    retry_delay_minutes: int | None = None
    ring_timeout: int | None = None
    abandon_timeout: int | None = None
    predictive_ratio: float | None = None

class CampaignResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cuenta_id: uuid.UUID
    trunk_id: uuid.UUID | None = None
    pbx_node_id: uuid.UUID | None = None
    nombre: str
    descripcion: str | None = None
    dialer_mode: str
    caller_id: str | None = None
    estado: str
    hora_inicio: time | None = None
    hora_fin: time | None = None
    timezone: str
    dias_semana: list[int] | None = None
    max_concurrent_calls: int
    max_retries: int
    retry_delay_minutes: int
    ring_timeout: int
    abandon_timeout: int
    predictive_ratio: float
    total_leads: int
    leads_contacted: int
    leads_pending: int
    created_at: datetime
    updated_at: datetime

class CampaignListResponse(BaseModel):
    items: list[CampaignResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# CampaignLead
# ═══════════════════════════════════════════════════════════════════════════

class CampaignLeadAdd(BaseModel):
    lead_id: uuid.UUID
    telefono: str

class CampaignLeadBulkAdd(BaseModel):
    """Add leads from a lead_base or lote, extracting phone from a datos field."""
    source_type: str  # "lead_base" or "lote"
    source_id: uuid.UUID
    campo_telefono: str  # field name in datos JSONB that contains the phone number

class CampaignLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    campaign_id: uuid.UUID
    lead_id: uuid.UUID
    telefono: str
    estado: str
    intentos: int
    ultimo_intento: datetime | None = None
    proximo_intento: datetime | None = None
    disposition_id: uuid.UUID | None = None
    disposition_nota: str | None = None
    callback_at: datetime | None = None
    assigned_agent_id: uuid.UUID | None = None
    created_at: datetime

class CampaignLeadListResponse(BaseModel):
    items: list[CampaignLeadResponse]
    total: int

class CampaignLeadDisposition(BaseModel):
    disposition_id: uuid.UUID
    nota: str | None = None
    callback_at: datetime | None = None


# ═══════════════════════════════════════════════════════════════════════════
# CallRecord
# ═══════════════════════════════════════════════════════════════════════════

class CallRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cuenta_id: uuid.UUID
    campaign_id: uuid.UUID | None = None
    agent_id: uuid.UUID | None = None
    uniqueid: str | None = None
    caller_id: str | None = None
    destino: str
    extension: str | None = None
    started_at: datetime | None = None
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    duration: int
    billsec: int
    wait_time: int
    resultado: str
    hangup_cause: int | None = None
    hangup_cause_text: str | None = None
    disposition_id: uuid.UUID | None = None
    disposition_nota: str | None = None
    recording_url: str | None = None
    direccion: str
    created_at: datetime

class CallRecordListResponse(BaseModel):
    items: list[CallRecordResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# CallEvent
# ═══════════════════════════════════════════════════════════════════════════

class CallEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    call_record_id: uuid.UUID
    evento: str
    detalle: dict | None = None
    timestamp: datetime


# ═══════════════════════════════════════════════════════════════════════════
# DNC
# ═══════════════════════════════════════════════════════════════════════════

class DncCreate(BaseModel):
    telefono: str
    motivo: str | None = None

class DncResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    cuenta_id: uuid.UUID
    telefono: str
    motivo: str | None = None
    created_at: datetime

class DncListResponse(BaseModel):
    items: list[DncResponse]
    total: int


# ═══════════════════════════════════════════════════════════════════════════
# Dialer control
# ═══════════════════════════════════════════════════════════════════════════

class ManualCallRequest(BaseModel):
    agent_id: uuid.UUID
    campaign_lead_id: uuid.UUID

class ManualCallResponse(BaseModel):
    call_id: uuid.UUID
    uniqueid: str | None = None
    status: str
    message: str

class CampaignStatsResponse(BaseModel):
    campaign_id: uuid.UUID
    estado: str
    total_leads: int
    leads_pending: int
    leads_contacted: int
    leads_no_answer: int
    leads_busy: int
    leads_failed: int
    leads_completed: int
    active_calls: int
    available_agents: int
    asr: float | None = None  # Answer-Seizure Ratio
    aht: float | None = None  # Average Handle Time (seconds)
    contact_rate: float | None = None

"""
Schemas Pydantic para Campañas de Contact Center
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


# ─────────────────────────────────────────────────────────────────────────────
# Enums como strings
# ─────────────────────────────────────────────────────────────────────────────

class TipoDiscador(str):
    SIN_DISCADOR = "sin_discador"
    PREVIEW = "preview"
    PROGRESIVO = "progresivo"
    PREDICTIVO = "predictivo"


class EstadoCampania(str):
    BORRADOR = "borrador"
    ACTIVA = "activa"
    PAUSADA = "pausada"
    FINALIZADA = "finalizada"


# ─────────────────────────────────────────────────────────────────────────────
# Campaña Base
# ─────────────────────────────────────────────────────────────────────────────

class CampaniaBase(BaseModel):
    nombre: str
    descripcion: str | None = None
    tipo_discador: str = "sin_discador"
    config_discador: dict = {}
    permite_llamada_manual: bool = True
    grabar_llamadas: bool = False
    horario_inicio: str | None = None  # HH:MM
    horario_fin: str | None = None  # HH:MM
    dias_operacion: list[int] = []
    tipificaciones_permitidas: list[str] = []
    prioridad: int = 5


class CampaniaCreate(CampaniaBase):
    base_ids: list[uuid.UUID] = []  # Bases a asignar
    agente_ids: list[uuid.UUID] = []  # Agentes a asignar


class CampaniaUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    estado: str | None = None
    tipo_discador: str | None = None
    config_discador: dict | None = None
    permite_llamada_manual: bool | None = None
    grabar_llamadas: bool | None = None
    horario_inicio: str | None = None
    horario_fin: str | None = None
    dias_operacion: list[int] | None = None
    tipificaciones_permitidas: list[str] | None = None
    prioridad: int | None = None


class CampaniaResponse(CampaniaBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    cuenta_id: uuid.UUID
    estado: str
    created_at: datetime
    updated_at: datetime
    created_by: uuid.UUID | None
    
    # Contadores
    total_bases: int = 0
    total_agentes: int = 0
    leads_en_cola: int = 0


class CampaniaListResponse(BaseModel):
    items: list[CampaniaResponse]
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# Campaña-Bases
# ─────────────────────────────────────────────────────────────────────────────

class CampaniaBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    base_id: uuid.UUID
    base_nombre: str
    activo: bool
    prioridad: int
    filtros: dict | None
    added_at: datetime


class CampaniaBaseAssign(BaseModel):
    base_ids: list[uuid.UUID]


# ─────────────────────────────────────────────────────────────────────────────
# Campaña-Agentes
# ─────────────────────────────────────────────────────────────────────────────

class CampaniaAgenteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    agente_id: uuid.UUID
    agente_nombre: str
    agente_email: str
    activo: bool
    nivel_skill: int
    max_fichas: int
    added_at: datetime
    
    # Estado actual en la campaña
    estado_actual: str | None = None
    fichas_gestionadas_hoy: int = 0


class CampaniaAgenteAssign(BaseModel):
    agente_ids: list[uuid.UUID]


class AgenteEstadoUpdate(BaseModel):
    estado: str  # disponible, pausado, etc.
    motivo: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Cola de Leads
# ─────────────────────────────────────────────────────────────────────────────

class ColaLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    lead_id: uuid.UUID
    estado: str
    prioridad: int
    intentos: int
    agente_asignado_id: uuid.UUID | None
    agente_asignado_nombre: str | None = None
    proximo_intento: datetime | None
    added_at: datetime
    
    # Datos del lead
    lead_datos: dict = {}
    lead_telefono: str | None = None


class ColaLeadListResponse(BaseModel):
    items: list[ColaLeadResponse]
    total: int
    pendientes: int
    asignados: int
    completados: int


class LeadPendienteResponse(BaseModel):
    """Ficha que le cae a un agente"""
    cola_id: uuid.UUID
    lead_id: uuid.UUID
    campania_id: uuid.UUID
    campania_nombre: str
    
    # Datos completos del lead
    lead: dict  # LeadResponse completo
    
    # Historial de gestiones previas
    historial: list[dict] = []
    
    # Script o guión de la campaña
    script: str | None = None

    # Ficha config resuelta (campos configurados)
    ficha_config: dict | None = None


class GestionFichaRequest(BaseModel):
    """Datos cuando el agente gestiona una ficha"""
    tipificacion_id: uuid.UUID | None = None
    subtipificacion_id: uuid.UUID | None = None
    notas: str | None = None
    
    # Para llamadas
    resultado_llamada: str | None = None  # contestado, no_contestado, ocupado, etc.
    duracion_segundos: int | None = None
    grabacion_url: str | None = None
    
    # Callback
    agendar_callback: bool = False
    callback_fecha: datetime | None = None
    callback_observacion: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Solicitar/Asignar ficha
# ─────────────────────────────────────────────────────────────────────────────

class SolicitarFichaResponse(BaseModel):
    """Respuesta cuando un agente solicita una ficha"""
    success: bool
    message: str
    ficha: LeadPendienteResponse | None = None


class SaltarFichaRequest(BaseModel):
    """Cuando un agente quiere saltar una ficha"""
    motivo: str  # requiere_tipificacion obligatoria


# ─────────────────────────────────────────────────────────────────────────────
# Métricas y Reportes
# ─────────────────────────────────────────────────────────────────────────────

class MetricasCampania(BaseModel):
    campania_id: uuid.UUID
    campania_nombre: str
    
    # Volumetría
    total_leads: int
    leads_pendientes: int
    leads_gestionados_hoy: int
    
    # Agentes
    agentes_conectados: int
    agentes_disponibles: int
    agentes_en_llamada: int
    agentes_pausados: int
    
    # Efectividad (hoy)
    llamadas_realizadas: int
    llamadas_conectadas: int
    porcentaje_contacto: float
    
    # Tipificaciones más comunes
    top_tipificaciones: list[dict] = []

"""
Schemas para CRM Extras: Actividades, Tareas, Notas, Tags, AuditLog
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# =============================================================================
# ACTIVIDADES
# =============================================================================

class ActividadBase(BaseModel):
    tipo: str = Field(..., description="Tipo: llamada, email, reunion, whatsapp, sms, nota, cambio_estado")
    direccion: str = Field(default="salida", description="entrada o salida")
    asunto: str | None = None
    descripcion: str | None = None
    metadata_: dict[str, Any] = Field(default_factory=dict, alias="metadata")
    fecha_inicio: datetime
    fecha_fin: datetime | None = None
    resultado: str | None = Field(None, description="contestado, no_contestado, reunion_agendada, etc.")


class ActividadCreate(ActividadBase):
    lead_id: uuid.UUID
    user_id: uuid.UUID | None = None


class ActividadUpdate(BaseModel):
    tipo: str | None = None
    asunto: str | None = None
    descripcion: str | None = None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata")
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    resultado: str | None = None


class ActividadResponse(ActividadBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    
    id: uuid.UUID
    cuenta_id: uuid.UUID
    lead_id: uuid.UUID
    user_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    
    # Datos relacionados (opcionales, para responses enriquecidos)
    user_nombre: str | None = None
    lead_nombre: str | None = None


class ActividadListResponse(BaseModel):
    items: list[ActividadResponse]
    total: int


# =============================================================================
# TAREAS
# =============================================================================

class TareaBase(BaseModel):
    titulo: str = Field(..., min_length=1, max_length=255)
    descripcion: str | None = None
    tipo: str = Field(default="seguimiento", description="llamar, enviar_email, reunion, seguimiento")
    prioridad: str = Field(default="media", description="baja, media, alta, urgente")
    estado: str = Field(default="pendiente", description="pendiente, en_progreso, completada, cancelada, vencida")
    fecha_vencimiento: datetime | None = None
    es_recurrente: bool = False
    frecuencia: str | None = Field(None, description="diaria, semanal, mensual")


class TareaCreate(TareaBase):
    lead_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class TareaUpdate(BaseModel):
    titulo: str | None = Field(None, min_length=1, max_length=255)
    descripcion: str | None = None
    tipo: str | None = None
    prioridad: str | None = None
    estado: str | None = None
    fecha_vencimiento: datetime | None = None
    es_recurrente: bool | None = None
    frecuencia: str | None = None


class TareaComplete(BaseModel):
    """Para marcar tarea como completada"""
    pass


class TareaResponse(TareaBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    cuenta_id: uuid.UUID
    lead_id: uuid.UUID | None
    user_id: uuid.UUID | None
    fecha_completada: datetime | None
    recordatorio_enviado: bool
    recordatorio_fecha: datetime | None
    created_at: datetime
    updated_at: datetime
    
    # Datos relacionados
    user_nombre: str | None = None
    lead_nombre: str | None = None


class TareaListResponse(BaseModel):
    items: list[TareaResponse]
    total: int


class TareaStats(BaseModel):
    """Estadísticas de tareas"""
    pendientes: int
    vencidas: int
    completadas_hoy: int
    completadas_semana: int


# =============================================================================
# NOTAS
# =============================================================================

class NotaBase(BaseModel):
    contenido: str = Field(..., min_length=1)
    tipo: str = Field(default="general", description="general, reunion, llamada, sistema, cambio_tipificacion")
    es_privada: bool = False


class NotaCreate(NotaBase):
    lead_id: uuid.UUID


class NotaUpdate(BaseModel):
    contenido: str | None = Field(None, min_length=1)
    es_privada: bool | None = None


class NotaResponse(NotaBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    cuenta_id: uuid.UUID
    lead_id: uuid.UUID
    user_id: uuid.UUID | None
    es_sistema: bool
    created_at: datetime
    updated_at: datetime
    
    # Datos relacionados
    user_nombre: str | None = None
    user_avatar: str | None = None


class NotaListResponse(BaseModel):
    items: list[NotaResponse]
    total: int


# =============================================================================
# TAGS
# =============================================================================

class TagBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    descripcion: str | None = Field(None, max_length=500)
    orden: int = 0
    activo: bool = True


class TagCreate(TagBase):
    pass


class TagUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    descripcion: str | None = Field(None, max_length=500)
    orden: int | None = None
    activo: bool | None = None


class TagResponse(TagBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    cuenta_id: uuid.UUID
    es_sistema: bool
    created_at: datetime
    total_leads: int = 0


class TagListResponse(BaseModel):
    items: list[TagResponse]
    total: int


class LeadTagAssign(BaseModel):
    """Para asignar/quitar tags a un lead"""
    tag_ids: list[uuid.UUID]


class LeadTagResponse(BaseModel):
    """Tag con datos de asignación"""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    nombre: str
    color: str
    assigned_at: datetime
    assigned_by: str | None


# =============================================================================
# AUDIT LOG
# =============================================================================

class AuditLogBase(BaseModel):
    entidad_tipo: str = Field(..., description="lead, oportunidad, tarea, actividad, etc.")
    entidad_id: uuid.UUID
    accion: str = Field(..., description="create, update, delete, view, export, assign")
    campo: str | None = None
    valor_anterior: str | None = None
    valor_nuevo: str | None = None
    snapshot: dict[str, Any] | None = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    cuenta_id: uuid.UUID
    user_id: uuid.UUID | None
    ip_address: str | None
    endpoint: str | None
    created_at: datetime
    
    # Datos relacionados
    user_nombre: str | None = None
    user_email: str | None = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int


# =============================================================================
# LEAD TIMELINE (Respuesta combinada)
# =============================================================================

class LeadTimelineItem(BaseModel):
    """Item unificado para el timeline/historial de un lead"""
    tipo: str  # 'actividad', 'tarea', 'nota', 'cambio', 'creacion'
    fecha: datetime
    titulo: str
    descripcion: str | None
    usuario: str | None
    metadata: dict[str, Any] | None

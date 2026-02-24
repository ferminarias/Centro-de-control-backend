"""
Modelos para Campañas de Contact Center
Gestión de campañas, colas de leads y asignaciones a agentes
"""
import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Boolean, Text, Time, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipoDiscador(str, Enum):
    """Tipos de discador para campañas"""
    SIN_DISCADOR = "sin_discador"  # Manual, el agente marca
    PREVIEW = "preview"  # Muestra ficha antes de llamar
    PROGRESIVO = "progresivo"  # Llama automáticamente cuando agente está libre
    PREDICTIVO = "predictivo"  # Predice cuándo habrá agente disponible


class EstadoCampania(str, Enum):
    """Estados posibles de una campaña"""
    BORRADOR = "borrador"
    ACTIVA = "activa"
    PAUSADA = "pausada"
    FINALIZADA = "finalizada"


class Campania(Base):
    """
    Campaña de contact center (consolidada VoIP + Contact Center)
    Define configuración, discador, bases asignadas, troncales SIP, etc.
    """
    __tablename__ = "campanias"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    # Información básica
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    estado: Mapped[str] = mapped_column(
        String(20), default=EstadoCampania.BORRADOR
    )
    
    # Tipo de discador (unificado)
    tipo_discador: Mapped[str] = mapped_column(
        String(20), default=TipoDiscador.SIN_DISCADOR,
        comment="sin_discador/manual, preview, progresivo, predictivo"
    )
    
    # Configuración del discador (JSON flexible)
    config_discador: Mapped[dict] = mapped_column(
        JSONB, default=dict,
        comment="Config específica: timeout, demora_llamada, canales_max, etc."
    )
    
    # ─────────────────────────────────────────────────────────────────
    # Campos VoIP (migrados desde campaigns)
    # ─────────────────────────────────────────────────────────────────
    trunk_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sip_trunks.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    pbx_node_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pbx_nodes.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    caller_id: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
        comment="Override del CallerID para esta campaña"
    )
    
    # Límites y timeouts
    max_concurrent_calls: Mapped[int] = mapped_column(
        Integer, default=5,
        comment="Máximo de llamadas concurrentes"
    )
    max_retries: Mapped[int] = mapped_column(
        Integer, default=3,
        comment="Máximo de intentos por lead"
    )
    retry_delay_minutes: Mapped[int] = mapped_column(
        Integer, default=60,
        comment="Minutos entre reintentos"
    )
    ring_timeout: Mapped[int] = mapped_column(
        Integer, default=30,
        comment="Segundos de ring antes de colgar"
    )
    abandon_timeout: Mapped[int] = mapped_column(
        Integer, default=5,
        comment="Segundos antes de considerar llamada abandonada"
    )
    
    # Predictive params
    predictive_ratio: Mapped[float] = mapped_column(
        Float, default=1.2,
        comment="Ratio llamadas/agente disponible (modo predictivo)"
    )
    
    # Métricas cacheadas
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    leads_contacted: Mapped[int] = mapped_column(Integer, default=0)
    leads_pending: Mapped[int] = mapped_column(Integer, default=0)
    
    # Configuración de la campaña
    permite_llamada_manual: Mapped[bool] = mapped_column(
        Boolean, default=True,
        comment="Permite al agente marcar números manualmente"
    )
    grabar_llamadas: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Horarios de operación
    horario_inicio: Mapped[str | None] = mapped_column(
        String(5), comment="HH:MM formato 24h"
    )
    horario_fin: Mapped[str | None] = mapped_column(
        String(5), comment="HH:MM formato 24h"
    )
    dias_operacion: Mapped[list] = mapped_column(
        JSONB, default=list,
        comment="[1,2,3,4,5] = Lunes a Viernes"
    )
    
    # Tipificaciones permitidas en esta campaña
    tipificaciones_permitidas: Mapped[list] = mapped_column(
        JSONB, default=list,
        comment="IDs de tipificaciones que se pueden usar"
    )
    
    # Prioridad de la campaña (1-10, mayor = más prioridad)
    prioridad: Mapped[int] = mapped_column(Integer, default=5)
    
    # Metadatos
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Relationships - Contact Center
    account: Mapped["Account"] = relationship(back_populates="campanias")  # noqa: F821
    bases: Mapped[list["CampaniaBase"]] = relationship(
        back_populates="campania", cascade="all, delete-orphan"
    )
    agentes: Mapped[list["CampaniaAgente"]] = relationship(
        back_populates="campania", cascade="all, delete-orphan"
    )
    cola: Mapped[list["ColaLead"]] = relationship(
        back_populates="campania", cascade="all, delete-orphan"
    )
    
    # Relationships - VoIP
    trunk: Mapped["SipTrunk | None"] = relationship()  # noqa: F821
    pbx_node: Mapped["PbxNode | None"] = relationship()  # noqa: F821
    campaign_leads: Mapped[list["CampaignLead"]] = relationship(
        back_populates="campania", cascade="all, delete-orphan"
    )
    campaign_agents: Mapped[list["CampaignAgent"]] = relationship(
        back_populates="campania", cascade="all, delete-orphan"
    )


class CampaniaBase(Base):
    """
    Relación muchos a muchos entre Campaña y Bases de datos
    Define qué bases están asignadas a una campaña
    """
    __tablename__ = "campania_bases"

    campania_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanias.id", ondelete="CASCADE"),
        primary_key=True
    )
    base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lead_bases.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # Config específica para esta base en esta campaña
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    prioridad: Mapped[int] = mapped_column(Integer, default=5)
    
    # Filtros (opcional) - solo leads que cumplan estas condiciones
    filtros: Mapped[dict | None] = mapped_column(
        JSONB,
        comment="Ej: {'ciudad': 'Guayaquil', 'score_min': 50}"
    )
    
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    campania: Mapped["Campania"] = relationship(back_populates="bases")  # noqa: F821
    base: Mapped["LeadBase"] = relationship()  # noqa: F821


class CampaniaAgente(Base):
    """
    Agentes asignados a una campaña
    """
    __tablename__ = "campania_agentes"

    campania_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanias.id", ondelete="CASCADE"),
        primary_key=True
    )
    agente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # Estado del agente en la campaña
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Nivel de habilidad (1-10) para distribución ponderada
    nivel_skill: Mapped[int] = mapped_column(Integer, default=5)
    
    # Límite de fichas simultáneas (para predictivo)
    max_fichas: Mapped[int] = mapped_column(Integer, default=1)
    
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    
    # Relationships
    campania: Mapped["Campania"] = relationship(back_populates="agentes")  # noqa: F821
    agente: Mapped["User"] = relationship()  # noqa: F821


class EstadoCola(str, Enum):
    """Estados de un lead en cola"""
    PENDIENTE = "pendiente"  # En cola, esperando agente
    ASIGNADO = "asignado"    # Asignado a un agente
    GESTIONANDO = "gestionando"  # El agente está trabajando la ficha
    COMPLETADO = "completado"    # Ya fue tipificado
    RECHAZADO = "rechazado"      # El agente lo rechazó
    PAUSADO = "pausado"          # Temporalmente pausado


class ColaLead(Base):
    """
    Cola de leads pendientes por gestionar en una campaña
    """
    __tablename__ = "cola_leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    campania_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanias.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    # Estado en la cola
    estado: Mapped[str] = mapped_column(
        String(20), default=EstadoCola.PENDIENTE, index=True
    )
    
    # Asignación
    agente_asignado_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    
    # Prioridad en cola (mayor = atender primero)
    prioridad: Mapped[int] = mapped_column(Integer, default=0)
    
    # Intentos de contacto
    intentos: Mapped[int] = mapped_column(Integer, default=0)
    ultimo_intento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Próximo intento programado
    proximo_intento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    
    # Motivo de rechazo (si aplica)
    motivo_rechazo: Mapped[str | None] = mapped_column(String(255))
    
    # Fechas
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Relationships
    campania: Mapped["Campania"] = relationship(back_populates="cola")  # noqa: F821
    lead: Mapped["Lead"] = relationship()  # noqa: F821
    agente: Mapped["User | None"] = relationship()  # noqa: F821


class EstadoAgenteEnCampania(str, Enum):
    """Estados de un agente dentro de una campaña"""
    OFFLINE = "offline"
    DISPONIBLE = "disponible"  # Listo para recibir fichas
    PAUSADO = "pausado"        # En pausa (baño, almuerzo, etc.)
    GESTIONANDO = "gestionando"  # Trabajando una ficha
    EN_LLAMADA = "en_llamada"    # En llamada activa


class AgenteCampaniaLog(Base):
    """
    Log de actividad de agentes en campañas
    Registra cuando entran, salen, pausas, etc.
    """
    __tablename__ = "agente_campania_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    campania_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campanias.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    agente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    # Estado
    estado: Mapped[str] = mapped_column(String(20))
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Duración calculada (en segundos)
    duracion_segundos: Mapped[int | None] = mapped_column(Integer)
    
    # Motivo (para pausas)
    motivo: Mapped[str | None] = mapped_column(String(255))

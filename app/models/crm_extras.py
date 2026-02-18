"""
Modelos adicionales para CRM completo:
- Actividades/Interacciones
- Tareas/Recordatorios
- Notas
- Audit Log
- Tags/Etiquetas
"""
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, 
    String, Text, func, Numeric
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Actividad(Base):
    """
    Historial de interacciones con leads (llamadas, emails, reuniones, etc.)
    """
    __tablename__ = "actividades"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    
    # Tipo de actividad
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    # 'llamada', 'email', 'reunion', 'whatsapp', 'sms', 'nota', 'cambio_estado'
    
    direccion: Mapped[str] = mapped_column(String(20), default="salida")
    # 'entrada' (recibido) o 'salida' (enviado)
    
    # Contenido
    asunto: Mapped[str | None] = mapped_column(String(255))
    descripcion: Mapped[str | None] = mapped_column(Text)
    
    # Metadatos específicos por tipo (JSONB flexible)
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    # Ej llamada: {"duracion_segundos": 120, "grabacion_url": "...", "numero_marcado": "..."}
    # Ej email: {"email_id": "...", "asunto_email": "...", "abierto": true, "clicks": 2}
    # Ej reunion: {"ubicacion": "Zoom", "link": "...", "asistentes": [...]}
    
    # Fechas
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Resultado/Outcome
    resultado: Mapped[str | None] = mapped_column(String(100))
    # 'contestado', 'no_contestado', 'buzon_voz', 'reunion_agendada', 
    # 'email_abierto', 'email_rebotado', 'interesado', 'no_interesado'
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="actividades")  # noqa: F821
    lead: Mapped["Lead"] = relationship(back_populates="actividades")  # noqa: F821
    user: Mapped["User | None"] = relationship(back_populates="actividades")  # noqa: F821


class Tarea(Base):
    """
    Tareas y recordatorios para seguimiento de leads
    """
    __tablename__ = "tareas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    
    tipo: Mapped[str] = mapped_column(String(50), default="seguimiento")
    # 'llamar', 'enviar_email', 'reunion', 'seguimiento', 'preparar_propuesta'
    
    prioridad: Mapped[str] = mapped_column(String(20), default="media")
    # 'baja', 'media', 'alta', 'urgente'
    
    estado: Mapped[str] = mapped_column(String(30), default="pendiente")
    # 'pendiente', 'en_progreso', 'completada', 'cancelada', 'vencida'
    
    fecha_vencimiento: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True
    )
    fecha_completada: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Recordatorios
    recordatorio_enviado: Mapped[bool] = mapped_column(Boolean, default=False)
    recordatorio_fecha: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    
    # Si es recurrente
    es_recurrente: Mapped[bool] = mapped_column(Boolean, default=False)
    frecuencia: Mapped[str | None] = mapped_column(String(30))
    # 'diaria', 'semanal', 'mensual'
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="tareas")  # noqa: F821
    lead: Mapped["Lead | None"] = relationship(back_populates="tareas")  # noqa: F821
    user: Mapped["User | None"] = relationship(back_populates="tareas")  # noqa: F821


class Nota(Base):
    """
    Notas simples adjuntas a leads
    """
    __tablename__ = "notas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    contenido: Mapped[str] = mapped_column(Text, nullable=False)
    
    tipo: Mapped[str] = mapped_column(String(50), default="general")
    # 'general', 'reunion', 'llamada', 'sistema', 'cambio_tipificacion'
    
    es_privada: Mapped[bool] = mapped_column(Boolean, default=False)
    # Solo visible para el creador
    
    # Si es generada por sistema (automática)
    es_sistema: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="notas")  # noqa: F821
    lead: Mapped["Lead"] = relationship(back_populates="notas")  # noqa: F821
    user: Mapped["User | None"] = relationship(back_populates="notas")  # noqa: F821


class AuditLog(Base):
    """
    Historial de cambios en entidades (trazabilidad completa)
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    
    # Entidad afectada
    entidad_tipo: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # 'lead', 'oportunidad', 'tarea', 'actividad', 'tipificacion'
    
    entidad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    
    accion: Mapped[str] = mapped_column(String(30), nullable=False)
    # 'create', 'update', 'delete', 'view', 'export', 'assign'
    
    # Cambios específicos (para updates)
    campo: Mapped[str | None] = mapped_column(String(100))
    valor_anterior: Mapped[str | None] = mapped_column(Text)
    valor_nuevo: Mapped[str | None] = mapped_column(Text)
    
    # Snapshot completo opcional
    snapshot: Mapped[dict | None] = mapped_column(JSONB)
    
    # Metadatos de request
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    endpoint: Mapped[str | None] = mapped_column(String(255))
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="audit_logs")  # noqa: F821
    user: Mapped["User | None"] = relationship(back_populates="audit_logs")  # noqa: F821


class Tag(Base):
    """
    Etiquetas/Tags para categorización flexible de leads
    """
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#6B7280")
    descripcion: Mapped[str | None] = mapped_column(String(500))
    
    # Sistema (no se puede eliminar, ej: 'nuevo', 'favorito')
    es_sistema: Mapped[bool] = mapped_column(Boolean, default=False)
    
    orden: Mapped[int] = mapped_column(Integer, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="tags")  # noqa: F821
    leads: Mapped[list["Lead"]] = relationship(
        secondary="lead_tags", back_populates="tags"
    )


class LeadTag(Base):
    """
    Tabla intermedia many-to-many entre Lead y Tag
    """
    __tablename__ = "lead_tags"

    lead_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("leads.id", ondelete="CASCADE"),
        primary_key=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True
    )
    
    # Quién aplicó el tag (opcional)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    lead: Mapped["Lead"] = relationship(back_populates="lead_tags")  # noqa: F821
    tag: Mapped["Tag"] = relationship(back_populates="lead_tags")  # noqa: F821

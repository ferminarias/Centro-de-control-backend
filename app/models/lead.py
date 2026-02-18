import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    id_lead: Mapped[int | None] = mapped_column(
        Integer, nullable=True, index=True,
        comment="Human-readable sequential ID, unique per account",
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    record_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("records.id", ondelete="CASCADE"),
        unique=True,
    )
    lead_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lead_bases.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    lote_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lotes.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    
    # Tipificación del lead (clasificación)
    tipificacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("tipificaciones.id", ondelete="SET NULL"),
        nullable=True, 
        index=True,
        comment="Categoría principal de tipificación",
    )
    subtipificacion_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("subtipificaciones.id", ondelete="SET NULL"),
        nullable=True, 
        index=True,
        comment="Subcategoría de tipificación",
    )
    
    # ASIGNACIÓN/OWNERSHIP
    assigned_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Usuario asignado al lead (vendedor/agente)",
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Fecha de asignación",
    )
    assigned_by_rule: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Regla de asignación: 'manual', 'round_robin', 'por_campo', 'automatico'",
    )
    
    # SCORING/VALORACIÓN
    score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Puntuación 0-100 del lead",
    )
    temperatura: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="'frio', 'templado', 'caliente', 'muy_caliente'",
    )
    
    datos: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="leads")  # noqa: F821
    record: Mapped["Record"] = relationship(back_populates="lead")  # noqa: F821
    lead_base: Mapped["LeadBase | None"] = relationship(back_populates="leads")  # noqa: F821
    lote: Mapped["Lote | None"] = relationship(back_populates="leads")  # noqa: F821
    
    # Tipificaciones
    tipificacion: Mapped["Tipificacion | None"] = relationship(
        back_populates="leads",
        foreign_keys=[tipificacion_id]
    )  # noqa: F821
    subtipificacion: Mapped["Subtipificacion | None"] = relationship(
        back_populates="leads",
        foreign_keys=[subtipificacion_id]
    )  # noqa: F821
    
    # Asignación
    assigned_to: Mapped["User | None"] = relationship(
        back_populates="assigned_leads",
        foreign_keys=[assigned_to_id]
    )  # noqa: F821
    
    # CRM Extras
    actividades: Mapped[list["Actividad"]] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="Actividad.created_at.desc()"
    )  # noqa: F821
    
    tareas: Mapped[list["Tarea"]] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="Tarea.fecha_vencimiento"
    )  # noqa: F821
    
    notas: Mapped[list["Nota"]] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="Nota.created_at.desc()"
    )  # noqa: F821
    
    tags: Mapped[list["Tag"]] = relationship(
        secondary="lead_tags",
        back_populates="leads",
        overlaps="lead_tags,lead"
    )  # noqa: F821
    
    lead_tags: Mapped[list["LeadTag"]] = relationship(
        back_populates="lead",
        cascade="all, delete-orphan",
        overlaps="tags,leads"
    )  # noqa: F821

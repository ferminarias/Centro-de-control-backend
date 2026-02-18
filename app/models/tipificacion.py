"""
Tipificaciones y Subtipificaciones para clasificación de Leads.

Este módulo permite crear categorías jerárquicas para clasificar leads:
- Tipificación: Categoría principal (ej: "Interesado", "No interesado", "En seguimiento")
- Subtipificación: Subcategoría anidada (ej: "Interesado > Precio alto", "Interesado > Quiere demo")
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Boolean, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Tipificacion(Base):
    """
    Categoría principal de tipificación para leads.
    
    Ejemplos: "Interesado", "No interesado", "En seguimiento", "No contactado"
    """
    
    __tablename__ = "tipificaciones"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("accounts.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Campos principales
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Color para identificación visual en UI (hex: #FF5733)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True, default="#6B7280")
    
    # Orden para mostrar en listas (menor = primero)
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Estado
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Es categoría final (no permite subtipificaciones)
    es_final: Mapped[bool] = mapped_column(
        Boolean, 
        default=False, 
        nullable=False,
        comment="Si es True, no permite subtipificaciones"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    account: Mapped["Account"] = relationship(back_populates="tipificaciones")  # noqa: F821
    subtipificaciones: Mapped[list["Subtipificacion"]] = relationship(
        back_populates="tipificacion",
        cascade="all, delete-orphan",
        order_by="Subtipificacion.orden"
    )
    leads: Mapped[list["Lead"]] = relationship(
        back_populates="tipificacion",
        foreign_keys="Lead.tipificacion_id"
    )
    
    def __repr__(self) -> str:
        return f"<Tipificacion {self.nombre}>"


class Subtipificacion(Base):
    """
    Subcategoría de tipificación, anidada bajo una Tipificacion.
    
    Ejemplos: 
    - Bajo "Interesado": "Quiere demo", "Pide presupuesto", "Decide en X días"
    - Bajo "No interesado": "No tiene presupuesto", "Ya tiene proveedor", "No es el decisor"
    """
    
    __tablename__ = "subtipificaciones"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    
    # Relación con tipificación padre
    tipificacion_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tipificaciones.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), 
        ForeignKey("accounts.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Campos principales
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Color para identificación visual (hereda del padre si es null)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    
    # Orden para mostrar en listas
    orden: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Estado
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    
    # Relationships
    tipificacion: Mapped["Tipificacion"] = relationship(back_populates="subtipificaciones")  # noqa: F821
    account: Mapped["Account"] = relationship(back_populates="subtipificaciones")  # noqa: F821
    leads: Mapped[list["Lead"]] = relationship(
        back_populates="subtipificacion",
        foreign_keys="Lead.subtipificacion_id"
    )
    
    def __repr__(self) -> str:
        return f"<Subtipificacion {self.nombre}>"

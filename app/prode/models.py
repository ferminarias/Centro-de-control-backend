import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProdeUser(Base):
    __tablename__ = "prode_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    es_gerente: Mapped[bool] = mapped_column(Boolean, default=False)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)
    club_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("prode_clubes.id", use_alter=True, name="fk_prode_user_club_id"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ProdeEquipo(Base):
    __tablename__ = "prode_equipos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    nombre_api: Mapped[str] = mapped_column(String(100), nullable=False)
    codigo_iso: Mapped[str] = mapped_column(String(10), nullable=False)
    grupo: Mapped[str] = mapped_column(String(1), nullable=False)
    api_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True)


class ProdePartido(Base):
    __tablename__ = "prode_partidos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    equipo_local_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("prode_equipos.id"), nullable=True
    )
    equipo_visitante_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("prode_equipos.id"), nullable=True
    )
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estadio: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    fase: Mapped[str] = mapped_column(String(20), nullable=False, default="grupo")
    grupo: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    jornada: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    api_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, unique=True)
    goles_local: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    goles_visitante: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="programado")

    equipo_local: Mapped[Optional["ProdeEquipo"]] = relationship(
        "ProdeEquipo", foreign_keys=[equipo_local_id], lazy="joined"
    )
    equipo_visitante: Mapped[Optional["ProdeEquipo"]] = relationship(
        "ProdeEquipo", foreign_keys=[equipo_visitante_id], lazy="joined"
    )


class ProdeClub(Base):
    __tablename__ = "prode_clubes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    gerente_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prode_users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProdeInvitacion(Base):
    __tablename__ = "prode_invitaciones"

    token: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    creado_por: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prode_users.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ProdeRegistroPendiente(Base):
    __tablename__ = "prode_registros_pendientes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    invitacion_token: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prode_invitaciones.token", ondelete="SET NULL"), nullable=True
    )
    estado: Mapped[str] = mapped_column(String(20), nullable=False, default="pendiente")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProdePrediccion(Base):
    __tablename__ = "prode_predicciones"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("prode_users.id", ondelete="CASCADE"), nullable=False
    )
    partido_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("prode_partidos.id", ondelete="CASCADE"), nullable=False
    )
    goles_local: Mapped[int] = mapped_column(Integer, nullable=False)
    goles_visitante: Mapped[int] = mapped_column(Integer, nullable=False)
    puntos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    partido: Mapped["ProdePartido"] = relationship(
        "ProdePartido", foreign_keys=[partido_id], lazy="joined"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "partido_id", name="uq_prediccion_user_partido"),
    )

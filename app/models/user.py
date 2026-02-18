import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("cuenta_id", "email", name="uq_account_user_email"),
        UniqueConstraint("cuenta_id", "username", name="uq_account_username"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    role_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    apellido: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    account: Mapped["Account"] = relationship(back_populates="users")  # noqa: F821
    role: Mapped["Role | None"] = relationship(back_populates="users")  # noqa: F821
    
    # Leads asignados a este usuario
    assigned_leads: Mapped[list["Lead"]] = relationship(
        back_populates="assigned_to",
        foreign_keys="Lead.assigned_to_id"
    )  # noqa: F821
    
    # CRM Extras
    actividades: Mapped[list["Actividad"]] = relationship(back_populates="user")  # noqa: F821
    tareas: Mapped[list["Tarea"]] = relationship(back_populates="user")  # noqa: F821
    notas: Mapped[list["Nota"]] = relationship(back_populates="user")  # noqa: F821
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")  # noqa: F821

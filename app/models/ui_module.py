"""
UI Module model for modular permission system.
This allows dynamic registration of frontend screens and their actions.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UIModule(Base):
    """
    Represents a UI module (screen/page) in the frontend.
    Each module has a set of actions that can be permitted.
    """

    __tablename__ = "ui_modules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Module identification
    codigo: Mapped[str] = mapped_column(String(50), nullable=False)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Frontend route
    ruta: Mapped[str] = mapped_column(String(200), nullable=False)
    icono: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Configuration
    orden: Mapped[int] = mapped_column(Integer, default=0)
    es_submodulo: Mapped[bool] = mapped_column(default=False)
    parent_code: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Available actions with metadata
    # Format: {
    #   "view": {"label": "Ver", "description": "Acceder a la pantalla"},
    #   "create": {"label": "Crear", "description": "Crear nuevos registros"},
    #   ...
    # }
    acciones: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Whether this is a system module (available to all accounts)
    es_sistema: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    account: Mapped["Account | None"] = relationship(back_populates="ui_modules")  # noqa: F821

    def __repr__(self) -> str:
        return f"<UIModule {self.codigo}>"


class RoleModulePermission(Base):
    """
    Junction table for Role-Module-Action permissions.
    Stores which actions a role can perform on each module.
    """

    __tablename__ = "role_module_permissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roles.id", ondelete="CASCADE"),
        index=True,
    )
    module_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ui_modules.id", ondelete="CASCADE"),
        index=True,
    )

    # List of allowed actions for this module (e.g., ["view", "create", "edit"])
    # Special value "*" means all actions
    acciones_permitidas: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    role: Mapped["Role"] = relationship(back_populates="module_permissions")  # noqa: F821
    module: Mapped["UIModule"] = relationship()  # noqa: F821

    def __repr__(self) -> str:
        return f"<RoleModulePermission role={self.role_id} module={self.module_id}>"

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    api_key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    auto_crear_campos: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    fields: Mapped[list["CustomField"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    records: Mapped[list["Record"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    leads: Mapped[list["Lead"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    lead_bases: Mapped[list["LeadBase"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    lotes: Mapped[list["Lote"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    webhooks: Mapped[list["Webhook"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    automations: Mapped[list["Automation"]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete-orphan"
    )
    sip_providers: Mapped[list["SipProvider"]] = relationship(  # noqa: F821
        cascade="all, delete-orphan"
    )
    pbx_nodes: Mapped[list["PbxNode"]] = relationship(  # noqa: F821
        cascade="all, delete-orphan"
    )
    agents: Mapped[list["Agent"]] = relationship(  # noqa: F821
        cascade="all, delete-orphan"
    )
    dispositions: Mapped[list["Disposition"]] = relationship(  # noqa: F821
        cascade="all, delete-orphan"
    )
    campaigns: Mapped[list["Campaign"]] = relationship(  # noqa: F821
        cascade="all, delete-orphan"
    )

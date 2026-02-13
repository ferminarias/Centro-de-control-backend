import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Automation(Base):
    """
    HubSpot-style automation: trigger → conditions → ordered actions.
    """

    __tablename__ = "automations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_tipo: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="lead_created | lead_updated | lead_moved | field_changed | lote_imported",
    )
    trigger_config: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True,
        comment='Extra config, e.g. {"base_id":"...","campo":"email"}',
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    account: Mapped["Account"] = relationship(back_populates="automations")  # noqa: F821
    conditions: Mapped[list["AutomationCondition"]] = relationship(
        back_populates="automation", cascade="all, delete-orphan",
        order_by="AutomationCondition.orden",
    )
    actions: Mapped[list["AutomationAction"]] = relationship(
        back_populates="automation", cascade="all, delete-orphan",
        order_by="AutomationAction.orden",
    )
    logs: Mapped[list["AutomationLog"]] = relationship(
        back_populates="automation", cascade="all, delete-orphan",
        order_by="AutomationLog.created_at.desc()",
    )


class AutomationCondition(Base):
    """Filter that must pass for the automation to execute."""

    __tablename__ = "automation_conditions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    automation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), index=True
    )
    campo: Mapped[str] = mapped_column(String(255), nullable=False)
    operador: Mapped[str] = mapped_column(
        String(30), nullable=False,
        comment="equals | not_equals | contains | not_contains | greater_than | less_than | is_empty | is_not_empty",
    )
    valor: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    orden: Mapped[int] = mapped_column(Integer, default=0)

    automation: Mapped["Automation"] = relationship(back_populates="conditions")


class AutomationAction(Base):
    """
    Action to execute when conditions pass.
    tipo: webhook | move_to_base | update_field | send_notification
    config: JSON with action-specific settings.
    """

    __tablename__ = "automation_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    automation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), index=True
    )
    tipo: Mapped[str] = mapped_column(
        String(50), nullable=False,
        comment="webhook | move_to_base | update_field | send_notification",
    )
    config: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict,
        comment='e.g. {"url":"https://...","method":"POST","headers":{}} or {"base_id":"..."}',
    )
    orden: Mapped[int] = mapped_column(Integer, default=0)

    automation: Mapped["Automation"] = relationship(back_populates="actions")


class AutomationLog(Base):
    """Execution log for an automation run."""

    __tablename__ = "automation_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    automation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("automations.id", ondelete="CASCADE"), index=True
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    trigger_evento: Mapped[str] = mapped_column(String(50), nullable=False)
    conditions_passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actions_result: Mapped[list | None] = mapped_column(
        JSONB, nullable=True,
        comment='[{"action_id":"...","tipo":"webhook","success":true,"detail":"200 OK"}]',
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    automation: Mapped["Automation"] = relationship(back_populates="logs")

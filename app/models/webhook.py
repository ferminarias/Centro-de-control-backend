import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Webhook(Base):
    """Outbound webhook: when an event fires in the system, POST to this URL."""

    __tablename__ = "webhooks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    eventos: Mapped[list] = mapped_column(
        JSONB, nullable=False, default=list,
        comment='e.g. ["lead_created","lead_moved","lote_imported"]',
    )
    headers_custom: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="Extra headers to send (e.g. Authorization)"
    )
    secret: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="HMAC-SHA256 signing secret"
    )
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    account: Mapped["Account"] = relationship(back_populates="webhooks")  # noqa: F821
    logs: Mapped[list["WebhookLog"]] = relationship(
        back_populates="webhook", cascade="all, delete-orphan",
        order_by="WebhookLog.created_at.desc()",
    )


class WebhookLog(Base):
    """Delivery attempt log for a webhook call."""

    __tablename__ = "webhook_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    webhook_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("webhooks.id", ondelete="CASCADE"), index=True
    )
    evento: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    webhook: Mapped["Webhook"] = relationship(back_populates="logs")

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TipificacionExterna(Base):
    __tablename__ = "tipificaciones_externas"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("leads.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    email: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="EMLMAIL del payload Neotel"
    )
    id_neotel: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="USUARIO del payload Neotel"
    )
    id_subresolucion: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="IdSubresolucion del payload Neotel"
    )
    raw_payload: Mapped[dict] = mapped_column(
        JSONB, nullable=False, comment="JSON completo recibido del webhook"
    )
    matched: Mapped[bool] = mapped_column(
        Boolean, default=False, comment="Si se encontró un lead con ese email"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="tipificaciones_externas")  # noqa: F821
    lead: Mapped["Lead | None"] = relationship(back_populates="tipificaciones_externas")  # noqa: F821

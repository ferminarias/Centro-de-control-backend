import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class RoutingRule(Base):
    __tablename__ = "routing_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    lead_base_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lead_bases.id", ondelete="CASCADE"), index=True
    )
    campo: Mapped[str] = mapped_column(String(255), nullable=False)
    operador: Mapped[str] = mapped_column(String(20), nullable=False)
    valor: Mapped[str] = mapped_column(String(500), nullable=False)
    prioridad: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    lead_base: Mapped["LeadBase"] = relationship(back_populates="routing_rules")  # noqa: F821

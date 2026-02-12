import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LeadBase(Base):
    __tablename__ = "lead_bases"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    es_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    account: Mapped["Account"] = relationship(back_populates="lead_bases")  # noqa: F821
    leads: Mapped[list["Lead"]] = relationship(back_populates="lead_base")  # noqa: F821
    routing_rules: Mapped[list["RoutingRule"]] = relationship(  # noqa: F821
        back_populates="lead_base", cascade="all, delete-orphan"
    )

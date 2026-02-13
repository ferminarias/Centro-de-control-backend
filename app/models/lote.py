import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Lote(Base):
    __tablename__ = "lotes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    lead_base_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lead_bases.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    total_leads: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    account: Mapped["Account"] = relationship(back_populates="lotes")  # noqa: F821
    lead_base: Mapped["LeadBase | None"] = relationship()  # noqa: F821
    leads: Mapped[list["Lead"]] = relationship(back_populates="lote")  # noqa: F821

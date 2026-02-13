import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    nombre: str
    lead_base_id: uuid.UUID | None = None
    base_nombre: str | None = None
    total_leads: int
    created_at: datetime


class LoteListResponse(BaseModel):
    items: list[LoteResponse]
    total: int


class LoteAssociateRequest(BaseModel):
    lead_base_id: uuid.UUID | None = None


class LoteAssociateResponse(BaseModel):
    lote_id: uuid.UUID
    lead_base_id: uuid.UUID | None = None
    leads_moved: int

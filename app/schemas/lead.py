import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    record_id: uuid.UUID
    lead_base_id: uuid.UUID | None = None
    base_nombre: str | None = None
    datos: dict[str, Any]
    created_at: datetime


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int

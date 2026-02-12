import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    datos: dict[str, Any]
    metadata_: dict[str, Any] | None
    created_at: datetime


class RecordListResponse(BaseModel):
    items: list[RecordResponse]
    total: int
    page: int
    page_size: int

import uuid

from pydantic import BaseModel


class IngestResponse(BaseModel):
    success: bool
    record_id: uuid.UUID
    lead_id: uuid.UUID
    unknown_fields: list[str]
    auto_create_enabled: bool
    fields_created: list[str] | None = None

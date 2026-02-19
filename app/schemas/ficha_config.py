import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FichaCampoConfig(BaseModel):
    key: str
    label: str
    visible: bool = True
    orden: int
    seccion: str = "datos"


class FichaConfigCreate(BaseModel):
    campania_id: uuid.UUID | None = None
    campos: list[FichaCampoConfig]


class FichaConfigUpdate(BaseModel):
    campos: list[FichaCampoConfig]


class FichaConfigResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    campania_id: uuid.UUID | None
    campos: list[dict]
    created_at: datetime
    updated_at: datetime


class AvailableFieldsResponse(BaseModel):
    fields: list[str]

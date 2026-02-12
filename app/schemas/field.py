import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.field import FieldType


class FieldCreate(BaseModel):
    nombre_campo: str
    tipo_dato: FieldType = FieldType.STRING
    descripcion: str | None = None
    es_requerido: bool = False


class FieldUpdate(BaseModel):
    tipo_dato: FieldType | None = None
    descripcion: str | None = None
    es_requerido: bool | None = None


class FieldResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    nombre_campo: str
    tipo_dato: FieldType
    descripcion: str | None
    es_requerido: bool
    created_at: datetime


class FieldListResponse(BaseModel):
    items: list[FieldResponse]
    total: int

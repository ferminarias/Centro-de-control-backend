import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AccountCreate(BaseModel):
    nombre: str
    auto_crear_campos: bool = True


class AccountUpdate(BaseModel):
    nombre: str | None = None
    activo: bool | None = None
    auto_crear_campos: bool | None = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    nombre: str
    api_key: str
    activo: bool
    auto_crear_campos: bool
    created_at: datetime
    updated_at: datetime


class AccountListResponse(BaseModel):
    items: list[AccountResponse]
    total: int

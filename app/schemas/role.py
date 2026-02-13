import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RoleCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    permisos: list[str] = []


class RoleUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    permisos: list[str] | None = None


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    nombre: str
    descripcion: str | None = None
    permisos: list[str]
    total_users: int = 0
    created_at: datetime


class RoleListResponse(BaseModel):
    items: list[RoleResponse]
    total: int

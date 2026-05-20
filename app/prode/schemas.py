import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProdeLoginRequest(BaseModel):
    email: str
    password: str


class ProdeUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    nombre: str
    apellido: str
    activo: bool
    created_at: datetime


class ProdeLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: ProdeUserResponse

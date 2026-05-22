import uuid
from datetime import datetime
from typing import Optional

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
    is_admin: bool
    must_change_password: bool
    created_at: datetime


class ProdeLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: ProdeUserResponse


class ProdeCreateUserRequest(BaseModel):
    email: str
    password: str
    nombre: str
    apellido: str
    is_admin: bool = False


class ProdeUpdateUserRequest(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    activo: Optional[bool] = None
    is_admin: Optional[bool] = None
    new_password: Optional[str] = None


class ProdeChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

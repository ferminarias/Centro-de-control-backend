import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    nombre: str
    apellido: str
    email: str
    username: str
    password: str
    role_id: uuid.UUID | None = None


class UserUpdate(BaseModel):
    nombre: str | None = None
    apellido: str | None = None
    email: str | None = None
    username: str | None = None
    password: str | None = None
    role_id: uuid.UUID | None = None
    activo: bool | None = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    nombre: str
    apellido: str
    email: str
    username: str
    role_id: uuid.UUID | None = None
    role_nombre: str | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int


class LoginRequest(BaseModel):
    username: str
    password: str
    cuenta_id: uuid.UUID


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

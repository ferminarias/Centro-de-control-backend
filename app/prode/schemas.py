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
    avatar_url: Optional[str] = None
    activo: bool
    is_admin: bool
    es_gerente: bool = False
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
    es_gerente: Optional[bool] = None
    new_password: Optional[str] = None


class ProdeChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


# ── Equipos ───────────────────────────────────────────────────────────────────

class EquipoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    codigo_iso: str
    grupo: str


# ── Partidos ──────────────────────────────────────────────────────────────────

class PrediccionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    partido_id: int
    goles_local: int
    goles_visitante: int
    puntos: Optional[int]
    updated_at: datetime


class PartidoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipo_local: Optional[EquipoResponse]
    equipo_visitante: Optional[EquipoResponse]
    fecha: datetime
    estadio: Optional[str]
    fase: str
    grupo: Optional[str]
    jornada: Optional[int]
    goles_local: Optional[int]
    goles_visitante: Optional[int]
    estado: str
    mi_prediccion: Optional[PrediccionResponse] = None


# ── Predicciones ──────────────────────────────────────────────────────────────

class PrediccionRequest(BaseModel):
    partido_id: int
    goles_local: int
    goles_visitante: int


class PrediccionConPartidoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    partido_id: int
    goles_local: int
    goles_visitante: int
    puntos: Optional[int]
    updated_at: datetime
    partido: PartidoResponse


# ── Tabla ─────────────────────────────────────────────────────────────────────

class TablaEntry(BaseModel):
    posicion: int
    user_id: str
    nombre: str
    apellido: str
    avatar_url: Optional[str] = None
    puntos: int
    exactos: int
    resultados: int
    predicciones: int


# ── Clubes (equipos de usuarios) ─────────────────────────────────────────────

class ClubCreate(BaseModel):
    nombre: str


class ClubMemberAdd(BaseModel):
    user_id: str


class ClubResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    gerente_id: uuid.UUID
    created_at: datetime


class ClubTablaEntry(BaseModel):
    posicion: int
    club_id: int
    nombre: str
    integrantes: int
    promedio: float
    total_puntos: int


# ── Sync ──────────────────────────────────────────────────────────────────────

class SyncResponse(BaseModel):
    partidos_creados: int
    partidos_actualizados: int
    predicciones_puntuadas: int
    total_partidos_api: int


class ResultadoManualRequest(BaseModel):
    goles_local: int
    goles_visitante: int

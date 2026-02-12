import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class LeadBaseCreate(BaseModel):
    nombre: str
    es_default: bool = False


class LeadBaseUpdate(BaseModel):
    nombre: str | None = None
    es_default: bool | None = None


class LeadBaseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    nombre: str
    es_default: bool
    created_at: datetime


class LeadBaseListResponse(BaseModel):
    items: list[LeadBaseResponse]
    total: int


class RoutingRuleCreate(BaseModel):
    campo: str
    operador: str
    valor: str
    prioridad: int = 0


class RoutingRuleUpdate(BaseModel):
    campo: str | None = None
    operador: str | None = None
    valor: str | None = None
    prioridad: int | None = None


class RoutingRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    lead_base_id: uuid.UUID
    campo: str
    operador: str
    valor: str
    prioridad: int
    created_at: datetime


class RoutingRuleListResponse(BaseModel):
    items: list[RoutingRuleResponse]
    total: int

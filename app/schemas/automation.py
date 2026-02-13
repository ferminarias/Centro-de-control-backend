import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Trigger / action type constants ────────────────────────────────────────

TRIGGER_TYPES = [
    "lead_created",
    "lead_updated",
    "lead_moved",
    "field_changed",
    "lote_imported",
]

ACTION_TYPES = [
    "webhook",
    "move_to_base",
    "update_field",
    "send_notification",
]

CONDITION_OPERATORS = [
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "greater_than",
    "less_than",
    "is_empty",
    "is_not_empty",
]


# ── Condition ──────────────────────────────────────────────────────────────

class ConditionCreate(BaseModel):
    campo: str
    operador: str
    valor: str = ""
    orden: int = 0


class ConditionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    campo: str
    operador: str
    valor: str
    orden: int


# ── Action ─────────────────────────────────────────────────────────────────

class ActionCreate(BaseModel):
    tipo: str
    config: dict = {}
    orden: int = 0


class ActionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tipo: str
    config: dict
    orden: int


# ── Automation CRUD ────────────────────────────────────────────────────────

class AutomationCreate(BaseModel):
    nombre: str
    descripcion: str | None = None
    trigger_tipo: str
    trigger_config: dict | None = None
    activo: bool = True
    conditions: list[ConditionCreate] = []
    actions: list[ActionCreate] = []


class AutomationUpdate(BaseModel):
    nombre: str | None = None
    descripcion: str | None = None
    trigger_tipo: str | None = None
    trigger_config: dict | None = None
    activo: bool | None = None


class AutomationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    nombre: str
    descripcion: str | None = None
    trigger_tipo: str
    trigger_config: dict | None = None
    activo: bool
    conditions: list[ConditionResponse] = []
    actions: list[ActionResponse] = []
    created_at: datetime
    updated_at: datetime


class AutomationListResponse(BaseModel):
    items: list[AutomationResponse]
    total: int


# ── Log ────────────────────────────────────────────────────────────────────

class AutomationLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    automation_id: uuid.UUID
    lead_id: uuid.UUID | None = None
    trigger_evento: str
    conditions_passed: bool
    actions_result: list | None = None
    error: str | None = None
    created_at: datetime


class AutomationLogListResponse(BaseModel):
    items: list[AutomationLogResponse]
    total: int


# ── Meta ───────────────────────────────────────────────────────────────────

class AutomationMetaResponse(BaseModel):
    trigger_types: list[str]
    action_types: list[str]
    condition_operators: list[str]

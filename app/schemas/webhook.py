import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Events ─────────────────────────────────────────────────────────────────

WEBHOOK_EVENTS = [
    "lead_created",
    "lead_updated",
    "lead_deleted",
    "lead_moved",
    "lote_imported",
    "lote_associated",
]


# ── Webhook CRUD ───────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    nombre: str
    url: str
    eventos: list[str]
    headers_custom: dict | None = None
    secret: str | None = None
    activo: bool = True


class WebhookUpdate(BaseModel):
    nombre: str | None = None
    url: str | None = None
    eventos: list[str] | None = None
    headers_custom: dict | None = None
    secret: str | None = None
    activo: bool | None = None


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    nombre: str
    url: str
    eventos: list[str]
    headers_custom: dict | None = None
    secret: str | None = None
    activo: bool
    created_at: datetime
    updated_at: datetime


class WebhookListResponse(BaseModel):
    items: list[WebhookResponse]
    total: int


# ── Webhook Log ────────────────────────────────────────────────────────────

class WebhookLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    webhook_id: uuid.UUID
    evento: str
    payload: dict
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None
    duration_ms: int | None = None
    created_at: datetime


class WebhookLogListResponse(BaseModel):
    items: list[WebhookLogResponse]
    total: int


# ── Test ───────────────────────────────────────────────────────────────────

class WebhookTestResponse(BaseModel):
    success: bool
    status_code: int | None = None
    response_body: str | None = None
    error: str | None = None
    duration_ms: int | None = None

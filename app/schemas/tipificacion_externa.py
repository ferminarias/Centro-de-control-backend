import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# --- Webhook payload (lo que envía Neotel) ---
class TipificacionExternaPayload(BaseModel):
    USUARIO: str = Field(..., description="ID del usuario en Neotel")
    EMLMAIL: EmailStr = Field(..., description="Email del lead")
    IdSubresolucion: str = Field(..., description="ID de subresolucion en Neotel")


# --- Response para una tipificación externa ---
class TipificacionExternaResponse(BaseModel):
    id: uuid.UUID
    cuenta_id: uuid.UUID
    lead_id: uuid.UUID | None = None
    email: str
    id_neotel: str
    id_subresolucion: str
    matched: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Lista paginada ---
class TipificacionExternaListResponse(BaseModel):
    items: list[TipificacionExternaResponse]
    total: int
    page: int
    page_size: int


# --- Respuesta del webhook ingest ---
class TipificacionExternaIngestResponse(BaseModel):
    success: bool
    tipificacion_id: uuid.UUID
    matched: bool
    lead_id: uuid.UUID | None = None


# --- Datos para evento SSE ---
class CentroControlSSEData(BaseModel):
    event: str = "nueva_tipificacion"
    data: TipificacionExternaResponse


# --- Respuesta del retry-match ---
class RetryMatchResponse(BaseModel):
    total_pendientes: int
    matched: int
    still_pending: int

"""
Pydantic schemas for Tipificacion and Subtipificacion management.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Subtipificacion Schemas
# ─────────────────────────────────────────────────────────────────────────────

class SubtipificacionBase(BaseModel):
    """Base schema for Subtipificacion."""
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str | None = Field(None, max_length=500)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    orden: int = Field(default=0, ge=0)
    activo: bool = True


class SubtipificacionCreate(SubtipificacionBase):
    """Schema for creating a Subtipificacion."""
    tipificacion_id: uuid.UUID


class SubtipificacionUpdate(BaseModel):
    """Schema for updating a Subtipificacion."""
    nombre: str | None = Field(None, min_length=1, max_length=100)
    descripcion: str | None = Field(None, max_length=500)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    orden: int | None = Field(None, ge=0)
    activo: bool | None = None


class SubtipificacionResponse(SubtipificacionBase):
    """Schema for Subtipificacion response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    tipificacion_id: uuid.UUID
    cuenta_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SubtipificacionSimpleResponse(BaseModel):
    """Simplified Subtipificacion response (for nested display)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    nombre: str
    color: str | None
    activo: bool


# ─────────────────────────────────────────────────────────────────────────────
# Tipificacion Schemas
# ─────────────────────────────────────────────────────────────────────────────

class TipificacionBase(BaseModel):
    """Base schema for Tipificacion."""
    nombre: str = Field(..., min_length=1, max_length=100)
    descripcion: str | None = Field(None, max_length=500)
    color: str = Field(default="#6B7280", pattern=r"^#[0-9A-Fa-f]{6}$")
    orden: int = Field(default=0, ge=0)
    activo: bool = True
    es_final: bool = False


class TipificacionCreate(TipificacionBase):
    """Schema for creating a Tipificacion."""
    subtipificaciones: list[SubtipificacionCreate] | None = None


class TipificacionUpdate(BaseModel):
    """Schema for updating a Tipificacion."""
    nombre: str | None = Field(None, min_length=1, max_length=100)
    descripcion: str | None = Field(None, max_length=500)
    color: str | None = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$")
    orden: int | None = Field(None, ge=0)
    activo: bool | None = None
    es_final: bool | None = None


class TipificacionResponse(TipificacionBase):
    """Schema for Tipificacion response."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    cuenta_id: uuid.UUID
    subtipificaciones: list[SubtipificacionResponse] = []
    total_subtipificaciones: int = 0
    total_leads: int = 0
    created_at: datetime
    updated_at: datetime


class TipificacionSimpleResponse(BaseModel):
    """Simplified Tipificacion response (for dropdowns)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    nombre: str
    color: str
    activo: bool
    es_final: bool


class TipificacionWithSubtipificacionesResponse(TipificacionBase):
    """Tipificacion with nested subtipificaciones."""
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    cuenta_id: uuid.UUID
    subtipificaciones: list[SubtipificacionResponse]
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# List Responses
# ─────────────────────────────────────────────────────────────────────────────

class TipificacionListResponse(BaseModel):
    """Schema for listing tipificaciones."""
    items: list[TipificacionResponse]
    total: int


class SubtipificacionListResponse(BaseModel):
    """Schema for listing subtipificaciones."""
    items: list[SubtipificacionResponse]
    total: int


# ─────────────────────────────────────────────────────────────────────────────
# Lead Tipification Update
# ─────────────────────────────────────────────────────────────────────────────

class LeadTipificacionUpdate(BaseModel):
    """Schema for updating a lead's tipificacion."""
    tipificacion_id: uuid.UUID | None = None
    subtipificacion_id: uuid.UUID | None = None
    
    @field_validator('subtipificacion_id')
    @classmethod
    def validate_subtipificacion(cls, v, info):
        """Validate that subtipificacion belongs to tipificacion if both provided."""
        # This validation is handled in the endpoint
        return v


# ─────────────────────────────────────────────────────────────────────────────
# Bulk Operations
# ─────────────────────────────────────────────────────────────────────────────

class BulkTipificacionUpdate(BaseModel):
    """Schema for bulk updating leads' tipificacion."""
    lead_ids: list[uuid.UUID]
    tipificacion_id: uuid.UUID | None = None
    subtipificacion_id: uuid.UUID | None = None

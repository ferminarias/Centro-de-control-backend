"""
Pydantic schemas for UI Module management.
"""
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ModuleAction(BaseModel):
    """Represents an action that can be performed on a module."""

    label: str
    description: str | None = None


class UIModuleBase(BaseModel):
    """Base schema for UI Module."""

    codigo: str
    nombre: str
    descripcion: str | None = None
    ruta: str
    icono: str | None = None
    orden: int = 0
    es_submodulo: bool = False
    parent_code: str | None = None
    acciones: dict[str, Any] = {}


class UIModuleCreate(UIModuleBase):
    """Schema for creating a new UI module."""

    es_sistema: bool = False


class UIModuleUpdate(BaseModel):
    """Schema for updating a UI module."""

    nombre: str | None = None
    descripcion: str | None = None
    ruta: str | None = None
    icono: str | None = None
    orden: int | None = None
    acciones: dict[str, Any] | None = None


class UIModuleResponse(UIModuleBase):
    """Schema for UI module response."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID | None
    es_sistema: bool
    created_at: datetime
    updated_at: datetime


class UIModuleListResponse(BaseModel):
    """Schema for listing UI modules."""

    items: list[UIModuleResponse]
    total: int


class ModulePermissionEntry(BaseModel):
    """Entry for a module's permission in a role."""

    module_id: uuid.UUID
    codigo: str
    nombre: str
    acciones_permitidas: list[str]


class RoleModulePermissionCreate(BaseModel):
    """Schema for creating role-module permissions."""

    module_id: uuid.UUID
    acciones_permitidas: list[str]


class RoleModulePermissionUpdate(BaseModel):
    """Schema for updating role-module permissions."""

    acciones_permitidas: list[str]


class SyncModulesRequest(BaseModel):
    """Schema for syncing modules from frontend registry."""

    modules: list[UIModuleCreate]


class UserPermissionsResponse(BaseModel):
    """Schema for user permissions response (includes both old and new format)."""

    role_id: uuid.UUID | None
    role_nombre: str | None
    # Legacy permissions (for backward compatibility)
    permisos: list[str]
    # New modular permissions
    modulos: dict[str, list[str]]  # { "leads": ["view", "create"], ... }


class ModuleActionInfo(BaseModel):
    """Action info with permission status."""

    code: str
    label: str
    description: str | None = None
    allowed: bool


class ModuleWithPermissions(BaseModel):
    """Module info with permission details."""

    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: str | None = None
    ruta: str
    icono: str | None = None
    orden: int
    es_submodulo: bool
    parent_code: str | None = None
    acciones: list[ModuleActionInfo]
    puede_ver: bool

"""
API endpoints for UI Module management.
Provides CRUD operations for modules and role permissions.
"""
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.models.account import Account
from app.models.role import Role
from app.models.ui_module import UIModule
from app.models.user import User
from app.schemas.ui_module import (
    ModuleActionInfo,
    ModulePermissionEntry,
    ModuleWithPermissions,
    RoleModulePermissionCreate,
    SyncModulesRequest,
    UIModuleListResponse,
    UIModuleResponse,
    UserPermissionsResponse,
)
from app.services.ui_module_service import UIModuleService

logger = logging.getLogger(__name__)
router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# Module Management (Admin only)
# ──────────────────────────────────────────────────────────────────────────────


@router.get(
    "/accounts/{account_id}/modules",
    response_model=UIModuleListResponse,
    summary="List UI modules for an account",
    dependencies=[Depends(require_permission("roles:read"))],
)
def list_modules(
    account_id: uuid.UUID,
    include_system: bool = True,
    db: Session = Depends(get_db),
) -> dict:
    """List all UI modules available for an account."""
    # Verify account exists
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    service = UIModuleService(db)
    modules = service.get_modules(cuenta_id=account_id, include_system=include_system)

    return {
        "items": modules,
        "total": len(modules),
    }


@router.post(
    "/accounts/{account_id}/modules/sync",
    response_model=UIModuleListResponse,
    summary="Sync modules from frontend registry",
    dependencies=[Depends(require_permission("roles:update"))],
)
def sync_modules(
    account_id: uuid.UUID,
    body: SyncModulesRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Synchronize modules from frontend registry to backend.

    Creates new modules, updates existing ones. Does not delete modules
    that are not in the request (soft sync).
    """
    # Verify account exists
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    service = UIModuleService(db)

    # Convert Pydantic models to dicts
    modules_data = [m.model_dump() for m in body.modules]

    modules = service.sync_modules(
        cuenta_id=account_id,
        modules_data=modules_data,
    )
    db.commit()

    logger.info("Synced %d modules for account %s", len(modules), account_id)

    return {
        "items": modules,
        "total": len(modules),
    }


@router.get(
    "/modules/{module_id}",
    response_model=UIModuleResponse,
    summary="Get module details",
    dependencies=[Depends(require_permission("roles:read"))],
)
def get_module(
    module_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> UIModule:
    """Get details of a specific UI module."""
    module = db.query(UIModule).filter(UIModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    return module


# ──────────────────────────────────────────────────────────────────────────────
# Role Permissions Management
# ──────────────────────────────────────────────────────────────────────────────


@router.get(
    "/roles/{role_id}/module-permissions",
    response_model=list[ModulePermissionEntry],
    summary="Get role's module permissions",
    dependencies=[Depends(require_permission("roles:read"))],
)
def get_role_module_permissions(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get all module permissions assigned to a role."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    service = UIModuleService(db)
    permissions = service.get_role_permissions(role_id)

    # Get module details for each permission
    result = []
    for module_code, actions in permissions.items():
        module = service.get_module_by_code(module_code, cuenta_id=role.cuenta_id)
        if module:
            result.append({
                "module_id": module.id,
                "codigo": module.codigo,
                "nombre": module.nombre,
                "acciones_permitidas": actions,
            })

    return result


@router.put(
    "/roles/{role_id}/module-permissions",
    response_model=ModulePermissionEntry,
    summary="Set role's permissions for a module",
    dependencies=[Depends(require_permission("roles:update"))],
)
def set_role_module_permissions(
    role_id: uuid.UUID,
    body: RoleModulePermissionCreate,
    db: Session = Depends(get_db),
) -> dict:
    """Set permissions for a role on a specific module."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Verify module exists
    module = db.query(UIModule).filter(UIModule.id == body.module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    # Validate actions against module's available actions
    valid_actions = set(module.acciones.keys()) | {"*"}
    invalid_actions = [a for a in body.acciones_permitidas if a not in valid_actions]
    if invalid_actions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid actions: {', '.join(invalid_actions)}. "
            f"Valid actions: {', '.join(valid_actions)}",
        )

    service = UIModuleService(db)
    perm = service.set_role_permissions(
        role_id=role_id,
        module_id=body.module_id,
        acciones_permitidas=body.acciones_permitidas,
    )
    db.commit()

    logger.info(
        "Updated permissions for role %s on module %s: %s",
        role_id,
        module.codigo,
        body.acciones_permitidas,
    )

    return {
        "module_id": module.id,
        "codigo": module.codigo,
        "nombre": module.nombre,
        "acciones_permitidas": perm.acciones_permitidas,
    }


@router.delete(
    "/roles/{role_id}/module-permissions/{module_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove role's permissions for a module",
    dependencies=[Depends(require_permission("roles:update"))],
)
def delete_role_module_permissions(
    role_id: uuid.UUID,
    module_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    """Remove all permissions for a role on a specific module."""
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    service = UIModuleService(db)
    deleted = service.delete_role_permissions(role_id, module_id)
    db.commit()

    if not deleted:
        raise HTTPException(status_code=404, detail="Permission not found")

    logger.info("Removed permissions for role %s on module %s", role_id, module_id)


# ──────────────────────────────────────────────────────────────────────────────
# Current User Permissions
# ──────────────────────────────────────────────────────────────────────────────


@router.get(
    "/auth/me/permissions",
    response_model=UserPermissionsResponse,
    summary="Get current user's permissions (legacy + modular)",
)
def get_my_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get current user's permissions including both legacy and modular formats.

    - `permisos`: Legacy flat permission strings (e.g., ["leads:read", "users:create"])
    - `modulos`: New modular permissions (e.g., {"leads": ["view", "create"]})
    """
    service = UIModuleService(db)
    perms = service.get_user_permissions(current_user.role_id)

    # Get role name
    role_nombre = None
    if current_user.role_id:
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role:
            role_nombre = role.nombre

    return {
        "role_id": current_user.role_id,
        "role_nombre": role_nombre,
        "permisos": perms["permisos"],
        "modulos": perms["modulos"],
    }


@router.get(
    "/auth/me/modules",
    response_model=list[ModuleWithPermissions],
    summary="Get modules accessible to current user with permission details",
)
def get_my_modules(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    """Get all modules that the current user has access to, with detailed permission info."""
    service = UIModuleService(db)

    # Get all modules for the account
    modules = service.get_modules(
        cuenta_id=current_user.cuenta_id,
        include_system=True,
    )

    # Get user's permissions
    user_perms = service.get_user_permissions(current_user.role_id)
    allowed_modules = user_perms.get("modulos", {})

    result = []
    for module in modules:
        module_perms = allowed_modules.get(module.codigo, [])
        can_view = "view" in module_perms or "*" in module_perms

        # Build action info list
        actions = []
        for action_code, action_info in module.acciones.items():
            actions.append({
                "code": action_code,
                "label": action_info.get("label", action_code),
                "description": action_info.get("description"),
                "allowed": action_code in module_perms or "*" in module_perms,
            })

        result.append({
            "id": module.id,
            "codigo": module.codigo,
            "nombre": module.nombre,
            "descripcion": module.descripcion,
            "ruta": module.ruta,
            "icono": module.icono,
            "orden": module.orden,
            "es_submodulo": module.es_submodulo,
            "parent_code": module.parent_code,
            "acciones": actions,
            "puede_ver": can_view,
        })

    return result


# ──────────────────────────────────────────────────────────────────────────────
# System Initialization (Admin only)
# ──────────────────────────────────────────────────────────────────────────────


@router.post(
    "/admin/modules/initialize",
    response_model=UIModuleListResponse,
    summary="Initialize system modules (admin only)",
)
def initialize_system_modules(
    db: Session = Depends(get_db),
) -> dict:
    """Initialize default system modules. Should be called once during setup."""
    service = UIModuleService(db)
    modules = service.initialize_system_modules()
    db.commit()

    logger.info("Initialized %d system modules", len(modules))

    return {
        "items": modules,
        "total": len(modules),
    }

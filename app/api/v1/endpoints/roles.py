import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import ALL_PERMISSIONS
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.role import Role
from app.models.user import User
from app.schemas.role import RoleCreate, RoleListResponse, RoleResponse, RoleUpdate

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_admin_key)])


def _validate_permisos(permisos: list[str]) -> None:
    invalid = [p for p in permisos if p not in ALL_PERMISSIONS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid permissions: {', '.join(invalid)}. "
            f"Valid permissions: {', '.join(ALL_PERMISSIONS)}",
        )


@router.post(
    "/accounts/{account_id}/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a role",
)
def create_role(
    account_id: uuid.UUID,
    body: RoleCreate,
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    _validate_permisos(body.permisos)

    role = Role(
        cuenta_id=account_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        permisos=body.permisos,
    )
    db.add(role)
    db.commit()
    db.refresh(role)

    logger.info("Role '%s' created for account %s", role.nombre, account_id)

    return {
        "id": role.id,
        "cuenta_id": role.cuenta_id,
        "nombre": role.nombre,
        "descripcion": role.descripcion,
        "permisos": role.permisos,
        "total_users": 0,
        "created_at": role.created_at,
    }


@router.get(
    "/accounts/{account_id}/roles",
    response_model=RoleListResponse,
    summary="List roles for an account",
)
def list_roles(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    roles = (
        db.query(Role)
        .filter(Role.cuenta_id == account_id)
        .order_by(Role.created_at)
        .all()
    )

    items = []
    for role in roles:
        user_count = db.query(User).filter(User.role_id == role.id).count()
        items.append({
            "id": role.id,
            "cuenta_id": role.cuenta_id,
            "nombre": role.nombre,
            "descripcion": role.descripcion,
            "permisos": role.permisos,
            "total_users": user_count,
            "created_at": role.created_at,
        })

    return {"items": items, "total": len(items)}


@router.get(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Get role details",
)
def get_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    user_count = db.query(User).filter(User.role_id == role.id).count()

    return {
        "id": role.id,
        "cuenta_id": role.cuenta_id,
        "nombre": role.nombre,
        "descripcion": role.descripcion,
        "permisos": role.permisos,
        "total_users": user_count,
        "created_at": role.created_at,
    }


@router.put(
    "/roles/{role_id}",
    response_model=RoleResponse,
    summary="Update a role",
)
def update_role(
    role_id: uuid.UUID,
    body: RoleUpdate,
    db: Session = Depends(get_db),
) -> dict:
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if body.nombre is not None:
        role.nombre = body.nombre
    if body.descripcion is not None:
        role.descripcion = body.descripcion
    if body.permisos is not None:
        _validate_permisos(body.permisos)
        role.permisos = body.permisos

    db.commit()
    db.refresh(role)

    user_count = db.query(User).filter(User.role_id == role.id).count()

    return {
        "id": role.id,
        "cuenta_id": role.cuenta_id,
        "nombre": role.nombre,
        "descripcion": role.descripcion,
        "permisos": role.permisos,
        "total_users": user_count,
        "created_at": role.created_at,
    }


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a role",
)
def delete_role(
    role_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Check if any users still use this role
    user_count = db.query(User).filter(User.role_id == role_id).count()
    if user_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete role: {user_count} user(s) still assigned to it",
        )

    db.delete(role)
    db.commit()
    logger.info("Role '%s' deleted", role.nombre)


@router.get(
    "/permissions",
    summary="List all available permissions",
)
def list_permissions() -> dict:
    """Returns all available permission strings that can be assigned to roles."""
    grouped: dict[str, list[str]] = {}
    for perm in ALL_PERMISSIONS:
        resource, action = perm.split(":")
        grouped.setdefault(resource, []).append(action)

    return {"permissions": ALL_PERMISSIONS, "grouped": grouped}

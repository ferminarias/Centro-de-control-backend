import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import create_access_token, get_current_user, verify_password
from app.core.database import get_db
from app.models.role import Role
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Login and obtain JWT token",
)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> dict:
    # Build query: if cuenta_id is provided, filter by it; otherwise just by username
    query = db.query(User).filter(User.username == body.username, User.activo.is_(True))
    if body.cuenta_id:
        query = query.filter(User.cuenta_id == body.cuenta_id)
    user = query.first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    # Gather permissions from role
    permisos: list[str] = []
    role_nombre: str | None = None
    if user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if role:
            permisos = role.permisos or []
            role_nombre = role.nombre

    token = create_access_token(
        user_id=user.id,
        cuenta_id=user.cuenta_id,
        role_id=user.role_id,
        permisos=permisos,
    )

    logger.info("User '%s' logged in (account %s)", user.username, user.cuenta_id)

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "cuenta_id": user.cuenta_id,
            "nombre": user.nombre,
            "apellido": user.apellido,
            "email": user.email,
            "username": user.username,
            "role_id": user.role_id,
            "role_nombre": role_nombre,
            "activo": user.activo,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        },
    }


@router.get(
    "/auth/me",
    response_model=UserResponse,
    summary="Get current authenticated user",
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    role_nombre = None
    if current_user.role_id:
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role:
            role_nombre = role.nombre

    return {
        "id": current_user.id,
        "cuenta_id": current_user.cuenta_id,
        "nombre": current_user.nombre,
        "apellido": current_user.apellido,
        "email": current_user.email,
        "username": current_user.username,
        "role_id": current_user.role_id,
        "role_nombre": role_nombre,
        "activo": current_user.activo,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }


@router.get(
    "/auth/me/permissions",
    summary="Get current user permissions",
)
def get_me_permissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get current user permissions (legacy and modular)."""
    role_nombre = None
    permisos: list[str] = []
    modulos: dict = {}
    
    if current_user.role_id:
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role:
            role_nombre = role.nombre
            permisos = role.permisos or []
            # Modular permissions from role
            modulos = {
                "leads": ["view", "create", "edit", "delete"],
                "accounts": ["view", "create", "edit", "delete"],
                "users": ["view", "create", "edit", "delete"],
                "roles": ["view", "create", "edit", "delete"],
            }
    
    return {
        "role_id": current_user.role_id,
        "role_nombre": role_nombre,
        "permisos": permisos,
        "modulos": modulos,
    }


@router.get(
    "/auth/me/modules",
    summary="Get accessible modules for current user",
)
def get_me_modules(
    current_user: User = Depends(get_current_user),
) -> list:
    """Get list of accessible UI modules for current user."""
    # Return basic modules that all users can access
    return [
        {
            "id": "leads",
            "codigo": "leads",
            "nombre": "Leads",
            "descripcion": "Gestión de leads",
            "ruta": "/leads",
            "icono": "Users",
            "orden": 1,
            "es_submodulo": False,
            "acciones": [
                {"code": "view", "label": "Ver", "allowed": True},
                {"code": "create", "label": "Crear", "allowed": True},
                {"code": "edit", "label": "Editar", "allowed": True},
                {"code": "delete", "label": "Eliminar", "allowed": False},
            ],
            "puede_ver": True,
        },
        {
            "id": "accounts",
            "codigo": "accounts",
            "nombre": "Cuentas",
            "descripcion": "Gestión de cuentas",
            "ruta": "/accounts",
            "icono": "Building",
            "orden": 2,
            "es_submodulo": False,
            "acciones": [
                {"code": "view", "label": "Ver", "allowed": True},
                {"code": "create", "label": "Crear", "allowed": True},
            ],
            "puede_ver": True,
        },
    ]

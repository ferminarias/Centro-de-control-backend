import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_current_user,
    verify_password,
)
from app.core.database import get_db
from app.core.rate_limiter import rate_limit
from app.models.role import Role
from app.models.ui_module import RoleModulePermission, UIModule
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse, UserResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/auth/login",
    response_model=LoginResponse,
    summary="Login and obtain JWT token",
)
@rate_limit(5, "minute")  # 5 attempts per minute
def login(
    request: Request,
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> dict:
    try:
        # Build query: if cuenta_id is provided, filter by it; otherwise just by username
        query = db.query(User).filter(User.username == body.username, User.activo.is_(True))
        if body.cuenta_id:
            query = query.filter(User.cuenta_id == body.cuenta_id)
        user = query.first()
        
        if not user:
            logger.warning("Login failed: user '%s' not found", body.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
        
        if not verify_password(body.password, user.password_hash):
            logger.warning("Login failed: invalid password for user '%s'", body.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Unexpected error during login: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during login",
        )

    # Gather permissions from role
    permisos: list[str] = []
    role_nombre: str | None = None
    if user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if role:
            permisos = role.permisos or []
            role_nombre = role.nombre

    access_token = create_access_token(
        user_id=user.id,
        cuenta_id=user.cuenta_id,
        role_id=user.role_id,
        permisos=permisos,
    )
    refresh_token = create_refresh_token(user_id=user.id, cuenta_id=user.cuenta_id)

    logger.info("User '%s' logged in (account %s)", user.username, user.cuenta_id)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
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
    db: Session = Depends(get_db),
) -> list:
    """Get UI modules accessible to the current user based on their role."""
    # Fetch system modules + account-specific modules
    modules = (
        db.query(UIModule)
        .filter(
            (UIModule.es_sistema.is_(True)) | (UIModule.cuenta_id == current_user.cuenta_id)
        )
        .order_by(UIModule.orden)
        .all()
    )

    if not modules:
        return []

    # Get role permissions if user has a role
    allowed_actions_by_module: dict[str, list[str]] = {}
    is_superadmin = False
    if current_user.role_id:
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role and role.permisos and "*" in role.permisos:
            is_superadmin = True
        if not is_superadmin:
            perms = (
                db.query(RoleModulePermission)
                .filter(RoleModulePermission.role_id == current_user.role_id)
                .all()
            )
            for p in perms:
                allowed_actions_by_module[str(p.module_id)] = p.acciones_permitidas

    result = []
    for mod in modules:
        module_id_str = str(mod.id)
        if is_superadmin:
            allowed = list(mod.acciones.keys()) if mod.acciones else []
        else:
            allowed = allowed_actions_by_module.get(module_id_str, [])
            # "*" means all actions
            if "*" in allowed:
                allowed = list(mod.acciones.keys()) if mod.acciones else []

        puede_ver = "view" in allowed or is_superadmin

        acciones_out = []
        for code, meta in (mod.acciones or {}).items():
            acciones_out.append({
                "code": code,
                "label": meta.get("label", code) if isinstance(meta, dict) else code,
                "allowed": code in allowed or is_superadmin,
            })

        result.append({
            "id": str(mod.id),
            "codigo": mod.codigo,
            "nombre": mod.nombre,
            "descripcion": mod.descripcion,
            "ruta": mod.ruta,
            "icono": mod.icono,
            "orden": mod.orden,
            "es_submodulo": mod.es_submodulo,
            "parent_code": mod.parent_code,
            "acciones": acciones_out,
            "puede_ver": puede_ver,
        })

    return result


@router.post(
    "/auth/refresh",
    summary="Refresh access token using refresh token",
)
def refresh_access_token(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db),
) -> dict:
    """Exchange a valid refresh token for a new access token."""
    data = decode_refresh_token(credentials.credentials)

    user = db.query(User).filter(User.id == data["sub"], User.activo.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    permisos: list[str] = []
    if user.role_id:
        role = db.query(Role).filter(Role.id == user.role_id).first()
        if role:
            permisos = role.permisos or []

    access_token = create_access_token(
        user_id=user.id,
        cuenta_id=user.cuenta_id,
        role_id=user.role_id,
        permisos=permisos,
    )

    return {"access_token": access_token, "token_type": "bearer"}

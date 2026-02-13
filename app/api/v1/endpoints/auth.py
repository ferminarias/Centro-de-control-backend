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
    user = (
        db.query(User)
        .filter(
            User.username == body.username,
            User.cuenta_id == body.cuenta_id,
            User.activo.is_(True),
        )
        .first()
    )
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

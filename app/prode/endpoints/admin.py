import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.prode.auth import get_current_prode_user, hash_password
from app.prode.models import ProdeUser
from app.prode.schemas import (
    ProdeCreateUserRequest,
    ProdeUpdateUserRequest,
    ProdeUserResponse,
)

router = APIRouter(tags=["Prode - Admin"])


def _verify_admin_key(x_admin_key: str = Header(...)):
    if not settings.ADMIN_API_KEY or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clave admin inválida")


def _require_admin(current_user: ProdeUser = Depends(get_current_prode_user)) -> ProdeUser:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requieren permisos de administrador")
    return current_user


@router.post(
    "/admin/users",
    response_model=ProdeUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario Prode",
    dependencies=[Depends(_require_admin)],
)
def create_prode_user(body: ProdeCreateUserRequest, db: Session = Depends(get_db)) -> ProdeUser:
    if db.query(ProdeUser).filter(ProdeUser.email == body.email.lower().strip()).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    user = ProdeUser(
        email=body.email.lower().strip(),
        nombre=body.nombre,
        apellido=body.apellido,
        password_hash=hash_password(body.password),
        is_admin=body.is_admin,
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/admin/promote",
    response_model=ProdeUserResponse,
    summary="Promover usuario a admin (admin key)",
    dependencies=[Depends(_verify_admin_key)],
)
def promote_to_admin(body: dict, db: Session = Depends(get_db)) -> ProdeUser:
    email = body.get("email", "").lower().strip()
    user = db.query(ProdeUser).filter(ProdeUser.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    user.is_admin = True
    user.must_change_password = False
    db.commit()
    db.refresh(user)
    return user


@router.get(
    "/admin/users",
    response_model=list[ProdeUserResponse],
    summary="Listar usuarios Prode",
    dependencies=[Depends(_require_admin)],
)
def list_prode_users(db: Session = Depends(get_db)) -> list[ProdeUser]:
    return db.query(ProdeUser).order_by(ProdeUser.created_at.desc()).all()


@router.patch(
    "/admin/users/{user_id}",
    response_model=ProdeUserResponse,
    summary="Actualizar usuario Prode",
    dependencies=[Depends(_require_admin)],
)
def update_prode_user(
    user_id: uuid.UUID,
    body: ProdeUpdateUserRequest,
    db: Session = Depends(get_db),
) -> ProdeUser:
    user = db.query(ProdeUser).filter(ProdeUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    if body.nombre is not None:
        user.nombre = body.nombre
    if body.apellido is not None:
        user.apellido = body.apellido
    if body.activo is not None:
        user.activo = body.activo
    if body.is_admin is not None:
        user.is_admin = body.is_admin
    if body.new_password is not None:
        user.password_hash = hash_password(body.new_password)
        user.must_change_password = True

    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/admin/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar usuario Prode",
    dependencies=[Depends(_require_admin)],
)
def delete_prode_user(user_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    user = db.query(ProdeUser).filter(ProdeUser.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")
    db.delete(user)
    db.commit()

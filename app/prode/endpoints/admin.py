import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.prode.auth import get_current_prode_user, hash_password
from app.prode.models import ProdeEquipo, ProdePartido, ProdeUser
from app.prode.schemas import (
    ProdeCreateUserRequest,
    ProdeUpdateUserRequest,
    ProdeUserResponse,
    ResultadoManualRequest,
    SyncResponse,
)
from app.prode.services.sync import apply_resultado_manual, sync_wc_fixtures

router = APIRouter(tags=["Prode - Admin"])


def _verify_admin_key(x_admin_key: str = Header(...)):
    if not settings.ADMIN_API_KEY or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clave admin inválida")


def _require_admin(current_user: ProdeUser = Depends(get_current_prode_user)) -> ProdeUser:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requieren permisos de administrador")
    return current_user


# ── Users CRUD ────────────────────────────────────────────────────────────────

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


# ── Sync & Results ────────────────────────────────────────────────────────────

@router.post(
    "/admin/sync",
    response_model=SyncResponse,
    summary="Sincronizar fixture y resultados desde football-data.org",
    dependencies=[Depends(_require_admin)],
)
def sync_fixtures(db: Session = Depends(get_db)) -> dict:
    api_key = settings.FOOTBALL_DATA_API_KEY if hasattr(settings, "FOOTBALL_DATA_API_KEY") else None
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FOOTBALL_DATA_API_KEY no configurada",
        )
    try:
        result = sync_wc_fixtures(db, api_key)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error al sincronizar: {e}",
        )
    return result


@router.get(
    "/admin/diagnostico",
    summary="Estado del DB: equipos, partidos y partidos sin equipos asignados",
    dependencies=[Depends(_require_admin)],
)
def diagnostico(db: Session = Depends(get_db)) -> dict:
    total_equipos = db.query(func.count(ProdeEquipo.id)).scalar()
    total_partidos = db.query(func.count(ProdePartido.id)).scalar()
    sin_local = db.query(func.count(ProdePartido.id)).filter(ProdePartido.equipo_local_id.is_(None)).scalar()
    sin_visitante = db.query(func.count(ProdePartido.id)).filter(ProdePartido.equipo_visitante_id.is_(None)).scalar()

    sample_equipos = (
        db.query(ProdeEquipo.nombre, ProdeEquipo.nombre_api, ProdeEquipo.codigo_iso, ProdeEquipo.api_id)
        .order_by(ProdeEquipo.id)
        .limit(10)
        .all()
    )

    return {
        "total_equipos": total_equipos,
        "total_partidos": total_partidos,
        "partidos_sin_equipo_local": sin_local,
        "partidos_sin_equipo_visitante": sin_visitante,
        "sample_equipos": [
            {"nombre": e.nombre, "nombre_api": e.nombre_api, "codigo_iso": e.codigo_iso, "api_id": e.api_id}
            for e in sample_equipos
        ],
    }


@router.patch(
    "/admin/partidos/{partido_id}/resultado",
    summary="Ingresar resultado manual de un partido",
    dependencies=[Depends(_require_admin)],
)
def set_resultado_manual(
    partido_id: int,
    body: ResultadoManualRequest,
    db: Session = Depends(get_db),
) -> dict:
    partido = db.query(ProdePartido).filter(ProdePartido.id == partido_id).first()
    if not partido:
        raise HTTPException(status_code=404, detail="Partido no encontrado")
    if body.goles_local < 0 or body.goles_visitante < 0:
        raise HTTPException(status_code=422, detail="Los goles no pueden ser negativos")

    pts_updated = apply_resultado_manual(db, partido, body.goles_local, body.goles_visitante)
    return {"predicciones_puntuadas": pts_updated}

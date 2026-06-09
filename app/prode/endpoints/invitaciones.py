import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.prode.auth import get_current_prode_user, hash_password
from app.prode.models import ProdeInvitacion, ProdeRegistroPendiente, ProdeUser
from app.prode.schemas import (
    InvitacionResponse,
    ProdeUserResponse,
    RegistroConInvitacionRequest,
    RegistroPendienteResponse,
)

router = APIRouter(tags=["Prode - Invitaciones"])


def _require_admin(current_user: ProdeUser = Depends(get_current_prode_user)) -> ProdeUser:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requieren permisos de administrador")
    return current_user


# ── Admin: gestión de links ────────────────────────────────────────────────────

@router.post(
    "/admin/invitaciones",
    response_model=InvitacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generar link de invitación",
)
def crear_invitacion(
    admin: ProdeUser = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> ProdeInvitacion:
    inv = ProdeInvitacion(token=uuid.uuid4(), creado_por=admin.id)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return inv


@router.get(
    "/admin/invitaciones",
    response_model=list[InvitacionResponse],
    summary="Listar links de invitación",
)
def listar_invitaciones(
    _: ProdeUser = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> list[ProdeInvitacion]:
    return db.query(ProdeInvitacion).order_by(ProdeInvitacion.created_at.desc()).all()


@router.delete(
    "/admin/invitaciones/{token}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revocar link de invitación",
)
def revocar_invitacion(
    token: uuid.UUID,
    _: ProdeUser = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> None:
    inv = db.query(ProdeInvitacion).filter(ProdeInvitacion.token == token).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitación no encontrada")
    inv.activo = False
    db.commit()


# ── Admin: gestión de solicitudes pendientes ───────────────────────────────────

@router.get(
    "/admin/pendientes",
    response_model=list[RegistroPendienteResponse],
    summary="Listar solicitudes de registro pendientes",
)
def listar_pendientes(
    _: ProdeUser = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> list[ProdeRegistroPendiente]:
    return (
        db.query(ProdeRegistroPendiente)
        .filter(ProdeRegistroPendiente.estado == "pendiente")
        .order_by(ProdeRegistroPendiente.created_at.asc())
        .all()
    )


@router.post(
    "/admin/pendientes/{registro_id}/aceptar",
    response_model=ProdeUserResponse,
    summary="Aceptar solicitud y crear usuario",
)
def aceptar_registro(
    registro_id: uuid.UUID,
    _: ProdeUser = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> ProdeUser:
    registro = db.query(ProdeRegistroPendiente).filter(ProdeRegistroPendiente.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada")
    if registro.estado != "pendiente":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La solicitud ya fue procesada")

    if db.query(ProdeUser).filter(ProdeUser.email == registro.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    user = ProdeUser(
        email=registro.email,
        nombre=registro.nombre,
        apellido=registro.apellido,
        password_hash=registro.password_hash,
        must_change_password=False,
        activo=True,
        is_admin=False,
    )
    db.add(user)
    registro.estado = "aceptado"
    db.commit()
    db.refresh(user)
    return user


@router.post(
    "/admin/pendientes/{registro_id}/rechazar",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Rechazar solicitud de registro",
)
def rechazar_registro(
    registro_id: uuid.UUID,
    _: ProdeUser = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> None:
    registro = db.query(ProdeRegistroPendiente).filter(ProdeRegistroPendiente.id == registro_id).first()
    if not registro:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Solicitud no encontrada")
    if registro.estado != "pendiente":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="La solicitud ya fue procesada")
    registro.estado = "rechazado"
    db.commit()


# ── Público: validar token + registrarse ──────────────────────────────────────

@router.get(
    "/auth/invitacion/{token}",
    summary="Validar token de invitación (público)",
)
def validar_invitacion(token: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    inv = db.query(ProdeInvitacion).filter(
        ProdeInvitacion.token == token,
        ProdeInvitacion.activo.is_(True),
    ).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link de invitación inválido o expirado")
    return {"valid": True}


@router.post(
    "/auth/registro",
    response_model=RegistroPendienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrarse con link de invitación (público)",
)
def registrarse(body: RegistroConInvitacionRequest, db: Session = Depends(get_db)) -> ProdeRegistroPendiente:
    inv = db.query(ProdeInvitacion).filter(
        ProdeInvitacion.token == body.token,
        ProdeInvitacion.activo.is_(True),
    ).first()
    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link de invitación inválido o expirado")

    email = body.email.lower().strip()

    if db.query(ProdeUser).filter(ProdeUser.email == email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    if db.query(ProdeRegistroPendiente).filter(
        ProdeRegistroPendiente.email == email,
        ProdeRegistroPendiente.estado == "pendiente",
    ).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Ya existe una solicitud pendiente con ese email")

    if len(body.password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="La contraseña debe tener al menos 8 caracteres")

    registro = ProdeRegistroPendiente(
        id=uuid.uuid4(),
        email=email,
        nombre=body.nombre.strip(),
        apellido=body.apellido.strip(),
        password_hash=hash_password(body.password),
        invitacion_token=inv.token,
        estado="pendiente",
    )
    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro

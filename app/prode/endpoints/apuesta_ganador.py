from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.prode.auth import get_current_prode_user
from app.prode.models import ProdeApuestaGanador, ProdeEquipo, ProdeUser
from app.prode.schemas import (
    ApuestaGanadorAdminEntry,
    ApuestaGanadorRequest,
    ApuestaGanadorResponse,
    EquipoResponse,
    GanadorMundialRequest,
)

router = APIRouter(tags=["Prode - Apuesta Ganador"])

DEADLINE = datetime(2026, 6, 28, 23, 59, 59, tzinfo=timezone.utc)
PUNTOS_GANADOR = 25


def _require_admin(current_user: ProdeUser = Depends(get_current_prode_user)) -> ProdeUser:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requieren permisos de administrador")
    return current_user


@router.get("/apuesta-ganador/equipos", response_model=list[EquipoResponse])
def listar_equipos(db: Session = Depends(get_db), _: ProdeUser = Depends(get_current_prode_user)) -> list[ProdeEquipo]:
    return db.query(ProdeEquipo).order_by(ProdeEquipo.nombre).all()


@router.get("/apuesta-ganador", response_model=ApuestaGanadorResponse | None)
def get_mi_apuesta(
    current_user: ProdeUser = Depends(get_current_prode_user),
    db: Session = Depends(get_db),
) -> ProdeApuestaGanador | None:
    return db.query(ProdeApuestaGanador).filter(ProdeApuestaGanador.user_id == current_user.id).first()


@router.post("/apuesta-ganador", response_model=ApuestaGanadorResponse, status_code=status.HTTP_200_OK)
def guardar_apuesta(
    body: ApuestaGanadorRequest,
    current_user: ProdeUser = Depends(get_current_prode_user),
    db: Session = Depends(get_db),
) -> ProdeApuestaGanador:
    if datetime.now(timezone.utc) > DEADLINE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="El plazo para apostar ya cerró (15 de junio)")

    equipo = db.query(ProdeEquipo).filter(ProdeEquipo.id == body.equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

    apuesta = db.query(ProdeApuestaGanador).filter(ProdeApuestaGanador.user_id == current_user.id).first()
    if apuesta:
        apuesta.equipo_id = body.equipo_id
    else:
        apuesta = ProdeApuestaGanador(user_id=current_user.id, equipo_id=body.equipo_id, puntos=0)
        db.add(apuesta)
    db.commit()
    db.refresh(apuesta)
    return apuesta


@router.get("/admin/apuesta-ganador", response_model=list[ApuestaGanadorAdminEntry])
def listar_apuestas_admin(
    _: ProdeUser = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> list:
    rows = (
        db.query(ProdeApuestaGanador, ProdeUser)
        .join(ProdeUser, ProdeUser.id == ProdeApuestaGanador.user_id)
        .filter(ProdeUser.activo.is_(True))
        .order_by(ProdeUser.apellido)
        .all()
    )
    result = []
    for apuesta, user in rows:
        result.append(ApuestaGanadorAdminEntry(
            user_id=user.id,
            nombre=user.nombre,
            apellido=user.apellido,
            equipo_id=apuesta.equipo_id,
            equipo=EquipoResponse.model_validate(apuesta.equipo),
            puntos=apuesta.puntos,
        ))
    return result


@router.post("/admin/apuesta-ganador/resultado", status_code=status.HTTP_200_OK)
def declarar_ganador(
    body: GanadorMundialRequest,
    _: ProdeUser = Depends(_require_admin),
    db: Session = Depends(get_db),
) -> dict:
    equipo = db.query(ProdeEquipo).filter(ProdeEquipo.id == body.equipo_id).first()
    if not equipo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Equipo no encontrado")

    apuestas = db.query(ProdeApuestaGanador).all()
    acertaron = 0
    for apuesta in apuestas:
        new_pts = PUNTOS_GANADOR if apuesta.equipo_id == body.equipo_id else 0
        if apuesta.puntos != new_pts:
            apuesta.puntos = new_pts
            if new_pts > 0:
                acertaron += 1
    db.commit()

    try:
        from app.prode import events as _events
        _events.broadcast("tabla_updated")
    except Exception:
        pass

    return {"ganador": equipo.nombre, "acertaron": acertaron}

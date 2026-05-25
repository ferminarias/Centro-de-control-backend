from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.prode.auth import get_current_prode_user
from app.prode.models import ProdePartido, ProdePrediccion, ProdeUser
from app.prode.schemas import PrediccionConPartidoResponse, PrediccionRequest, PrediccionResponse

router = APIRouter(tags=["Prode - Predicciones"])

LOCK_MINUTES = 30


@router.post("/predicciones", response_model=PrediccionResponse, status_code=status.HTTP_200_OK)
def upsert_prediccion(
    body: PrediccionRequest,
    current_user: ProdeUser = Depends(get_current_prode_user),
    db: Session = Depends(get_db),
) -> ProdePrediccion:
    partido = db.query(ProdePartido).filter(ProdePartido.id == body.partido_id).first()
    if not partido:
        raise HTTPException(status_code=404, detail="Partido no encontrado")

    if body.goles_local < 0 or body.goles_visitante < 0:
        raise HTTPException(status_code=422, detail="Los goles no pueden ser negativos")

    now = datetime.now(timezone.utc)
    cutoff = partido.fecha - timedelta(minutes=LOCK_MINUTES)

    if partido.estado != "programado" or cutoff <= now:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Los pronósticos cierran {LOCK_MINUTES} minutos antes del partido",
        )

    existing = (
        db.query(ProdePrediccion)
        .filter(
            ProdePrediccion.user_id == current_user.id,
            ProdePrediccion.partido_id == body.partido_id,
        )
        .first()
    )

    if existing:
        existing.goles_local = body.goles_local
        existing.goles_visitante = body.goles_visitante
        db.commit()
        db.refresh(existing)
        return existing

    pred = ProdePrediccion(
        user_id=current_user.id,
        partido_id=body.partido_id,
        goles_local=body.goles_local,
        goles_visitante=body.goles_visitante,
    )
    db.add(pred)
    db.commit()
    db.refresh(pred)
    return pred


@router.get("/predicciones/me", response_model=list[PrediccionConPartidoResponse])
def my_predicciones(
    current_user: ProdeUser = Depends(get_current_prode_user),
    db: Session = Depends(get_db),
) -> list[ProdePrediccion]:
    return (
        db.query(ProdePrediccion)
        .options(
            joinedload(ProdePrediccion.partido).joinedload(ProdePartido.equipo_local),
            joinedload(ProdePrediccion.partido).joinedload(ProdePartido.equipo_visitante),
        )
        .filter(ProdePrediccion.user_id == current_user.id)
        .join(ProdePartido)
        .order_by(ProdePartido.fecha)
        .all()
    )

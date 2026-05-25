from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.prode.auth import get_current_prode_user
from app.prode.models import ProdePartido, ProdePrediccion, ProdeUser
from app.prode.schemas import PartidoResponse, PrediccionResponse

router = APIRouter(tags=["Prode - Partidos"])


def _attach_prediccion(partido: ProdePartido, user_id, db: Session) -> PartidoResponse:
    pred = (
        db.query(ProdePrediccion)
        .filter(
            ProdePrediccion.partido_id == partido.id,
            ProdePrediccion.user_id == user_id,
        )
        .first()
    )
    data = PartidoResponse.model_validate(partido)
    if pred:
        data.mi_prediccion = PrediccionResponse.model_validate(pred)
    return data


@router.get("/partidos", response_model=list[PartidoResponse])
def get_partidos(
    fase: Optional[str] = None,
    grupo: Optional[str] = None,
    current_user: ProdeUser = Depends(get_current_prode_user),
    db: Session = Depends(get_db),
) -> list[PartidoResponse]:
    q = db.query(ProdePartido)
    if fase:
        q = q.filter(ProdePartido.fase == fase)
    if grupo:
        q = q.filter(ProdePartido.grupo == grupo.upper())
    partidos = q.order_by(ProdePartido.fecha).all()
    return [_attach_prediccion(p, current_user.id, db) for p in partidos]

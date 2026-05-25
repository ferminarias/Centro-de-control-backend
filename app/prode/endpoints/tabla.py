from fastapi import APIRouter, Depends
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.prode.auth import get_current_prode_user
from app.prode.models import ProdePrediccion, ProdeUser
from app.prode.schemas import TablaEntry

router = APIRouter(tags=["Prode - Tabla"])


@router.get("/tabla", response_model=list[TablaEntry])
def get_tabla(
    db: Session = Depends(get_db),
    _: ProdeUser = Depends(get_current_prode_user),
) -> list[TablaEntry]:
    rows = (
        db.query(
            ProdeUser.id,
            ProdeUser.nombre,
            ProdeUser.apellido,
            ProdeUser.avatar_url,
            func.coalesce(func.sum(ProdePrediccion.puntos), 0).label("puntos"),
            func.count(ProdePrediccion.id).label("predicciones"),
            func.sum(
                case((ProdePrediccion.puntos == 3, 1), else_=0)
            ).label("exactos"),
            func.sum(
                case((ProdePrediccion.puntos == 1, 1), else_=0)
            ).label("resultados"),
        )
        .outerjoin(ProdePrediccion, ProdePrediccion.user_id == ProdeUser.id)
        .filter(ProdeUser.activo.is_(True))
        .group_by(ProdeUser.id, ProdeUser.nombre, ProdeUser.apellido, ProdeUser.avatar_url)
        .order_by(
            func.coalesce(func.sum(ProdePrediccion.puntos), 0).desc(),
            func.sum(case((ProdePrediccion.puntos == 3, 1), else_=0)).desc(),
        )
        .all()
    )

    return [
        TablaEntry(
            posicion=i + 1,
            user_id=str(row.id),
            nombre=row.nombre,
            apellido=row.apellido,
            avatar_url=row.avatar_url,
            puntos=int(row.puntos or 0),
            exactos=int(row.exactos or 0),
            resultados=int(row.resultados or 0),
            predicciones=int(row.predicciones or 0),
        )
        for i, row in enumerate(rows)
    ]

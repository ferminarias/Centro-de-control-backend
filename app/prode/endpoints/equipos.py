import uuid as uuid_module

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.prode.auth import get_current_prode_user
from app.prode.models import ProdeClub, ProdePrediccion, ProdeUser
from app.prode.schemas import ClubCreate, ClubMemberAdd, ClubResponse, ClubTablaEntry

router = APIRouter(tags=["Prode - Equipos"])


def _require_gerente(current_user: ProdeUser = Depends(get_current_prode_user)) -> ProdeUser:
    if not current_user.es_gerente and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol de líder")
    return current_user


def _get_user_points(db: Session, user_id) -> int:
    pts = (
        db.query(func.coalesce(func.sum(ProdePrediccion.puntos), 0))
        .filter(ProdePrediccion.user_id == user_id)
        .scalar()
    )
    return int(pts or 0)


# ── CRUD ──────────────────────────────────────────────────────────────────────

@router.post("/equipos", response_model=ClubResponse, status_code=status.HTTP_201_CREATED)
def create_equipo(
    body: ClubCreate,
    db: Session = Depends(get_db),
    current_user: ProdeUser = Depends(_require_gerente),
) -> ProdeClub:
    if not body.nombre.strip():
        raise HTTPException(status_code=422, detail="El nombre no puede estar vacío")
    if not current_user.is_admin:
        existing = db.query(ProdeClub).filter(ProdeClub.gerente_id == current_user.id).first()
        if existing:
            raise HTTPException(status_code=409, detail="Ya tenés un equipo creado")

    club = ProdeClub(nombre=body.nombre.strip(), gerente_id=current_user.id)
    db.add(club)
    db.flush()
    # Un admin crea equipos para terceros sin sumarse como miembro: el primer
    # usuario agregado pasará a ser el gerente (ver add_miembro). Un gerente
    # crea su propio equipo y queda adentro.
    if not current_user.is_admin:
        current_user.club_id = club.id
    db.commit()
    db.refresh(club)
    return club


@router.get("/equipos", response_model=list[ClubResponse])
def list_equipos(
    db: Session = Depends(get_db),
    _: ProdeUser = Depends(get_current_prode_user),
) -> list[ProdeClub]:
    return db.query(ProdeClub).order_by(ProdeClub.nombre).all()


@router.get("/equipos/mi-equipo")
def get_mi_equipo(
    db: Session = Depends(get_db),
    current_user: ProdeUser = Depends(get_current_prode_user),
):
    if not current_user.club_id:
        return None
    club = db.query(ProdeClub).filter(ProdeClub.id == current_user.club_id).first()
    if not club:
        return None
    miembros = (
        db.query(ProdeUser)
        .filter(ProdeUser.club_id == club.id, ProdeUser.activo.is_(True))
        .all()
    )
    return {
        "id": club.id,
        "nombre": club.nombre,
        "gerente_id": str(club.gerente_id),
        "miembros": [
            {
                "user_id": str(m.id),
                "nombre": m.nombre,
                "apellido": m.apellido,
                "avatar_url": m.avatar_url,
                "puntos": _get_user_points(db, m.id),
            }
            for m in miembros
        ],
    }


@router.get("/equipos/tabla", response_model=list[ClubTablaEntry])
def get_tabla_equipos(
    db: Session = Depends(get_db),
    _: ProdeUser = Depends(get_current_prode_user),
) -> list[ClubTablaEntry]:
    clubs = db.query(ProdeClub).all()
    rows = []
    for club in clubs:
        miembros = (
            db.query(ProdeUser)
            .filter(ProdeUser.club_id == club.id, ProdeUser.activo.is_(True))
            .all()
        )
        if not miembros:
            continue
        total = sum(_get_user_points(db, m.id) for m in miembros)
        promedio = round(total / len(miembros), 1)
        rows.append(
            {"club_id": club.id, "nombre": club.nombre, "integrantes": len(miembros), "total_puntos": total, "promedio": promedio}
        )
    rows.sort(key=lambda x: (-x["promedio"], -x["total_puntos"]))
    return [ClubTablaEntry(posicion=i + 1, **r) for i, r in enumerate(rows)]


@router.get("/equipos/usuarios-disponibles")
def list_usuarios_disponibles(
    db: Session = Depends(get_db),
    _: ProdeUser = Depends(_require_gerente),
):
    """Active users a gerente can pick from when adding team members.

    Includes club_id so the frontend can hide/label people already in a team.
    """
    users = (
        db.query(ProdeUser)
        .filter(ProdeUser.activo.is_(True))
        .order_by(ProdeUser.nombre, ProdeUser.apellido)
        .all()
    )
    return [
        {
            "id": str(u.id),
            "nombre": u.nombre,
            "apellido": u.apellido,
            "email": u.email,
            "avatar_url": u.avatar_url,
            "club_id": u.club_id,
        }
        for u in users
    ]


# ── Members ───────────────────────────────────────────────────────────────────

@router.get("/equipos/{club_id}/miembros")
def get_miembros(
    club_id: int,
    db: Session = Depends(get_db),
    _: ProdeUser = Depends(get_current_prode_user),
):
    club = db.query(ProdeClub).filter(ProdeClub.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    miembros = (
        db.query(ProdeUser)
        .filter(ProdeUser.club_id == club_id, ProdeUser.activo.is_(True))
        .all()
    )
    return [
        {
            "user_id": str(m.id),
            "nombre": m.nombre,
            "apellido": m.apellido,
            "avatar_url": m.avatar_url,
            "puntos": _get_user_points(db, m.id),
        }
        for m in miembros
    ]


@router.post("/equipos/{club_id}/miembros")
def add_miembro(
    club_id: int,
    body: ClubMemberAdd,
    db: Session = Depends(get_db),
    current_user: ProdeUser = Depends(_require_gerente),
):
    club = db.query(ProdeClub).filter(ProdeClub.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    if str(club.gerente_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo el líder puede agregar miembros")

    try:
        user_uuid = uuid_module.UUID(body.user_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="user_id inválido")

    user = db.query(ProdeUser).filter(ProdeUser.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.club_id is not None and user.club_id != club_id:
        other = db.query(ProdeClub).filter(ProdeClub.id == user.club_id).first()
        raise HTTPException(
            status_code=409,
            detail=f"El usuario ya pertenece al equipo «{other.nombre if other else user.club_id}»",
        )
    if user.club_id == club_id:
        raise HTTPException(status_code=409, detail="El usuario ya es miembro de este equipo")

    # Primer miembro del equipo → se convierte en gerente y puede sumar al resto
    es_primer_miembro = (
        db.query(func.count(ProdeUser.id)).filter(ProdeUser.club_id == club_id).scalar() or 0
    ) == 0

    user.club_id = club_id
    gerente_asignado = False
    if es_primer_miembro and str(club.gerente_id) != str(user.id):
        club.gerente_id = user.id
        user.es_gerente = True
        gerente_asignado = True
    db.commit()
    return {"ok": True, "gerente_asignado": gerente_asignado}


@router.delete("/equipos/{club_id}/miembros/{user_id}")
def remove_miembro(
    club_id: int,
    user_id: str,
    db: Session = Depends(get_db),
    current_user: ProdeUser = Depends(_require_gerente),
):
    club = db.query(ProdeClub).filter(ProdeClub.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    if str(club.gerente_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo el líder puede eliminar miembros")

    try:
        user_uuid = uuid_module.UUID(user_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="user_id inválido")

    user = db.query(ProdeUser).filter(ProdeUser.id == user_uuid).first()
    if not user or user.club_id != club_id:
        raise HTTPException(status_code=404, detail="El usuario no es miembro de este equipo")
    if str(user.id) == str(club.gerente_id):
        raise HTTPException(status_code=400, detail="No se puede eliminar al líder del equipo")

    user.club_id = None
    db.commit()
    return {"ok": True}


@router.delete("/equipos/{club_id}", status_code=200)
def delete_equipo(
    club_id: int,
    db: Session = Depends(get_db),
    current_user: ProdeUser = Depends(_require_gerente),
):
    club = db.query(ProdeClub).filter(ProdeClub.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    if str(club.gerente_id) != str(current_user.id) and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo el líder puede disolver su equipo")

    db.query(ProdeUser).filter(ProdeUser.club_id == club_id).update({"club_id": None})
    db.delete(club)
    db.commit()
    return {"ok": True}

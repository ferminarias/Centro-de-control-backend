from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.prode.auth import hash_password
from app.prode.models import ProdeUser
from app.prode.schemas import ProdeCreateUserRequest, ProdeUserResponse

router = APIRouter(tags=["Prode - Admin"])


def _verify_admin(x_admin_key: str = Header(...)):
    if not settings.ADMIN_API_KEY or x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Clave admin inválida")


@router.post(
    "/admin/users",
    response_model=ProdeUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario Prode (admin)",
    dependencies=[Depends(_verify_admin)],
)
def create_prode_user(body: ProdeCreateUserRequest, db: Session = Depends(get_db)) -> ProdeUser:
    if db.query(ProdeUser).filter(ProdeUser.email == body.email.lower().strip()).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El email ya está registrado")

    user = ProdeUser(
        email=body.email.lower().strip(),
        nombre=body.nombre,
        apellido=body.apellido,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

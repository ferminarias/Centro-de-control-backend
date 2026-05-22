from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.prode.auth import create_access_token, get_current_prode_user, hash_password, verify_password
from app.prode.models import ProdeUser
from app.prode.schemas import (
    ProdeChangePasswordRequest,
    ProdeLoginRequest,
    ProdeLoginResponse,
    ProdeUserResponse,
)

router = APIRouter(tags=["Prode - Auth"])


@router.post("/auth/login", response_model=ProdeLoginResponse, summary="Login Prode")
def prode_login(body: ProdeLoginRequest, db: Session = Depends(get_db)) -> dict:
    user = db.query(ProdeUser).filter(
        ProdeUser.email == body.email.lower().strip(),
        ProdeUser.activo.is_(True),
    ).first()

    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    token = create_access_token(user.id, user.email)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.get("/auth/me", response_model=ProdeUserResponse, summary="Usuario actual Prode")
def prode_me(current_user: ProdeUser = Depends(get_current_prode_user)) -> ProdeUser:
    return current_user


@router.post("/auth/change-password", response_model=ProdeUserResponse, summary="Cambiar contraseña")
def prode_change_password(
    body: ProdeChangePasswordRequest,
    current_user: ProdeUser = Depends(get_current_prode_user),
    db: Session = Depends(get_db),
) -> ProdeUser:
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contraseña actual incorrecta")

    if len(body.new_password) < 8:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="La nueva contraseña debe tener al menos 8 caracteres")

    current_user.password_hash = hash_password(body.new_password)
    current_user.must_change_password = False
    db.commit()
    db.refresh(current_user)
    return current_user

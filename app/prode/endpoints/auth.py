from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.prode.auth import create_access_token, get_current_prode_user, verify_password
from app.prode.models import ProdeUser
from app.prode.schemas import ProdeLoginRequest, ProdeLoginResponse, ProdeUserResponse

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

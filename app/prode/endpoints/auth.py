from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
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


class GoogleLoginRequest(BaseModel):
    credential: str


class GoogleTokenRequest(BaseModel):
    access_token: str


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


@router.post("/auth/google", response_model=ProdeLoginResponse, summary="Login con Google Workspace")
def google_login(body: GoogleLoginRequest, db: Session = Depends(get_db)) -> dict:
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth no configurado")

    # Verify the Google ID token
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests
        idinfo = id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de Google inválido")

    email: str = idinfo.get("email", "").lower().strip()
    if not email or not idinfo.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email de Google no verificado")

    # Enforce workspace domain restriction
    if settings.GOOGLE_ALLOWED_DOMAIN and not email.endswith(f"@{settings.GOOGLE_ALLOWED_DOMAIN}"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Solo se permiten cuentas @{settings.GOOGLE_ALLOWED_DOMAIN}",
        )

    user = db.query(ProdeUser).filter(ProdeUser.email == email).first()

    if user is None:
        # Auto-register from Google profile
        user = ProdeUser(
            email=email,
            nombre=idinfo.get("given_name") or email.split("@")[0],
            apellido=idinfo.get("family_name") or "",
            avatar_url=idinfo.get("picture"),
            password_hash="",
            is_admin=False,
            must_change_password=False,
            activo=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.activo:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta desactivada")
        # Keep avatar and name in sync with Google
        updated = False
        if idinfo.get("picture") and user.avatar_url != idinfo["picture"]:
            user.avatar_url = idinfo["picture"]
            updated = True
        if updated:
            db.commit()

    token = create_access_token(user.id, user.email)
    return {"access_token": token, "token_type": "bearer", "user": user}


@router.post("/auth/google-token", response_model=ProdeLoginResponse, summary="Login con Google (access token)")
def google_token_login(body: GoogleTokenRequest, db: Session = Depends(get_db)) -> dict:
    """Accept a Google OAuth2 access_token (from implicit flow), validate via userinfo endpoint."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Google OAuth no configurado")

    try:
        import httpx
        resp = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {body.access_token}"},
            timeout=10,
        )
        if resp.status_code != 200:
            raise ValueError("invalid token")
        userinfo = resp.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de Google inválido")

    email: str = userinfo.get("email", "").lower().strip()
    if not email or not userinfo.get("email_verified"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email de Google no verificado")

    if settings.GOOGLE_ALLOWED_DOMAIN and not email.endswith(f"@{settings.GOOGLE_ALLOWED_DOMAIN}"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Solo se permiten cuentas @{settings.GOOGLE_ALLOWED_DOMAIN}",
        )

    user = db.query(ProdeUser).filter(ProdeUser.email == email).first()

    if user is None:
        user = ProdeUser(
            email=email,
            nombre=userinfo.get("given_name") or email.split("@")[0],
            apellido=userinfo.get("family_name") or "",
            avatar_url=userinfo.get("picture"),
            password_hash="",
            is_admin=False,
            must_change_password=False,
            activo=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        if not user.activo:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cuenta desactivada")
        if userinfo.get("picture") and user.avatar_url != userinfo["picture"]:
            user.avatar_url = userinfo["picture"]
            db.commit()

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

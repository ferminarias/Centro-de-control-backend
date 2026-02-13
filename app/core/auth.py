"""
JWT utilities and FastAPI dependencies for user authentication.
"""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    user_id: uuid.UUID,
    cuenta_id: uuid.UUID,
    role_id: uuid.UUID | None,
    permisos: list[str],
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "cuenta_id": str(cuenta_id),
        "role_id": str(role_id) if role_id else None,
        "permisos": permisos,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


# ── Dependencies ───────────────────────────────────────────────────────────

def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Extracts and validates the JWT, returns the User object."""
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    data = decode_token(credentials.credentials)
    user = db.query(User).filter(User.id == data["sub"], User.activo.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_permission(*needed: str):
    """
    Returns a FastAPI dependency that checks the JWT contains ALL the listed permissions.

    Usage:
        @router.get("/...", dependencies=[Depends(require_permission("users:read"))])
    """

    def _checker(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    ) -> dict:
        if not credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

        data = decode_token(credentials.credentials)
        user_perms: list[str] = data.get("permisos", [])

        missing = [p for p in needed if p not in user_perms]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )
        return data

    return _checker

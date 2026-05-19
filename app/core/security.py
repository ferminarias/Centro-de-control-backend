import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"


def _is_valid_jwt(token: str) -> bool:
    try:
        jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return True
    except Exception:
        return False


def verify_admin_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    """
    Verify admin API key OR valid JWT from the Authorization: Bearer header.

    Development bypass: when ENVIRONMENT=development and ADMIN_API_KEY is not
    configured, requests are allowed through with a per-request warning logged.
    This bypass is intentionally disabled in any other environment.
    """
    if settings.ENVIRONMENT == "development" and not settings.ADMIN_API_KEY:
        logger.warning(
            "SECURITY WARNING: admin auth bypassed — "
            "set ADMIN_API_KEY in .env to enable authentication"
        )
        return None

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )

    token = credentials.credentials

    # Accept valid JWT tokens (frontend users)
    if _is_valid_jwt(token):
        return token

    # Accept static admin API key (server-to-server)
    if settings.ADMIN_API_KEY and token == settings.ADMIN_API_KEY:
        return token

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid admin API key",
    )

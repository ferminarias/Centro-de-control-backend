import logging

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)

JWT_ALGORITHM = "HS256"


def _check_jwt(token: str) -> str:
    """Returns 'valid', 'expired', or 'invalid'."""
    try:
        jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return "valid"
    except jwt.ExpiredSignatureError:
        return "expired"
    except Exception:
        return "invalid"


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

    jwt_status = _check_jwt(token)
    if jwt_status == "valid":
        return token
    # Expired JWT → 401 so the frontend refresh interceptor fires
    if jwt_status == "expired":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    # Accept static admin API key (server-to-server)
    if settings.ADMIN_API_KEY and token == settings.ADMIN_API_KEY:
        return token

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Invalid admin API key",
    )

import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


def verify_admin_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    """
    Verify admin API key from the Authorization: Bearer header.

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

    if not credentials or credentials.credentials != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )
    return credentials.credentials

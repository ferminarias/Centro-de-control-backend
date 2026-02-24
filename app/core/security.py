from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)


def verify_admin_key(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str | None:
    """
    Verify admin API key.
    In development mode with empty ADMIN_API_KEY, allows all requests (for testing only).
    """
    # Development mode with no key configured - log warning but allow
    if settings.ENVIRONMENT == "development" and not settings.ADMIN_API_KEY:
        return None

    if not credentials or credentials.credentials != settings.ADMIN_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin API key",
        )
    return credentials.credentials

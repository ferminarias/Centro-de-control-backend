"""
Rate limiting configuration using slowapi and Redis.
"""
import os
from functools import wraps

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, HTTPException

# Use Redis for rate limiting in production, memory for development
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/1")

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL if os.getenv("ENVIRONMENT") != "development" else "memory://",
    strategy="moving-window",  # Better for distributed systems
)


def rate_limit(requests: int, window: str):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        requests: Number of requests allowed
        window: Time window (e.g., "1/minute", "10/hour", "100/day")
    
    Example:
        @router.post("/login")
        @rate_limit(5, "1/minute")
        def login(...):
            ...
    """
    return limiter.limit(f"{requests}/{window}")


def rate_limit_per_user(requests: int, window: str):
    """
    Rate limit per authenticated user (uses user ID if available, IP otherwise).
    """
    def key_func(request: Request):
        # Try to get user ID from request state (set by auth middleware)
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"
        # Fallback to IP address
        return get_remote_address(request)
    
    return limiter.limit(f"{requests}/{window}", key_func=key_func)


def exempt_from_limit(func):
    """Decorator to exempt an endpoint from rate limiting."""
    return limiter.exempt(func)


# Custom rate limit exceeded handler
def custom_rate_limit_handler(request: Request, exc: RateLimitExceeded):
    """Custom handler for rate limit exceeded."""
    raise HTTPException(
        status_code=429,
        detail={
            "error": "Rate limit exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.retry_after if hasattr(exc, "retry_after") else 60,
        },
    )


def setup_rate_limiting(app):
    """Setup rate limiting for the FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

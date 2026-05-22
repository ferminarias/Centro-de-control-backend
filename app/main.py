from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

# from app.api.v1.router import api_router  # CRM desactivado temporalmente
from app.prode.router import prode_router
from app.core.audit_middleware import AuditMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging_config import configure_logging
from app.core.metrics import MetricsMiddleware, get_metrics_response
from app.core.rate_limiter import limiter, custom_rate_limit_handler
from app.core.startup_checks import run_startup_checks
from app.core.tracing import setup_tracing

# Configure structured logging first
logger = configure_logging(settings.ENVIRONMENT)

# Import all models so Base.metadata knows about them
import app.models  # noqa: F401

# ─────────────────────────────────────────────────────────────────────────────
# Database initialization
# ─────────────────────────────────────────────────────────────────────────────

try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created")
except Exception as exc:
    logger.error("Failed to create database tables: %s", exc)

# Fallback checks for migrations that may not have run (idempotent)
run_startup_checks(engine)

# ─────────────────────────────────────────────────────────────────────────────
# Application factory
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Prode Mundial 2026 - Grupo Nods",
    description="Backend del Prode Mundial 2026.",
    version="1.0.0",
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

# CORS — origins come from ALLOWED_ORIGINS env var (comma-separated)
_allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Total-Count"],
    max_age=3600,
)

# Middleware stack (order matters: outermost = first to run)
app.add_middleware(MetricsMiddleware)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuditMiddleware)

# app.include_router(api_router)  # CRM desactivado temporalmente
app.include_router(prode_router)

# OpenTelemetry tracing (no-op if OTEL_EXPORTER_OTLP_ENDPOINT is not set)
setup_tracing(app)


# ─────────────────────────────────────────────────────────────────────────────
# System endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["Health"])
def health_check() -> dict:
    return {"status": "ok"}


@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics_response()

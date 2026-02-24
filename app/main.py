import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.audit_middleware import AuditMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging_config import configure_logging
from app.core.metrics import MetricsMiddleware, get_metrics_response
from app.core.rate_limiter import limiter, custom_rate_limit_handler

# Configure structured logging
logger = configure_logging(settings.ENVIRONMENT)

# Import all models so Base.metadata knows about them
import app.models  # noqa: F401

# Create any missing tables (fallback if alembic migration didn't run)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified/created successfully")
except Exception as e:
    logger.error("Failed to create database tables: %s", e)

# Add lead_base_id column to leads if missing (fallback for migration 004)
try:
    from sqlalchemy import text

    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'leads' AND column_name = 'lead_base_id'"
        ))
        if not result.fetchone():
            conn.execute(text(
                "ALTER TABLE leads ADD COLUMN lead_base_id UUID "
                "REFERENCES lead_bases(id) ON DELETE SET NULL"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_leads_lead_base_id ON leads (lead_base_id)"
            ))
            conn.commit()
            logger.info("Added lead_base_id column to leads table")
        else:
            logger.info("lead_base_id column already exists in leads table")
except Exception as e:
    logger.error("Failed to add lead_base_id column: %s", e)

# Add lote_id column to leads if missing (fallback for migration 005)
try:
    from sqlalchemy import text as _text

    with engine.connect() as conn:
        result = conn.execute(_text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'leads' AND column_name = 'lote_id'"
        ))
        if not result.fetchone():
            conn.execute(_text(
                "ALTER TABLE leads ADD COLUMN lote_id UUID "
                "REFERENCES lotes(id) ON DELETE SET NULL"
            ))
            conn.execute(_text(
                "CREATE INDEX IF NOT EXISTS ix_leads_lote_id ON leads (lote_id)"
            ))
            conn.commit()
            logger.info("Added lote_id column to leads table")
        else:
            logger.info("lote_id column already exists in leads table")
except Exception as e:
    logger.error("Failed to add lote_id column: %s", e)

# Add id_lead column to leads if missing (fallback for migration 008)
try:
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'leads' AND column_name = 'id_lead'"
        ))
        if not result.fetchone():
            conn.execute(text(
                "ALTER TABLE leads ADD COLUMN id_lead INTEGER"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_leads_id_lead ON leads (id_lead)"
            ))
            # Backfill existing leads
            conn.execute(text("""
                UPDATE leads
                SET id_lead = sub.rn
                FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (PARTITION BY cuenta_id ORDER BY created_at) AS rn
                    FROM leads
                ) sub
                WHERE leads.id = sub.id
            """))
            conn.commit()
            logger.info("Added id_lead column to leads table and backfilled")
        else:
            logger.info("id_lead column already exists in leads table")
except Exception as e:
    logger.error("Failed to add id_lead column: %s", e)

# Add column_name column to custom_fields if missing (fallback for migration 010)
try:
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'custom_fields' AND column_name = 'column_name'"
        ))
        if not result.fetchone():
            conn.execute(text(
                "ALTER TABLE custom_fields ADD COLUMN column_name VARCHAR(100)"
            ))
            conn.commit()
            logger.info("Added column_name column to custom_fields table")

            # Backfill existing custom fields and create real columns on leads
            import re

            def _sanitize(nombre: str) -> str:
                clean = re.sub(r"[^a-z0-9]", "_", nombre.lower())
                clean = re.sub(r"_+", "_", clean).strip("_")
                return f"cf_{clean}"

            rows = conn.execute(text("SELECT id, nombre_campo FROM custom_fields")).fetchall()
            for row_id, nombre_campo in rows:
                col_name = _sanitize(nombre_campo)
                conn.execute(text(
                    "UPDATE custom_fields SET column_name = :col WHERE id = :id"
                ), {"col": col_name, "id": str(row_id)})
                conn.execute(text(
                    f'ALTER TABLE leads ADD COLUMN IF NOT EXISTS "{col_name}" TEXT'
                ))
                conn.execute(text(
                    f'UPDATE leads SET "{col_name}" = datos->>:field_name '
                    f"WHERE datos ? :field_name"
                ), {"field_name": nombre_campo})
            conn.commit()
            logger.info("Backfilled %d custom field columns on leads", len(rows))
        else:
            logger.info("column_name column already exists in custom_fields table")
except Exception as e:
    logger.error("Failed to add column_name to custom_fields: %s", e)

# Create ficha_configs table if missing (fallback for migration 014)
try:
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT to_regclass('public.ficha_configs')"
        ))
        if result.scalar() is None:
            conn.execute(text("""
                CREATE TABLE ficha_configs (
                    id UUID PRIMARY KEY,
                    cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                    campania_id UUID REFERENCES campanias(id) ON DELETE CASCADE,
                    campos JSONB NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT now(),
                    updated_at TIMESTAMPTZ DEFAULT now(),
                    CONSTRAINT uq_ficha_config_cuenta_campania UNIQUE (cuenta_id, campania_id)
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_ficha_configs_cuenta_id ON ficha_configs (cuenta_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_ficha_configs_campania_id ON ficha_configs (campania_id)"
            ))
            conn.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_ficha_config_cuenta_default "
                "ON ficha_configs (cuenta_id) WHERE campania_id IS NULL"
            ))
            conn.commit()
            logger.info("Created ficha_configs table")
        else:
            logger.info("ficha_configs table already exists")
except Exception as e:
    logger.error("Failed to create ficha_configs table: %s", e)

# Create tipificaciones_externas table and ultima_tipificacion column if missing (fallback for migration 015)
try:
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT to_regclass('public.tipificaciones_externas')"
        ))
        if result.scalar() is None:
            conn.execute(text("""
                CREATE TABLE tipificaciones_externas (
                    id UUID PRIMARY KEY,
                    cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
                    lead_id UUID REFERENCES leads(id) ON DELETE SET NULL,
                    email VARCHAR(255) NOT NULL,
                    id_neotel VARCHAR(100) NOT NULL,
                    id_subresolucion VARCHAR(100) NOT NULL,
                    raw_payload JSONB NOT NULL,
                    matched BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_tipificaciones_externas_cuenta_id "
                "ON tipificaciones_externas (cuenta_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_tipificaciones_externas_lead_id "
                "ON tipificaciones_externas (lead_id)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_tipificaciones_externas_created_at "
                "ON tipificaciones_externas (created_at)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_tipificaciones_externas_cuenta_email "
                "ON tipificaciones_externas (cuenta_id, email)"
            ))
            conn.execute(text(
                "CREATE INDEX IF NOT EXISTS ix_tipificaciones_externas_cuenta_matched "
                "ON tipificaciones_externas (cuenta_id, matched)"
            ))
            conn.commit()
            logger.info("Created tipificaciones_externas table")
        else:
            logger.info("tipificaciones_externas table already exists")

        # Add ultima_tipificacion column to leads if missing
        result = conn.execute(text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'leads' AND column_name = 'ultima_tipificacion'"
        ))
        if not result.fetchone():
            conn.execute(text(
                "ALTER TABLE leads ADD COLUMN ultima_tipificacion JSONB"
            ))
            conn.commit()
            logger.info("Added ultima_tipificacion column to leads table")
        else:
            logger.info("ultima_tipificacion column already exists in leads table")
except Exception as e:
    logger.error("Failed to create tipificaciones_externas table or column: %s", e)

app = FastAPI(
    title="Centro de Control - Multi-Tenant CRM Ingest",
    description="Backend multi-tenant para ingesta de datos de CRM con auto-creación de campos.",
    version="1.0.0",
)

# Setup rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

# Parse allowed origins from settings
# Supports comma-separated list: "https://a.com,https://b.com"
_allowed_origins = [
    origin.strip()
    for origin in settings.ALLOWED_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-Total-Count"],
    max_age=3600,
)

# Middleware de métricas (primero para capturar todo)
app.add_middleware(MetricsMiddleware)

# Middleware de rate limiting
app.add_middleware(SlowAPIMiddleware)

# Middleware de auditoría automática
app.add_middleware(AuditMiddleware)

app.include_router(api_router)


# Metrics endpoint
@app.get("/metrics", include_in_schema=False)
def metrics():
    """Prometheus metrics endpoint."""
    return get_metrics_response()


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    return {"status": "ok"}

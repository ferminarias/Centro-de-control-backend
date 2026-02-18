import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.database import Base, engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

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

app = FastAPI(
    title="Centro de Control - Multi-Tenant CRM Ingest",
    description="Backend multi-tenant para ingesta de datos de CRM con auto-creación de campos.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check() -> dict:
    return {"status": "ok"}

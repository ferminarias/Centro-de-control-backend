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

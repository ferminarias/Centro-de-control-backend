"""
Startup schema checks - fallback safety net for environments where
Alembic migrations may not have run (e.g. local dev without Docker).

NOTE: Alembic is the source of truth. These checks are idempotent guards only.
      Each function maps 1:1 to an Alembic migration version.
"""
import logging
import re

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _column_exists(conn, table: str, column: str) -> bool:
    result = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(
        text("SELECT to_regclass('public.' || :table)"),
        {"table": table},
    )
    return result.scalar() is not None


def _sanitize_field_name(nombre: str) -> str:
    clean = re.sub(r"[^a-z0-9]", "_", nombre.lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    return f"cf_{clean}"


# ─────────────────────────────────────────────────────────────────────────────
# Per-migration fallback checks
# ─────────────────────────────────────────────────────────────────────────────

def _check_migration_004(conn) -> None:
    """lead_base_id on leads (migration 004)."""
    if _column_exists(conn, "leads", "lead_base_id"):
        return
    conn.execute(text(
        "ALTER TABLE leads ADD COLUMN lead_base_id UUID "
        "REFERENCES lead_bases(id) ON DELETE SET NULL"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_leads_lead_base_id ON leads (lead_base_id)"
    ))
    conn.commit()
    logger.warning("Startup check: applied migration 004 fallback (lead_base_id on leads)")


def _check_migration_005(conn) -> None:
    """lote_id on leads (migration 005)."""
    if _column_exists(conn, "leads", "lote_id"):
        return
    conn.execute(text(
        "ALTER TABLE leads ADD COLUMN lote_id UUID "
        "REFERENCES lotes(id) ON DELETE SET NULL"
    ))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_leads_lote_id ON leads (lote_id)"
    ))
    conn.commit()
    logger.warning("Startup check: applied migration 005 fallback (lote_id on leads)")


def _check_migration_008(conn) -> None:
    """id_lead sequential counter on leads (migration 008)."""
    if _column_exists(conn, "leads", "id_lead"):
        return
    conn.execute(text("ALTER TABLE leads ADD COLUMN id_lead INTEGER"))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_leads_id_lead ON leads (id_lead)"
    ))
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
    logger.warning("Startup check: applied migration 008 fallback (id_lead on leads)")


def _check_migration_010(conn) -> None:
    """column_name on custom_fields (migration 010)."""
    if _column_exists(conn, "custom_fields", "column_name"):
        return
    conn.execute(text(
        "ALTER TABLE custom_fields ADD COLUMN column_name VARCHAR(100)"
    ))
    rows = conn.execute(
        text("SELECT id, nombre_campo FROM custom_fields")
    ).fetchall()
    for row_id, nombre_campo in rows:
        col_name = _sanitize_field_name(nombre_campo)
        conn.execute(
            text("UPDATE custom_fields SET column_name = :col WHERE id = :id"),
            {"col": col_name, "id": str(row_id)},
        )
        conn.execute(text(
            f'ALTER TABLE leads ADD COLUMN IF NOT EXISTS "{col_name}" TEXT'
        ))
        conn.execute(
            text(f'UPDATE leads SET "{col_name}" = datos->>:f WHERE datos ? :f'),
            {"f": nombre_campo},
        )
    conn.commit()
    logger.warning(
        "Startup check: applied migration 010 fallback "
        "(column_name on custom_fields, %d fields backfilled)",
        len(rows),
    )


def _check_migration_014(conn) -> None:
    """ficha_configs table (migration 014)."""
    if _table_exists(conn, "ficha_configs"):
        return
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
    logger.warning("Startup check: applied migration 014 fallback (ficha_configs table)")


def _check_migration_015(conn) -> None:
    """tipificaciones_externas table + ultima_tipificacion on leads (migration 015)."""
    if not _table_exists(conn, "tipificaciones_externas"):
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
        for idx in [
            "CREATE INDEX IF NOT EXISTS ix_tipif_ext_cuenta ON tipificaciones_externas (cuenta_id)",
            "CREATE INDEX IF NOT EXISTS ix_tipif_ext_lead ON tipificaciones_externas (lead_id)",
            "CREATE INDEX IF NOT EXISTS ix_tipif_ext_created ON tipificaciones_externas (created_at)",
            "CREATE INDEX IF NOT EXISTS ix_tipif_ext_cuenta_email ON tipificaciones_externas (cuenta_id, email)",
            "CREATE INDEX IF NOT EXISTS ix_tipif_ext_cuenta_matched ON tipificaciones_externas (cuenta_id, matched)",
        ]:
            conn.execute(text(idx))
        conn.commit()
        logger.warning("Startup check: applied migration 015 fallback (tipificaciones_externas table)")

    if not _column_exists(conn, "leads", "ultima_tipificacion"):
        conn.execute(text("ALTER TABLE leads ADD COLUMN ultima_tipificacion JSONB"))
        conn.commit()
        logger.warning("Startup check: applied migration 015 fallback (ultima_tipificacion on leads)")


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def run_startup_checks(engine: Engine) -> None:
    """
    Run all schema fallback checks at application startup.
    Each check is idempotent - safe to run multiple times.
    A warning is logged only when a fallback is actually applied.
    """
    try:
        with engine.connect() as conn:
            _check_migration_004(conn)
            _check_migration_005(conn)
            _check_migration_008(conn)
            _check_migration_010(conn)
            _check_migration_014(conn)
            _check_migration_015(conn)
        logger.info("Startup schema checks completed")
    except Exception as exc:
        logger.error("Startup schema checks failed: %s", exc)

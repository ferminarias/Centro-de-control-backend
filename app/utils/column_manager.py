"""Manage real PostgreSQL columns for custom fields on the leads table.

Strategy: dual-write — values go into both the JSONB `datos` column (for API
compatibility) and into a dedicated TEXT column (for raw SQL queries).
"""

import logging
import re
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def sanitize_column_name(nombre_campo: str) -> str:
    """Return a safe PG column name: ``cf_`` + lowercase + non-alnum → ``_``."""
    clean = re.sub(r"[^a-z0-9]", "_", nombre_campo.lower())
    clean = re.sub(r"_+", "_", clean).strip("_")
    return f"cf_{clean}"


def add_column_to_leads(db: Session, column_name: str) -> None:
    """Add a TEXT column to the leads table (idempotent)."""
    db.execute(
        text(f'ALTER TABLE leads ADD COLUMN IF NOT EXISTS "{column_name}" TEXT')
    )
    db.flush()
    logger.info("Ensured column '%s' exists on leads table", column_name)


def drop_column_from_leads(db: Session, column_name: str) -> None:
    """Remove a column from the leads table (idempotent)."""
    db.execute(
        text(f'ALTER TABLE leads DROP COLUMN IF EXISTS "{column_name}"')
    )
    db.flush()
    logger.info("Dropped column '%s' from leads table", column_name)


def sync_lead_columns(
    db: Session,
    lead_id: uuid.UUID,
    datos: dict,
    field_map: dict[str, str],
) -> None:
    """Write custom-field values into their real columns for a single lead.

    *field_map* maps ``nombre_campo`` → ``column_name``.
    """
    sets: list[str] = []
    params: dict = {"lead_id": str(lead_id)}

    for field_name, col_name in field_map.items():
        if field_name in datos:
            param_key = f"v_{col_name}"
            val = datos[field_name]
            sets.append(f'"{col_name}" = :{param_key}')
            params[param_key] = str(val) if val is not None else None

    if not sets:
        return

    sql = f"UPDATE leads SET {', '.join(sets)} WHERE id = :lead_id"
    db.execute(text(sql), params)


def backfill_column(db: Session, column_name: str, field_name: str) -> int:
    """Bulk-copy values from ``datos->>field_name`` into the real column.

    Returns the number of rows updated.
    """
    result = db.execute(
        text(
            f'UPDATE leads SET "{column_name}" = datos->>:field_name '
            f"WHERE datos ? :field_name"
        ),
        {"field_name": field_name},
    )
    db.flush()
    count = result.rowcount
    logger.info(
        "Backfilled %d rows for column '%s' from field '%s'",
        count, column_name, field_name,
    )
    return count

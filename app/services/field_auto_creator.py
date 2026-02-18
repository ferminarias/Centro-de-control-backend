import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.field import CustomField
from app.services.type_inference import infer_type
from app.utils.column_manager import add_column_to_leads, sanitize_column_name

logger = logging.getLogger(__name__)


def auto_create_fields(
    db: Session,
    cuenta_id: uuid.UUID,
    payload: dict[str, Any],
    existing_field_names: set[str],
) -> list[str]:
    """Auto-create fields for keys not yet registered. Returns list of created field names."""
    created: list[str] = []

    for key, value in payload.items():
        if key in settings.EXCLUDED_FIELDS:
            logger.debug("Skipping excluded field: %s", key)
            continue

        if key in existing_field_names:
            continue

        tipo = infer_type(value)
        col_name = sanitize_column_name(key)
        field = CustomField(
            cuenta_id=cuenta_id,
            nombre_campo=key,
            tipo_dato=tipo,
            column_name=col_name,
        )
        db.add(field)
        created.append(key)
        logger.info(
            "Auto-created field '%s' (type=%s, col=%s) for account %s",
            key,
            tipo,
            col_name,
            cuenta_id,
        )

    if created:
        db.flush()
        # Create real columns on the leads table
        for key in created:
            col_name = sanitize_column_name(key)
            try:
                add_column_to_leads(db, col_name)
            except Exception as e:
                logger.error("Failed to add column '%s': %s", col_name, e)

    return created


def detect_unknown_fields(
    payload: dict[str, Any],
    existing_field_names: set[str],
) -> list[str]:
    """Return field names present in the payload but not registered for the account."""
    unknown = []
    for key in payload:
        if key in settings.EXCLUDED_FIELDS:
            continue
        if key not in existing_field_names:
            unknown.append(key)
    return unknown

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.field import CustomField
from app.services.type_inference import infer_type

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
        field = CustomField(
            cuenta_id=cuenta_id,
            nombre_campo=key,
            tipo_dato=tipo,
        )
        db.add(field)
        created.append(key)
        logger.info(
            "Auto-created field '%s' (type=%s) for account %s",
            key,
            tipo,
            cuenta_id,
        )

    if created:
        db.flush()

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

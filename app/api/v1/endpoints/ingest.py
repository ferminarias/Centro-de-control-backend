import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.account import Account
from app.models.field import CustomField
from app.models.lead import Lead
from app.models.record import Record
from app.schemas.ingest import IngestResponse
from app.services.field_auto_creator import auto_create_fields, detect_unknown_fields

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/ingest/{account_api_key}",
    response_model=IngestResponse,
    summary="Ingest webhook data",
    description="Receive CRM data for a specific account identified by its API key.",
)
def ingest_webhook(
    account_api_key: str,
    payload: dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
) -> IngestResponse:
    account = (
        db.query(Account)
        .filter(Account.api_key == account_api_key, Account.activo.is_(True))
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found or inactive",
        )

    logger.info("Webhook received for account '%s' (%s)", account.nombre, account.id)

    existing_fields = (
        db.query(CustomField.nombre_campo)
        .filter(CustomField.cuenta_id == account.id)
        .all()
    )
    existing_names: set[str] = {f[0] for f in existing_fields}

    fields_created: list[str] = []
    unknown_fields: list[str] = []

    if account.auto_crear_campos:
        fields_created = auto_create_fields(db, account.id, payload, existing_names)
    else:
        unknown_fields = detect_unknown_fields(payload, existing_names)
        if unknown_fields:
            logger.warning(
                "Unknown fields for account %s: %s", account.id, unknown_fields
            )

    record = Record(
        cuenta_id=account.id,
        datos=payload,
        metadata_={
            "source_ip": request.client.host if request.client else None,
            "unknown_fields": unknown_fields or None,
        },
    )
    db.add(record)
    db.flush()

    lead = Lead(
        cuenta_id=account.id,
        record_id=record.id,
        datos=payload,
    )
    db.add(lead)
    db.commit()
    db.refresh(record)
    db.refresh(lead)

    logger.info("Record %s and Lead %s created for account %s", record.id, lead.id, account.id)

    return IngestResponse(
        success=True,
        record_id=record.id,
        lead_id=lead.id,
        unknown_fields=unknown_fields,
        auto_create_enabled=account.auto_crear_campos,
        fields_created=fields_created or None,
    )

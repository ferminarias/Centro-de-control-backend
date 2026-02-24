import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limiter import rate_limit
from app.models.account import Account
from app.models.field import CustomField
from app.models.lead import Lead
from app.models.record import Record
from app.schemas.ingest import IngestResponse
from app.tasks.automations import run_automations_for_event
from app.services.field_auto_creator import auto_create_fields, detect_unknown_fields
from app.services.lead_id_generator import next_id_lead
from app.services.routing_engine import evaluate_routing
from app.services.webhook_dispatcher import dispatch_event
from app.utils.column_manager import sync_lead_columns

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/ingest/{account_api_key}",
    response_model=IngestResponse,
    summary="Ingest webhook data",
    description="Receive CRM data for a specific account identified by its API key.",
)
@rate_limit(100, "1/minute")  # 100 requests per minute per IP
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

    try:
        lead_base_id = evaluate_routing(db, account.id, payload)
        logger.info("Routing result for account %s: lead_base_id=%s", account.id, lead_base_id)
    except Exception as e:
        logger.error("Routing failed for account %s: %s", account.id, e)
        lead_base_id = None

    lead = Lead(
        cuenta_id=account.id,
        record_id=record.id,
        datos=payload,
        lead_base_id=lead_base_id,
        id_lead=next_id_lead(db, account.id),
    )
    db.add(lead)
    db.commit()
    db.refresh(record)
    db.refresh(lead)

    # Sync custom-field values into real columns
    try:
        field_rows = (
            db.query(CustomField.nombre_campo, CustomField.column_name)
            .filter(CustomField.cuenta_id == account.id, CustomField.column_name.isnot(None))
            .all()
        )
        field_map = {name: col for name, col in field_rows}
        if field_map:
            sync_lead_columns(db, lead.id, payload, field_map)
            db.commit()
    except Exception as e:
        logger.error("Failed to sync lead columns for lead %s: %s", lead.id, e)

    logger.info("Record %s and Lead %s created (base=%s) for account %s", record.id, lead.id, lead_base_id, account.id)

    # Fire webhooks (best-effort, independent of automations)
    try:
        event_payload = {"lead_id": str(lead.id), "record_id": str(record.id), "datos": payload}
        dispatch_event(db, account.id, "lead_created", event_payload)
    except Exception as e:
        logger.error("Webhook dispatch failed for account %s: %s", account.id, e)

    # Fire automations asynchronously (non-blocking)
    try:
        run_automations_for_event.delay(
            str(account.id),
            "lead_created",
            str(lead.id),
            context={"record_id": str(record.id)}
        )
    except Exception as e:
        logger.error("Failed to queue automations for account %s: %s", account.id, e)

    return IngestResponse(
        success=True,
        record_id=record.id,
        lead_id=lead.id,
        lead_base_id=lead_base_id,
        unknown_fields=unknown_fields,
        auto_create_enabled=account.auto_crear_campos,
        fields_created=fields_created or None,
    )

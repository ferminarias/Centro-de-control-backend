import hashlib
import hmac
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import or_
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
from app.services.scoring_engine import recalculate_and_save
from app.services.webhook_dispatcher import dispatch_event
from app.utils.column_manager import sync_lead_columns

logger = logging.getLogger(__name__)
router = APIRouter()

# Fields used for deduplication (checked in order of preference)
_DEDUP_FIELDS = ["email", "telefono", "phone", "tel", "correo"]


def _verify_signature(body_bytes: bytes, secret: str, signature: str | None) -> bool:
    """Verify HMAC-SHA256 signature. Returns True if valid or if no signature provided."""
    if not signature:
        return True  # Signature is optional; accounts can enforce it themselves
    expected = "sha256=" + hmac.new(secret.encode(), body_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _find_duplicate_lead(db: Session, cuenta_id: Any, payload: dict) -> Lead | None:
    """Look for an existing lead with the same dedup field value."""
    for field in _DEDUP_FIELDS:
        value = payload.get(field)
        if not value or not str(value).strip():
            continue
        value_str = str(value).strip().lower()
        # Search in JSONB datos column
        existing = (
            db.query(Lead)
            .filter(
                Lead.cuenta_id == cuenta_id,
                Lead.datos[field].astext.ilike(value_str),
            )
            .first()
        )
        if existing:
            return existing
    return None


@router.post(
    "/ingest/{account_api_key}",
    response_model=IngestResponse,
    summary="Ingest webhook data",
    description="Receive CRM data for a specific account identified by its API key.",
)
@rate_limit(100, "1/minute")
async def ingest_webhook(
    account_api_key: str,
    payload: dict[str, Any],
    request: Request,
    x_signature: str | None = Header(default=None, alias="X-Signature"),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
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

    # Verify HMAC signature if provided
    raw_body = await request.body()
    if not _verify_signature(raw_body, account.webhook_secret, x_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook signature")

    logger.info("Webhook received for account '%s' (%s)", account.nombre, account.id)

    # Idempotency: if same key was already processed, return the existing lead
    if x_idempotency_key:
        existing_record = (
            db.query(Record)
            .filter(
                Record.cuenta_id == account.id,
                Record.metadata_["idempotency_key"].astext == x_idempotency_key,
            )
            .first()
        )
        if existing_record:
            existing_lead = db.query(Lead).filter(Lead.record_id == existing_record.id).first()
            logger.info("Idempotent request detected, returning existing lead %s", existing_lead and existing_lead.id)
            return IngestResponse(
                success=True,
                record_id=existing_record.id,
                lead_id=existing_lead.id if existing_lead else None,
                lead_base_id=existing_lead.lead_base_id if existing_lead else None,
                unknown_fields=[],
                auto_create_enabled=account.auto_crear_campos,
                fields_created=None,
                deduplicated=True,
            )

    existing_fields = (
        db.query(CustomField.nombre_campo)
        .filter(CustomField.cuenta_id == account.id)
        .all()
    )
    existing_names: set[str] = {f[0] for f in existing_fields}

    fields_created: list[str] = []
    unknown_fields: list[str] = []

    if account.auto_crear_campos:
        fields_created = auto_create_fields(
            db, account.id, payload, existing_names,
            max_fields=account.max_custom_fields,
        )
    else:
        unknown_fields = detect_unknown_fields(payload, existing_names)
        if unknown_fields:
            logger.warning("Unknown fields for account %s: %s", account.id, unknown_fields)

    # Deduplication: update existing lead instead of creating a duplicate
    duplicate_lead = _find_duplicate_lead(db, account.id, payload)
    is_dedup = duplicate_lead is not None

    record = Record(
        cuenta_id=account.id,
        datos=payload,
        metadata_={
            "source_ip": request.client.host if request.client else None,
            "unknown_fields": unknown_fields or None,
            "idempotency_key": x_idempotency_key,
            "deduplicated": is_dedup,
        },
    )
    db.add(record)
    db.flush()

    if is_dedup:
        # Merge new data into existing lead
        lead = duplicate_lead
        merged = dict(lead.datos)
        merged.update(payload)
        lead.datos = merged
        lead.record_id = record.id
        logger.info("Deduplicated lead %s for account %s", lead.id, account.id)
    else:
        try:
            lead_base_id = evaluate_routing(db, account.id, payload)
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

    # Recalculate score after data update
    try:
        recalculate_and_save(db, lead)
        db.commit()
    except Exception as e:
        logger.error("Scoring failed for lead %s: %s", lead.id, e)

    logger.info(
        "Record %s → Lead %s (dedup=%s, score=%s) for account %s",
        record.id, lead.id, is_dedup, lead.score, account.id,
    )

    event = "lead_updated" if is_dedup else "lead_created"

    try:
        event_payload = {"lead_id": str(lead.id), "record_id": str(record.id), "datos": payload}
        dispatch_event(db, account.id, event, event_payload)
    except Exception as e:
        logger.error("Webhook dispatch failed for account %s: %s", account.id, e)

    try:
        run_automations_for_event.delay(
            str(account.id), event, str(lead.id),
            context={"record_id": str(record.id)},
        )
    except Exception as e:
        logger.error("Failed to queue automations for account %s: %s", account.id, e)

    return IngestResponse(
        success=True,
        record_id=record.id,
        lead_id=lead.id,
        lead_base_id=lead.lead_base_id,
        unknown_fields=unknown_fields,
        auto_create_enabled=account.auto_crear_campos,
        fields_created=fields_created or None,
        deduplicated=is_dedup,
    )

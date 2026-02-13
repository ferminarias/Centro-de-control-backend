import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.webhook import Webhook, WebhookLog
from app.schemas.webhook import (
    WEBHOOK_EVENTS,
    WebhookCreate,
    WebhookListResponse,
    WebhookLogListResponse,
    WebhookLogResponse,
    WebhookResponse,
    WebhookTestResponse,
    WebhookUpdate,
)
from app.services.webhook_dispatcher import deliver_single

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_admin_key)])


def _validate_eventos(eventos: list[str]) -> None:
    invalid = [e for e in eventos if e not in WEBHOOK_EVENTS]
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid events: {', '.join(invalid)}. Valid: {', '.join(WEBHOOK_EVENTS)}",
        )


# ── CRUD ───────────────────────────────────────────────────────────────────

@router.post(
    "/accounts/{account_id}/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a webhook",
)
def create_webhook(
    account_id: uuid.UUID,
    body: WebhookCreate,
    db: Session = Depends(get_db),
) -> Webhook:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    _validate_eventos(body.eventos)

    wh = Webhook(
        cuenta_id=account_id,
        nombre=body.nombre,
        url=body.url,
        eventos=body.eventos,
        headers_custom=body.headers_custom,
        secret=body.secret,
        activo=body.activo,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    logger.info("Webhook '%s' created for account %s", wh.nombre, account_id)
    return wh


@router.get(
    "/accounts/{account_id}/webhooks",
    response_model=WebhookListResponse,
    summary="List webhooks for an account",
)
def list_webhooks(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    items = (
        db.query(Webhook)
        .filter(Webhook.cuenta_id == account_id)
        .order_by(Webhook.created_at.desc())
        .all()
    )
    return {"items": items, "total": len(items)}


@router.get(
    "/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    summary="Get webhook details",
)
def get_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Webhook:
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return wh


@router.put(
    "/webhooks/{webhook_id}",
    response_model=WebhookResponse,
    summary="Update a webhook",
)
def update_webhook(
    webhook_id: uuid.UUID,
    body: WebhookUpdate,
    db: Session = Depends(get_db),
) -> Webhook:
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")

    if body.nombre is not None:
        wh.nombre = body.nombre
    if body.url is not None:
        wh.url = body.url
    if body.eventos is not None:
        _validate_eventos(body.eventos)
        wh.eventos = body.eventos
    if body.headers_custom is not None:
        wh.headers_custom = body.headers_custom
    if body.secret is not None:
        wh.secret = body.secret
    if body.activo is not None:
        wh.activo = body.activo

    db.commit()
    db.refresh(wh)
    return wh


@router.delete(
    "/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a webhook",
)
def delete_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")
    db.delete(wh)
    db.commit()
    logger.info("Webhook '%s' deleted", wh.nombre)


# ── Test ───────────────────────────────────────────────────────────────────

@router.post(
    "/webhooks/{webhook_id}/test",
    response_model=WebhookTestResponse,
    summary="Send a test payload to the webhook",
)
def test_webhook(
    webhook_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")

    test_payload = {
        "event": "test",
        "webhook_id": str(wh.id),
        "message": "This is a test delivery from Centro de Control",
    }
    result = deliver_single(db, wh, "test", test_payload)
    return result


# ── Logs ───────────────────────────────────────────────────────────────────

@router.get(
    "/webhooks/{webhook_id}/logs",
    response_model=WebhookLogListResponse,
    summary="List delivery logs for a webhook",
)
def list_webhook_logs(
    webhook_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    wh = db.query(Webhook).filter(Webhook.id == webhook_id).first()
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook not found")

    query = db.query(WebhookLog).filter(WebhookLog.webhook_id == webhook_id)
    total = query.count()
    items = (
        query.order_by(WebhookLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total}


# ── Events meta ────────────────────────────────────────────────────────────

@router.get(
    "/webhook-events",
    summary="List all available webhook events",
)
def list_webhook_events() -> dict:
    return {"events": WEBHOOK_EVENTS}

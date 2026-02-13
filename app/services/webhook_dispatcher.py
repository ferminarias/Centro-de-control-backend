"""
Fires outbound webhooks for a given event + account.

Usage (from any endpoint / service):
    from app.services.webhook_dispatcher import dispatch_event
    dispatch_event(db, cuenta_id, "lead_created", {"lead_id": "...", "datos": {...}})

The function is synchronous and best-effort: failures are logged but never raised.
"""

import hashlib
import hmac
import json
import logging
import time
import uuid

import httpx
from sqlalchemy.orm import Session

from app.models.webhook import Webhook, WebhookLog

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # seconds per request


def _sign_payload(payload_bytes: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()


def dispatch_event(
    db: Session,
    cuenta_id: uuid.UUID,
    evento: str,
    payload: dict,
) -> None:
    """Send `payload` to every active webhook of the account that listens to `evento`."""
    webhooks = (
        db.query(Webhook)
        .filter(Webhook.cuenta_id == cuenta_id, Webhook.activo.is_(True))
        .all()
    )

    for wh in webhooks:
        if evento not in (wh.eventos or []):
            continue

        _deliver(db, wh, evento, payload)


def deliver_single(
    db: Session,
    webhook: Webhook,
    evento: str,
    payload: dict,
) -> dict:
    """Deliver to a single webhook and return result dict (used for test endpoint)."""
    return _deliver(db, webhook, evento, payload, log=True)


def _deliver(
    db: Session,
    webhook: Webhook,
    evento: str,
    payload: dict,
    log: bool = True,
) -> dict:
    body_bytes = json.dumps(payload, default=str).encode()

    headers: dict[str, str] = {
        "Content-Type": "application/json",
        "X-Webhook-Event": evento,
    }
    if webhook.secret:
        headers["X-Webhook-Signature"] = _sign_payload(body_bytes, webhook.secret)
    if webhook.headers_custom:
        headers.update(webhook.headers_custom)

    result: dict = {
        "success": False,
        "status_code": None,
        "response_body": None,
        "error": None,
        "duration_ms": None,
    }

    start = time.monotonic()
    try:
        with httpx.Client(timeout=_TIMEOUT) as client:
            resp = client.post(webhook.url, content=body_bytes, headers=headers)
        elapsed = int((time.monotonic() - start) * 1000)
        result["status_code"] = resp.status_code
        result["response_body"] = resp.text[:2000]
        result["duration_ms"] = elapsed
        result["success"] = 200 <= resp.status_code < 300
    except Exception as exc:
        elapsed = int((time.monotonic() - start) * 1000)
        result["error"] = str(exc)[:2000]
        result["duration_ms"] = elapsed
        logger.warning("Webhook %s delivery failed: %s", webhook.id, exc)

    if log:
        entry = WebhookLog(
            webhook_id=webhook.id,
            evento=evento,
            payload=payload,
            status_code=result["status_code"],
            response_body=result["response_body"],
            error=result["error"],
            duration_ms=result["duration_ms"],
        )
        db.add(entry)
        db.commit()

    return result

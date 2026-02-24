"""
Celery tasks for webhook dispatch.
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.celery import celery_app
from app.core.database import SessionLocal
from app.models.webhook import Webhook, WebhookLog

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=5)
def dispatch_webhook_task(
    self,
    webhook_id: str,
    payload: dict,
    event_type: str
) -> dict:
    """
    Dispatch a webhook asynchronously with retry logic.
    
    Args:
        webhook_id: ID of the webhook configuration
        payload: Data to send
        event_type: Type of event (e.g., "lead.created")
    
    Returns:
        dict with dispatch results
    """
    db = SessionLocal()
    try:
        webhook = db.query(Webhook).filter(
            Webhook.id == webhook_id,
            Webhook.activo == True
        ).first()
        
        if not webhook:
            return {"status": "skipped", "reason": "webhook_not_found_or_inactive"}
        
        # Build headers
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": event_type,
            "X-Webhook-ID": webhook_id,
        }
        if webhook.secret:
            import hmac
            import hashlib
            signature = hmac.new(
                webhook.secret.encode(),
                str(payload).encode(),
                hashlib.sha256
            ).hexdigest()
            headers["X-Webhook-Signature"] = f"sha256={signature}"
        
        # Add custom headers
        if webhook.headers:
            headers.update(webhook.headers)
        
        # Send request
        start_time = datetime.now(timezone.utc)
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    webhook.url,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
            
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Log success
            log = WebhookLog(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                response_status=response.status_code,
                response_body=response.text[:1000] if response.text else None,
                duration_ms=int(duration_ms),
                success=True,
            )
            db.add(log)
            db.commit()
            
            return {
                "status": "delivered",
                "webhook_id": webhook_id,
                "http_status": response.status_code,
                "duration_ms": duration_ms,
            }
            
        except httpx.HTTPStatusError as e:
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Log failure
            log = WebhookLog(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                response_status=e.response.status_code,
                response_body=e.response.text[:1000] if e.response.text else str(e),
                duration_ms=int(duration_ms),
                success=False,
                error_message=f"HTTP {e.response.status_code}: {str(e)}",
            )
            db.add(log)
            db.commit()
            
            # Retry on server errors (5xx) or rate limits (429)
            if e.response.status_code >= 500 or e.response.status_code == 429:
                raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
            
            return {
                "status": "failed",
                "webhook_id": webhook_id,
                "error": f"HTTP {e.response.status_code}",
            }
            
        except httpx.RequestError as e:
            duration_ms = (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
            
            # Log failure
            log = WebhookLog(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                success=False,
                error_message=str(e),
            )
            db.add(log)
            db.commit()
            
            # Retry on network errors
            raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))
            
    finally:
        db.close()


@celery_app.task
def dispatch_bulk_webhooks(
    webhook_ids: list[str],
    payload: dict,
    event_type: str
) -> dict:
    """
    Dispatch webhooks to multiple endpoints in parallel.
    """
    from celery import group
    
    job = group(
        dispatch_webhook_task.s(wid, payload, event_type)
        for wid in webhook_ids
    )
    result = job.apply_async()
    
    return {
        "status": "launched",
        "count": len(webhook_ids),
        "group_id": result.id,
    }

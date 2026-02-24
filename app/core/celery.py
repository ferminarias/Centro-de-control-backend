"""
Celery configuration for async task processing.
"""
import os
from celery import Celery
from celery.signals import task_failure
import logging

logger = logging.getLogger(__name__)

# Redis broker URL from environment or default
BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/0")

celery_app = Celery(
    "centro_control",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=[
        "app.tasks.automations",
        "app.tasks.webhooks",
        "app.tasks.exports",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Argentina/Buenos_Aires",
    enable_utc=True,
    
    # Task execution
    task_always_eager=False,  # Set to True for testing (runs tasks synchronously)
    task_store_eager_result=False,
    
    # Result backend settings
    result_expires=3600 * 24,  # Results expire after 24 hours
    result_extended=True,
    
    # Worker settings
    worker_prefetch_multiplier=1,  # Process one task at a time per worker
    worker_max_tasks_per_child=1000,  # Restart worker after 1000 tasks (prevent memory leaks)
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Rate limiting
    task_default_rate_limit="100/m",  # Default: 100 tasks per minute
)


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, **kw):
    """Log task failures for monitoring."""
    logger.error(
        f"Task {sender.name} [{task_id}] failed: {exception}",
        extra={
            "task_id": task_id,
            "task_name": sender.name if sender else None,
            "args": args,
            "kwargs": kwargs,
        }
    )


def get_task_info(task_id: str) -> dict:
    """Get task status and result."""
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
    }

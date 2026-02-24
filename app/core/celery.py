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
    task_always_eager=False,
    task_store_eager_result=True,
    task_track_started=True,

    # Result backend settings
    result_expires=3600 * 24,  # 24 hours
    result_extended=True,

    # Worker settings
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,

    # Retry settings
    task_default_retry_delay=60,
    task_max_retries=3,

    # Rate limiting
    task_default_rate_limit="100/m",

    # Dead-letter queue: failed tasks go to 'dead_letter' queue after max retries
    task_queues={
        "default": {"exchange": "default", "routing_key": "default"},
        "dead_letter": {"exchange": "dead_letter", "routing_key": "dead_letter"},
    },
    task_default_queue="default",

    # Reject tasks that exceed max retries and route to dead_letter
    task_reject_on_worker_lost=True,
    task_acks_late=True,
)


@task_failure.connect
def handle_task_failure(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, **kw):
    """Log task failures and route to dead-letter queue after max retries."""
    logger.error(
        "Task %s [%s] failed: %s",
        sender.name if sender else "unknown",
        task_id,
        exception,
        extra={
            "task_id": task_id,
            "task_name": sender.name if sender else None,
        },
    )
    # Route to dead_letter queue if task has exhausted retries
    if sender and hasattr(sender, "request"):
        retries = getattr(sender.request, "retries", 0)
        max_retries = getattr(sender, "max_retries", 3)
        if retries >= max_retries:
            try:
                celery_app.send_task(
                    "dead_letter_handler",
                    args=[sender.name, task_id, str(exception), args, kwargs],
                    queue="dead_letter",
                )
                logger.warning("Task %s [%s] sent to dead_letter queue", sender.name, task_id)
            except Exception as e:
                logger.error("Failed to route to dead_letter queue: %s", e)


def get_task_info(task_id: str) -> dict:
    """Get task status and result."""
    result = celery_app.AsyncResult(task_id)
    info = {
        "task_id": task_id,
        "status": result.status,
        "result": None,
        "error": None,
        "date_done": None,
    }
    if result.ready():
        if result.successful():
            info["result"] = result.result
        else:
            info["error"] = str(result.result)
    if result.date_done:
        info["date_done"] = result.date_done.isoformat()
    return info

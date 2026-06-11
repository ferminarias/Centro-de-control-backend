"""
Background scheduler — auto-syncs WC2026 fixture every 5 minutes.
Uses APScheduler (in-process, no Redis/Celery needed).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import SessionLocal
from app.prode.services.sync import sync_wc_fixtures

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None

SYNC_INTERVAL_MINUTES = 5


def _run_sync() -> None:
    api_key = getattr(settings, "FOOTBALL_DATA_API_KEY", "")
    if not api_key:
        logger.debug("Auto-sync skipped: FOOTBALL_DATA_API_KEY not set")
        return

    db = SessionLocal()
    try:
        result = sync_wc_fixtures(db, api_key)
        logger.info(
            "Auto-sync OK — creados=%d actualizados=%d puntuados=%d",
            result.get("partidos_creados", 0),
            result.get("partidos_actualizados", 0),
            result.get("predicciones_puntuadas", 0),
        )
        if result.get("equipos_sin_match"):
            logger.warning("Auto-sync equipos sin match: %s", result["equipos_sin_match"])
    except Exception as exc:
        logger.error("Auto-sync error: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        _run_sync,
        trigger=IntervalTrigger(minutes=SYNC_INTERVAL_MINUTES),
        next_run_time=datetime.now(timezone.utc),  # primera corrida inmediata, no a los 5 min
        id="prode_sync",
        replace_existing=True,
        max_instances=1,  # never overlap
    )
    _scheduler.start()
    logger.info("Prode auto-sync scheduler started (every %d min)", SYNC_INTERVAL_MINUTES)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Prode auto-sync scheduler stopped")

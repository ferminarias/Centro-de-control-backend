"""
Celery tasks for automation execution.
"""
import logging
from datetime import datetime, timezone
from typing import Any

from celery import chain, group

from app.core.celery import celery_app
from app.core.database import SessionLocal
from app.models.automation import Automation, AutomationLog
from app.models.lead import Lead
from app.services.automation_engine import evaluate_condition, execute_action

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def run_automation_task(
    self,
    automation_id: str,
    trigger_event: str,
    lead_id: str,
    context: dict | None = None
) -> dict:
    """
    Execute an automation workflow asynchronously.
    
    Args:
        automation_id: ID of the automation to run
        trigger_event: Event that triggered the automation (e.g., "lead_created")
        lead_id: ID of the lead involved
        context: Additional context data
    
    Returns:
        dict with execution results
    """
    db = SessionLocal()
    try:
        # Fetch automation and lead
        automation = db.query(Automation).filter(
            Automation.id == automation_id,
            Automation.activo == True
        ).first()
        
        if not automation:
            logger.warning(f"Automation {automation_id} not found or inactive")
            return {"status": "skipped", "reason": "automation_not_found"}
        
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            logger.warning(f"Lead {lead_id} not found")
            return {"status": "failed", "reason": "lead_not_found"}
        
        # Create execution log
        log = AutomationLog(
            automation_id=automation.id,
            lead_id=lead.id,
            trigger_event=trigger_event,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(log)
        db.commit()
        
        # Evaluate conditions
        conditions_met = True
        for condition in automation.conditions:
            if not evaluate_condition(condition, lead):
                conditions_met = False
                break
        
        if not conditions_met:
            log.status = "conditions_not_met"
            log.completed_at = datetime.now(timezone.utc)
            db.commit()
            return {"status": "skipped", "reason": "conditions_not_met"}
        
        # Execute actions
        results = []
        for action in automation.actions:
            try:
                result = execute_action(action, lead, context or {})
                results.append({"action": action.tipo, "status": "success", "result": result})
            except Exception as e:
                results.append({"action": action.tipo, "status": "failed", "error": str(e)})
                logger.error(f"Action {action.tipo} failed: {e}")
        
        # Update log
        log.status = "completed"
        log.result = {"actions": results}
        log.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        return {
            "status": "completed",
            "automation_id": automation_id,
            "lead_id": lead_id,
            "actions_executed": len(results),
            "results": results,
        }
        
    except Exception as exc:
        logger.exception(f"Automation task failed: {exc}")
        
        # Update log if it exists
        try:
            if 'log' in locals() and log:
                log.status = "failed"
                log.error_message = str(exc)
                log.completed_at = datetime.now(timezone.utc)
                db.commit()
        except:
            pass
        
        # Retry with exponential backoff
        retry_count = self.request.retries
        countdown = 60 * (2 ** retry_count)  # 1min, 2min, 4min
        raise self.retry(exc=exc, countdown=countdown)
        
    finally:
        db.close()


@celery_app.task
def run_automations_for_event(
    cuenta_id: str,
    trigger_event: str,
    lead_id: str,
    context: dict | None = None
) -> dict:
    """
    Run all active automations for a given event.
    This is the main entry point called from webhooks/API.
    """
    db = SessionLocal()
    try:
        # Find all active automations for this event and account
        automations = db.query(Automation).filter(
            Automation.cuenta_id == cuenta_id,
            Automation.activo == True,
            Automation.disparador == trigger_event
        ).all()
        
        if not automations:
            return {"status": "no_automations", "count": 0}
        
        # Launch automation tasks in parallel
        job = group(
            run_automation_task.s(str(a.id), trigger_event, lead_id, context)
            for a in automations
        )
        result = job.apply_async()
        
        return {
            "status": "launched",
            "count": len(automations),
            "group_id": result.id,
        }
        
    finally:
        db.close()


@celery_app.task
def cleanup_old_automation_logs(days: int = 30) -> dict:
    """
    Delete automation logs older than specified days.
    Run this periodically (e.g., daily) to prevent table bloat.
    """
    from sqlalchemy import text
    
    db = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - __import__('datetime').timedelta(days=days)
        
        result = db.execute(
            text("DELETE FROM automation_logs WHERE created_at < :cutoff"),
            {"cutoff": cutoff}
        )
        db.commit()
        
        deleted_count = result.rowcount
        logger.info(f"Cleaned up {deleted_count} old automation logs")
        
        return {"status": "completed", "deleted": deleted_count}
        
    finally:
        db.close()

"""
Evaluates and executes automations when a trigger event fires.

Usage:
    from app.services.automation_engine import run_automations
    run_automations(db, cuenta_id, "lead_created", lead=lead_obj)

Best-effort: failures are logged per-automation, never raised to the caller.
"""

import json
import logging
import time
import uuid
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.models.automation import Automation, AutomationAction, AutomationCondition, AutomationLog
from app.models.lead import Lead
from app.models.lead_base import LeadBase

logger = logging.getLogger(__name__)

_TIMEOUT = 10


# ── Public entry point ─────────────────────────────────────────────────────

def run_automations(
    db: Session,
    cuenta_id: uuid.UUID,
    evento: str,
    lead: Lead | None = None,
    extra_context: dict | None = None,
) -> None:
    """Evaluate all active automations for this account + trigger type."""
    automations = (
        db.query(Automation)
        .filter(
            Automation.cuenta_id == cuenta_id,
            Automation.trigger_tipo == evento,
            Automation.activo.is_(True),
        )
        .all()
    )

    context: dict[str, Any] = extra_context or {}
    if lead:
        context["lead_id"] = str(lead.id)
        context["datos"] = lead.datos

    for auto in automations:
        _execute_automation(db, auto, lead, context)


# ── Internal ───────────────────────────────────────────────────────────────

def _execute_automation(
    db: Session,
    auto: Automation,
    lead: Lead | None,
    context: dict,
) -> None:
    try:
        passed = _evaluate_conditions(auto.conditions, context.get("datos", {}))

        actions_result: list[dict] = []
        if passed:
            for action in sorted(auto.actions, key=lambda a: a.orden):
                result = _execute_action(db, action, lead, context)
                actions_result.append(result)

        log_entry = AutomationLog(
            automation_id=auto.id,
            lead_id=lead.id if lead else None,
            trigger_evento=auto.trigger_tipo,
            conditions_passed=passed,
            actions_result=actions_result if actions_result else None,
        )
        db.add(log_entry)
        db.commit()

    except Exception as exc:
        logger.error("Automation %s failed: %s", auto.id, exc)
        log_entry = AutomationLog(
            automation_id=auto.id,
            lead_id=lead.id if lead else None,
            trigger_evento=auto.trigger_tipo,
            conditions_passed=False,
            error=str(exc)[:2000],
        )
        db.add(log_entry)
        db.commit()


def _evaluate_conditions(conditions: list[AutomationCondition], datos: dict) -> bool:
    """All conditions must pass (AND logic)."""
    for cond in sorted(conditions, key=lambda c: c.orden):
        field_val = str(datos.get(cond.campo, ""))
        cmp_val = cond.valor

        match cond.operador:
            case "equals":
                if field_val != cmp_val:
                    return False
            case "not_equals":
                if field_val == cmp_val:
                    return False
            case "contains":
                if cmp_val not in field_val:
                    return False
            case "not_contains":
                if cmp_val in field_val:
                    return False
            case "greater_than":
                try:
                    if float(field_val) <= float(cmp_val):
                        return False
                except (ValueError, TypeError):
                    return False
            case "less_than":
                try:
                    if float(field_val) >= float(cmp_val):
                        return False
                except (ValueError, TypeError):
                    return False
            case "is_empty":
                if field_val:
                    return False
            case "is_not_empty":
                if not field_val:
                    return False
            case _:
                logger.warning("Unknown operator: %s", cond.operador)
                return False
    return True


def _execute_action(
    db: Session,
    action: AutomationAction,
    lead: Lead | None,
    context: dict,
) -> dict:
    """Execute a single action and return a result dict."""
    result: dict[str, Any] = {
        "action_id": str(action.id),
        "tipo": action.tipo,
        "success": False,
        "detail": None,
    }

    try:
        match action.tipo:
            case "webhook":
                result.update(_action_webhook(action.config, context))
            case "move_to_base":
                result.update(_action_move_to_base(db, action.config, lead))
            case "update_field":
                result.update(_action_update_field(db, action.config, lead))
            case "send_notification":
                result.update(_action_send_notification(action.config, context))
            case _:
                result["detail"] = f"Unknown action type: {action.tipo}"
    except Exception as exc:
        result["detail"] = str(exc)[:500]

    return result


# ── Action handlers ────────────────────────────────────────────────────────

def _action_webhook(config: dict, context: dict) -> dict:
    """POST context data to an external URL."""
    url = config.get("url", "")
    method = config.get("method", "POST").upper()
    headers = {"Content-Type": "application/json"}
    headers.update(config.get("headers", {}))
    body = json.dumps(config.get("body") or context, default=str).encode()

    start = time.monotonic()
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.request(method, url, content=body, headers=headers)
    elapsed = int((time.monotonic() - start) * 1000)

    return {
        "success": 200 <= resp.status_code < 300,
        "detail": f"{resp.status_code} in {elapsed}ms",
    }


def _action_move_to_base(db: Session, config: dict, lead: Lead | None) -> dict:
    """Move the lead to a different base."""
    if not lead:
        return {"detail": "No lead in context"}

    base_id = config.get("base_id")
    if not base_id:
        return {"detail": "No base_id in config"}

    base = db.query(LeadBase).filter(LeadBase.id == base_id).first()
    if not base:
        return {"detail": f"Base {base_id} not found"}

    lead.lead_base_id = base.id
    db.flush()
    return {"success": True, "detail": f"Moved to base '{base.nombre}'"}


def _action_update_field(db: Session, config: dict, lead: Lead | None) -> dict:
    """Set a field value on the lead's datos JSONB."""
    if not lead:
        return {"detail": "No lead in context"}

    campo = config.get("campo")
    valor = config.get("valor")
    if not campo:
        return {"detail": "No campo in config"}

    datos = dict(lead.datos)
    datos[campo] = valor
    lead.datos = datos
    db.flush()
    return {"success": True, "detail": f"Set {campo}={valor}"}


def _action_send_notification(config: dict, context: dict) -> dict:
    """
    Placeholder for future notification channel (email, Slack, etc.).
    For now, just logs and returns success.
    """
    channel = config.get("channel", "log")
    message = config.get("message", "Automation triggered")
    logger.info("Notification [%s]: %s | context keys=%s", channel, message, list(context.keys()))
    return {"success": True, "detail": f"Notified via {channel}"}

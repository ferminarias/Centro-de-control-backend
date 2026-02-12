import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.lead_base import LeadBase

logger = logging.getLogger(__name__)

VALID_OPERATORS = {"equals", "not_equals", "contains", "greater_than", "less_than"}


def evaluate_routing(db: Session, cuenta_id: uuid.UUID, payload: dict[str, Any]) -> uuid.UUID | None:
    """Evaluate routing rules and return the matching lead_base_id."""
    bases = (
        db.query(LeadBase)
        .options(joinedload(LeadBase.routing_rules))
        .filter(LeadBase.cuenta_id == cuenta_id)
        .all()
    )

    if not bases:
        return None

    default_base: LeadBase | None = None

    # Sort non-default bases by their rules' priority (min priority of rules)
    non_default_bases: list[LeadBase] = []
    for base in bases:
        if base.es_default:
            default_base = base
        else:
            non_default_bases.append(base)

    # Sort by minimum priority of rules (lower = higher priority)
    non_default_bases.sort(
        key=lambda b: min((r.prioridad for r in b.routing_rules), default=999999)
    )

    for base in non_default_bases:
        if not base.routing_rules:
            continue
        if all(_evaluate_condition(rule.campo, rule.operador, rule.valor, payload) for rule in base.routing_rules):
            logger.info("Lead routed to base '%s' (%s)", base.nombre, base.id)
            return base.id

    if default_base:
        logger.info("Lead routed to default base '%s' (%s)", default_base.nombre, default_base.id)
        return default_base.id

    return None


def _evaluate_condition(campo: str, operador: str, valor: str, payload: dict[str, Any]) -> bool:
    """Evaluate a single routing condition against the payload."""
    payload_value = payload.get(campo)
    if payload_value is None:
        return False

    try:
        if operador == "equals":
            return str(payload_value) == valor
        elif operador == "not_equals":
            return str(payload_value) != valor
        elif operador == "contains":
            return valor in str(payload_value)
        elif operador == "greater_than":
            return float(payload_value) > float(valor)
        elif operador == "less_than":
            return float(payload_value) < float(valor)
    except (ValueError, TypeError):
        logger.warning("Could not evaluate condition: %s %s %s (payload value: %s)", campo, operador, valor, payload_value)
        return False

    return False

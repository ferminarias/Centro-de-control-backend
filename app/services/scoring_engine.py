"""
Lead scoring engine.

Calculates a 0-100 score for each lead based on data completeness,
engagement signals, and classification state. Called on ingest and update.

Score breakdown:
  +15  email present and non-empty
  +15  phone present and non-empty
  +10  nombre (first name) present
  +5   apellido (last name) present
  +20  tipificacion assigned
  +10  subtipificacion assigned
  +15  temperatura: frio=0 / tibio=8 / caliente=15
  +10  assigned to a user (assigned_to set)
"""
import logging
import uuid

from sqlalchemy.orm import Session

from app.models.lead import Lead

logger = logging.getLogger(__name__)

_PHONE_FIELDS = {"telefono", "phone", "tel", "celular", "movil"}
_EMAIL_FIELDS = {"email", "correo", "mail"}
_TEMP_SCORES = {"frio": 0, "tibio": 8, "caliente": 15}


def calculate_score(lead: Lead) -> int:
    """Compute a 0-100 score for the given lead object (does NOT persist)."""
    datos = lead.datos or {}
    score = 0

    # Email
    for field in _EMAIL_FIELDS:
        val = datos.get(field, "")
        if val and str(val).strip():
            score += 15
            break

    # Phone
    for field in _PHONE_FIELDS:
        val = datos.get(field, "")
        if val and str(val).strip():
            score += 15
            break

    # Name
    if str(datos.get("nombre", "")).strip():
        score += 10
    if str(datos.get("apellido", "")).strip():
        score += 5

    # Tipificacion
    if lead.tipificacion_id:
        score += 20
    if lead.subtipificacion_id:
        score += 10

    # Temperatura
    temp = (lead.temperatura or "").lower()
    score += _TEMP_SCORES.get(temp, 0)

    # Assigned
    if lead.assigned_to:
        score += 10

    return min(score, 100)


def recalculate_and_save(db: Session, lead: Lead) -> int:
    """Calculate score, persist it, and return the new value."""
    new_score = calculate_score(lead)
    if lead.score != new_score:
        lead.score = new_score
        db.add(lead)
    return new_score


def recalculate_bulk(db: Session, cuenta_id: uuid.UUID) -> int:
    """Recalculate scores for all leads in an account. Returns number updated."""
    leads = db.query(Lead).filter(Lead.cuenta_id == cuenta_id).all()
    updated = 0
    for lead in leads:
        new_score = calculate_score(lead)
        if lead.score != new_score:
            lead.score = new_score
            db.add(lead)
            updated += 1
    db.commit()
    logger.info("Recalculated scores for %d leads in account %s", updated, cuenta_id)
    return updated

"""
Generates the next sequential id_lead for a given account.
Each account has its own independent counter starting at 1.
"""

import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.lead import Lead


def next_id_lead(db: Session, cuenta_id: uuid.UUID) -> int:
    """Return the next available id_lead for the account."""
    max_id = (
        db.query(func.max(Lead.id_lead))
        .filter(Lead.cuenta_id == cuenta_id)
        .scalar()
    )
    return (max_id or 0) + 1

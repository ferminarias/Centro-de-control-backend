import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.lead import Lead
from app.models.lead_base import LeadBase
from app.models.lote import Lote
from app.schemas.lead import LeadListResponse, LeadResponse

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get(
    "/accounts/{account_id}/leads",
    response_model=LeadListResponse,
    summary="List leads for an account",
)
def list_leads(
    account_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    query = db.query(Lead).filter(Lead.cuenta_id == account_id)
    total = query.count()
    leads = (
        query.order_by(Lead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Fetch base names for leads that have a base assigned
    base_ids = {l.lead_base_id for l in leads if l.lead_base_id}
    base_names: dict[uuid.UUID, str] = {}
    if base_ids:
        bases = db.query(LeadBase.id, LeadBase.nombre).filter(LeadBase.id.in_(base_ids)).all()
        base_names = {b.id: b.nombre for b in bases}

    # Fetch lote names for leads that have a lote assigned
    lote_ids = {l.lote_id for l in leads if l.lote_id}
    lote_names: dict[uuid.UUID, str] = {}
    if lote_ids:
        lotes = db.query(Lote.id, Lote.nombre).filter(Lote.id.in_(lote_ids)).all()
        lote_names = {lo.id: lo.nombre for lo in lotes}

    items = []
    for lead in leads:
        items.append({
            "id": lead.id,
            "cuenta_id": lead.cuenta_id,
            "record_id": lead.record_id,
            "lead_base_id": lead.lead_base_id,
            "base_nombre": base_names.get(lead.lead_base_id) if lead.lead_base_id else None,
            "lote_id": lead.lote_id,
            "lote_nombre": lote_names.get(lead.lote_id) if lead.lote_id else None,
            "datos": lead.datos,
            "created_at": lead.created_at,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/leads/{lead_id}",
    response_model=LeadResponse,
    summary="Get lead details",
)
def get_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    base_nombre = None
    if lead.lead_base_id:
        base = db.query(LeadBase.nombre).filter(LeadBase.id == lead.lead_base_id).first()
        if base:
            base_nombre = base.nombre

    lote_nombre = None
    if lead.lote_id:
        lote = db.query(Lote.nombre).filter(Lote.id == lead.lote_id).first()
        if lote:
            lote_nombre = lote.nombre

    return {
        "id": lead.id,
        "cuenta_id": lead.cuenta_id,
        "record_id": lead.record_id,
        "lead_base_id": lead.lead_base_id,
        "base_nombre": base_nombre,
        "lote_id": lead.lote_id,
        "lote_nombre": lote_nombre,
        "datos": lead.datos,
        "created_at": lead.created_at,
    }

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.lead import Lead
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
    items = (
        query.order_by(Lead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/leads/{lead_id}",
    response_model=LeadResponse,
    summary="Get lead details",
)
def get_lead(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Lead:
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

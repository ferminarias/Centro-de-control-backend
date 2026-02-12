import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.record import Record
from app.schemas.record import RecordListResponse, RecordResponse

router = APIRouter(dependencies=[Depends(verify_admin_key)])


@router.get(
    "/accounts/{account_id}/records",
    response_model=RecordListResponse,
    summary="List records for an account",
)
def list_records(
    account_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    query = db.query(Record).filter(Record.cuenta_id == account_id)
    total = query.count()
    items = (
        query.order_by(Record.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total, "page": page, "page_size": page_size}


@router.get(
    "/records/{record_id}",
    response_model=RecordResponse,
    summary="Get record details",
)
def get_record(
    record_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Record:
    record = db.query(Record).filter(Record.id == record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

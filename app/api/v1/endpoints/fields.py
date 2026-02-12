import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.field import CustomField
from app.schemas.field import FieldCreate, FieldListResponse, FieldResponse, FieldUpdate

router = APIRouter(dependencies=[Depends(verify_admin_key)])


def _get_account_or_404(db: Session, account_id: uuid.UUID) -> Account:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.get(
    "/accounts/{account_id}/fields",
    response_model=FieldListResponse,
    summary="List fields for an account",
)
def list_fields(
    account_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> dict:
    _get_account_or_404(db, account_id)
    query = db.query(CustomField).filter(CustomField.cuenta_id == account_id)
    total = query.count()
    items = (
        query.order_by(CustomField.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total}


@router.post(
    "/accounts/{account_id}/fields",
    response_model=FieldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a field manually",
)
def create_field(
    account_id: uuid.UUID,
    data: FieldCreate,
    db: Session = Depends(get_db),
) -> CustomField:
    _get_account_or_404(db, account_id)

    exists = (
        db.query(CustomField)
        .filter(
            CustomField.cuenta_id == account_id,
            CustomField.nombre_campo == data.nombre_campo,
        )
        .first()
    )
    if exists:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Field '{data.nombre_campo}' already exists for this account",
        )

    field = CustomField(cuenta_id=account_id, **data.model_dump())
    db.add(field)
    db.commit()
    db.refresh(field)
    return field


@router.put(
    "/fields/{field_id}",
    response_model=FieldResponse,
    summary="Update a field",
)
def update_field(
    field_id: uuid.UUID,
    data: FieldUpdate,
    db: Session = Depends(get_db),
) -> CustomField:
    field = db.query(CustomField).filter(CustomField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(field, key, value)
    db.commit()
    db.refresh(field)
    return field


@router.delete(
    "/fields/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a field",
)
def delete_field(
    field_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    field = db.query(CustomField).filter(CustomField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Field not found")
    db.delete(field)
    db.commit()

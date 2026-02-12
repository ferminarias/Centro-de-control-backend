import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.schemas.account import (
    AccountCreate,
    AccountListResponse,
    AccountResponse,
    AccountUpdate,
)

router = APIRouter(dependencies=[Depends(verify_admin_key)])


def _generate_api_key() -> str:
    return f"cc_{secrets.token_urlsafe(32)}"


def _get_account_or_404(db: Session, account_id: uuid.UUID) -> Account:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


@router.post(
    "/accounts",
    response_model=AccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
def create_account(
    data: AccountCreate,
    db: Session = Depends(get_db),
) -> Account:
    account = Account(
        nombre=data.nombre,
        api_key=_generate_api_key(),
        auto_crear_campos=data.auto_crear_campos,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get(
    "/accounts",
    response_model=AccountListResponse,
    summary="List all accounts",
)
def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    query = db.query(Account).filter(Account.activo.is_(True))
    total = query.count()
    items = (
        query.order_by(Account.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total}


@router.get(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    summary="Get account details",
)
def get_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Account:
    return _get_account_or_404(db, account_id)


@router.put(
    "/accounts/{account_id}",
    response_model=AccountResponse,
    summary="Update account",
)
def update_account(
    account_id: uuid.UUID,
    data: AccountUpdate,
    db: Session = Depends(get_db),
) -> Account:
    account = _get_account_or_404(db, account_id)
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)
    db.commit()
    db.refresh(account)
    return account


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete account",
)
def delete_account(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    account = _get_account_or_404(db, account_id)
    account.activo = False
    db.commit()


@router.patch(
    "/accounts/{account_id}/toggle-auto-create",
    response_model=AccountResponse,
    summary="Toggle auto-create fields",
)
def toggle_auto_create(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> Account:
    account = _get_account_or_404(db, account_id)
    account.auto_crear_campos = not account.auto_crear_campos
    db.commit()
    db.refresh(account)
    return account

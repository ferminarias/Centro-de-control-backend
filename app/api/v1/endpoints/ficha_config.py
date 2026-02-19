import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.campaign import Campania
from app.models.ficha_config import FichaConfig
from app.schemas.ficha_config import (
    AvailableFieldsResponse,
    FichaConfigCreate,
    FichaConfigResponse,
    FichaConfigUpdate,
)

router = APIRouter(dependencies=[Depends(verify_admin_key)])


def _get_account_or_404(db: Session, cuenta_id: uuid.UUID) -> Account:
    account = db.query(Account).filter(Account.id == cuenta_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    return account


def resolve_ficha_config(
    db: Session, cuenta_id: uuid.UUID, campania_id: uuid.UUID | None
) -> FichaConfig | None:
    """
    Resolve ficha config with fallback:
    1. Config for specific campania_id
    2. Default config (campania_id IS NULL)
    3. None
    """
    if campania_id:
        config = db.query(FichaConfig).filter(
            FichaConfig.cuenta_id == cuenta_id,
            FichaConfig.campania_id == campania_id,
        ).first()
        if config:
            return config

    # Fallback to account default
    return db.query(FichaConfig).filter(
        FichaConfig.cuenta_id == cuenta_id,
        FichaConfig.campania_id.is_(None),
    ).first()


@router.get(
    "/accounts/{cuenta_id}/ficha-config",
    response_model=FichaConfigResponse,
    summary="Get ficha config (with campaign fallback)",
)
def get_ficha_config(
    cuenta_id: uuid.UUID,
    campania_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
) -> FichaConfig:
    _get_account_or_404(db, cuenta_id)
    config = resolve_ficha_config(db, cuenta_id, campania_id)
    if not config:
        raise HTTPException(status_code=404, detail="No ficha config found")
    return config


@router.put(
    "/accounts/{cuenta_id}/ficha-config",
    response_model=FichaConfigResponse,
    summary="Upsert ficha config",
)
def upsert_ficha_config(
    cuenta_id: uuid.UUID,
    data: FichaConfigCreate,
    db: Session = Depends(get_db),
) -> FichaConfig:
    _get_account_or_404(db, cuenta_id)

    if data.campania_id:
        campania = db.query(Campania).filter(
            Campania.id == data.campania_id,
            Campania.cuenta_id == cuenta_id,
        ).first()
        if not campania:
            raise HTTPException(status_code=404, detail="Campania not found or does not belong to this account")

    existing = db.query(FichaConfig).filter(
        FichaConfig.cuenta_id == cuenta_id,
        FichaConfig.campania_id == data.campania_id if data.campania_id else FichaConfig.campania_id.is_(None),
    ).first()

    campos_dicts = [c.model_dump() for c in data.campos]

    if existing:
        existing.campos = campos_dicts
        db.commit()
        db.refresh(existing)
        return existing

    config = FichaConfig(
        cuenta_id=cuenta_id,
        campania_id=data.campania_id,
        campos=campos_dicts,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.delete(
    "/accounts/{cuenta_id}/ficha-config",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete ficha config",
)
def delete_ficha_config(
    cuenta_id: uuid.UUID,
    campania_id: uuid.UUID | None = Query(None),
    db: Session = Depends(get_db),
) -> None:
    _get_account_or_404(db, cuenta_id)

    query = db.query(FichaConfig).filter(FichaConfig.cuenta_id == cuenta_id)
    if campania_id:
        query = query.filter(FichaConfig.campania_id == campania_id)
    else:
        query = query.filter(FichaConfig.campania_id.is_(None))

    config = query.first()
    if not config:
        raise HTTPException(status_code=404, detail="Ficha config not found")

    db.delete(config)
    db.commit()


@router.get(
    "/accounts/{cuenta_id}/ficha-config/available-fields",
    response_model=AvailableFieldsResponse,
    summary="Get available lead data fields",
)
def get_available_fields(
    cuenta_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    _get_account_or_404(db, cuenta_id)

    result = db.execute(
        text(
            "SELECT DISTINCT jsonb_object_keys(datos) AS key "
            "FROM leads WHERE cuenta_id = :cuenta_id ORDER BY key"
        ),
        {"cuenta_id": str(cuenta_id)},
    )
    fields = [row[0] for row in result]
    return {"fields": fields}

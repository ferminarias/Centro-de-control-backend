import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.automation import (
    Automation,
    AutomationAction,
    AutomationCondition,
    AutomationLog,
)
from app.schemas.automation import (
    ACTION_TYPES,
    CONDITION_OPERATORS,
    TRIGGER_TYPES,
    ActionCreate,
    ActionResponse,
    AutomationCreate,
    AutomationListResponse,
    AutomationLogListResponse,
    AutomationMetaResponse,
    AutomationResponse,
    AutomationUpdate,
    ConditionCreate,
    ConditionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(verify_admin_key)])


# ── Helpers ────────────────────────────────────────────────────────────────

def _validate_trigger(tipo: str) -> None:
    if tipo not in TRIGGER_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger: {tipo}. Valid: {', '.join(TRIGGER_TYPES)}",
        )


def _validate_action_type(tipo: str) -> None:
    if tipo not in ACTION_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid action type: {tipo}. Valid: {', '.join(ACTION_TYPES)}",
        )


def _validate_operator(op: str) -> None:
    if op not in CONDITION_OPERATORS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid operator: {op}. Valid: {', '.join(CONDITION_OPERATORS)}",
        )


def _automation_to_response(auto: Automation) -> dict:
    return {
        "id": auto.id,
        "cuenta_id": auto.cuenta_id,
        "nombre": auto.nombre,
        "descripcion": auto.descripcion,
        "trigger_tipo": auto.trigger_tipo,
        "trigger_config": auto.trigger_config,
        "activo": auto.activo,
        "conditions": [
            {"id": c.id, "campo": c.campo, "operador": c.operador, "valor": c.valor, "orden": c.orden}
            for c in sorted(auto.conditions, key=lambda c: c.orden)
        ],
        "actions": [
            {"id": a.id, "tipo": a.tipo, "config": a.config, "orden": a.orden}
            for a in sorted(auto.actions, key=lambda a: a.orden)
        ],
        "created_at": auto.created_at,
        "updated_at": auto.updated_at,
    }


# ── CRUD ───────────────────────────────────────────────────────────────────

@router.post(
    "/accounts/{account_id}/automations",
    response_model=AutomationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an automation with conditions and actions",
)
def create_automation(
    account_id: uuid.UUID,
    body: AutomationCreate,
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    _validate_trigger(body.trigger_tipo)
    for c in body.conditions:
        _validate_operator(c.operador)
    for a in body.actions:
        _validate_action_type(a.tipo)

    auto = Automation(
        cuenta_id=account_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        trigger_tipo=body.trigger_tipo,
        trigger_config=body.trigger_config,
        activo=body.activo,
    )
    db.add(auto)
    db.flush()

    for c in body.conditions:
        db.add(AutomationCondition(
            automation_id=auto.id,
            campo=c.campo,
            operador=c.operador,
            valor=c.valor,
            orden=c.orden,
        ))

    for a in body.actions:
        db.add(AutomationAction(
            automation_id=auto.id,
            tipo=a.tipo,
            config=a.config,
            orden=a.orden,
        ))

    db.commit()
    db.refresh(auto)

    logger.info("Automation '%s' created for account %s", auto.nombre, account_id)
    return _automation_to_response(auto)


@router.get(
    "/accounts/{account_id}/automations",
    response_model=AutomationListResponse,
    summary="List automations for an account",
)
def list_automations(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    autos = (
        db.query(Automation)
        .filter(Automation.cuenta_id == account_id)
        .order_by(Automation.created_at.desc())
        .all()
    )
    return {"items": [_automation_to_response(a) for a in autos], "total": len(autos)}


@router.get(
    "/automations/{automation_id}",
    response_model=AutomationResponse,
    summary="Get automation details",
)
def get_automation(
    automation_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    auto = db.query(Automation).filter(Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")
    return _automation_to_response(auto)


@router.put(
    "/automations/{automation_id}",
    response_model=AutomationResponse,
    summary="Update automation basic info",
)
def update_automation(
    automation_id: uuid.UUID,
    body: AutomationUpdate,
    db: Session = Depends(get_db),
) -> dict:
    auto = db.query(Automation).filter(Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")

    if body.nombre is not None:
        auto.nombre = body.nombre
    if body.descripcion is not None:
        auto.descripcion = body.descripcion
    if body.trigger_tipo is not None:
        _validate_trigger(body.trigger_tipo)
        auto.trigger_tipo = body.trigger_tipo
    if body.trigger_config is not None:
        auto.trigger_config = body.trigger_config
    if body.activo is not None:
        auto.activo = body.activo

    db.commit()
    db.refresh(auto)
    return _automation_to_response(auto)


@router.delete(
    "/automations/{automation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an automation",
)
def delete_automation(
    automation_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    auto = db.query(Automation).filter(Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")
    db.delete(auto)
    db.commit()
    logger.info("Automation '%s' deleted", auto.nombre)


# ── Conditions CRUD ────────────────────────────────────────────────────────

@router.post(
    "/automations/{automation_id}/conditions",
    response_model=ConditionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a condition to an automation",
)
def add_condition(
    automation_id: uuid.UUID,
    body: ConditionCreate,
    db: Session = Depends(get_db),
) -> AutomationCondition:
    auto = db.query(Automation).filter(Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")

    _validate_operator(body.operador)

    cond = AutomationCondition(
        automation_id=automation_id,
        campo=body.campo,
        operador=body.operador,
        valor=body.valor,
        orden=body.orden,
    )
    db.add(cond)
    db.commit()
    db.refresh(cond)
    return cond


@router.delete(
    "/automation-conditions/{condition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a condition",
)
def delete_condition(
    condition_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    cond = db.query(AutomationCondition).filter(AutomationCondition.id == condition_id).first()
    if not cond:
        raise HTTPException(status_code=404, detail="Condition not found")
    db.delete(cond)
    db.commit()


# ── Actions CRUD ───────────────────────────────────────────────────────────

@router.post(
    "/automations/{automation_id}/actions",
    response_model=ActionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an action to an automation",
)
def add_action(
    automation_id: uuid.UUID,
    body: ActionCreate,
    db: Session = Depends(get_db),
) -> AutomationAction:
    auto = db.query(Automation).filter(Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")

    _validate_action_type(body.tipo)

    action = AutomationAction(
        automation_id=automation_id,
        tipo=body.tipo,
        config=body.config,
        orden=body.orden,
    )
    db.add(action)
    db.commit()
    db.refresh(action)
    return action


@router.delete(
    "/automation-actions/{action_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an action",
)
def delete_action(
    action_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    action = db.query(AutomationAction).filter(AutomationAction.id == action_id).first()
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    db.delete(action)
    db.commit()


# ── Logs ───────────────────────────────────────────────────────────────────

@router.get(
    "/automations/{automation_id}/logs",
    response_model=AutomationLogListResponse,
    summary="List execution logs for an automation",
)
def list_automation_logs(
    automation_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    auto = db.query(Automation).filter(Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")

    query = db.query(AutomationLog).filter(AutomationLog.automation_id == automation_id)
    total = query.count()
    items = (
        query.order_by(AutomationLog.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": items, "total": total}


# ── Toggle ─────────────────────────────────────────────────────────────────

@router.patch(
    "/automations/{automation_id}/toggle",
    response_model=AutomationResponse,
    summary="Toggle automation active/inactive",
)
def toggle_automation(
    automation_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    auto = db.query(Automation).filter(Automation.id == automation_id).first()
    if not auto:
        raise HTTPException(status_code=404, detail="Automation not found")
    auto.activo = not auto.activo
    db.commit()
    db.refresh(auto)
    return _automation_to_response(auto)


# ── Meta ───────────────────────────────────────────────────────────────────

@router.get(
    "/automation-meta",
    response_model=AutomationMetaResponse,
    summary="List trigger types, action types, and condition operators",
)
def automation_meta() -> dict:
    return {
        "trigger_types": TRIGGER_TYPES,
        "action_types": ACTION_TYPES,
        "condition_operators": CONDITION_OPERATORS,
    }

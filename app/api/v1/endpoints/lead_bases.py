import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from sqlalchemy import func

from app.core.database import get_db
from app.core.security import verify_admin_key
from app.models.account import Account
from app.models.lead import Lead
from app.models.lead_base import LeadBase
from app.models.routing_rule import RoutingRule
from app.schemas.lead import LeadListResponse
from app.schemas.lead_base import (
    LeadBaseCreate,
    LeadBaseListResponse,
    LeadBaseResponse,
    LeadBaseUpdate,
    MoveLeadsRequest,
    MoveLeadsResponse,
    RoutingRuleCreate,
    RoutingRuleListResponse,
    RoutingRuleResponse,
    RoutingRuleUpdate,
)

router = APIRouter(dependencies=[Depends(verify_admin_key)])


# --- Lead Bases ---


@router.post(
    "/accounts/{account_id}/bases",
    response_model=LeadBaseResponse,
    status_code=201,
    summary="Create a lead base",
)
def create_lead_base(
    account_id: uuid.UUID,
    body: LeadBaseCreate,
    db: Session = Depends(get_db),
) -> LeadBase:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # If this is the first base for the account, make it default
    existing_count = db.query(LeadBase).filter(LeadBase.cuenta_id == account_id).count()
    if existing_count == 0:
        body.es_default = True

    # If marking as default, unset previous default
    if body.es_default:
        db.query(LeadBase).filter(
            LeadBase.cuenta_id == account_id, LeadBase.es_default.is_(True)
        ).update({"es_default": False})

    lead_base = LeadBase(
        cuenta_id=account_id,
        nombre=body.nombre,
        es_default=body.es_default,
    )
    db.add(lead_base)
    db.commit()
    db.refresh(lead_base)
    return lead_base


@router.get(
    "/accounts/{account_id}/bases",
    response_model=LeadBaseListResponse,
    summary="List lead bases for an account",
)
def list_lead_bases(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    bases = (
        db.query(LeadBase)
        .filter(LeadBase.cuenta_id == account_id)
        .order_by(LeadBase.created_at)
        .all()
    )

    # Count leads per base
    lead_counts = dict(
        db.query(Lead.lead_base_id, func.count(Lead.id))
        .filter(Lead.lead_base_id.in_([b.id for b in bases]))
        .group_by(Lead.lead_base_id)
        .all()
    )

    items = []
    for base in bases:
        items.append({
            "id": base.id,
            "cuenta_id": base.cuenta_id,
            "nombre": base.nombre,
            "es_default": base.es_default,
            "total_leads": lead_counts.get(base.id, 0),
            "created_at": base.created_at,
        })

    return {"items": items, "total": len(items)}


@router.get(
    "/bases/{base_id}",
    response_model=LeadBaseResponse,
    summary="Get lead base details",
)
def get_lead_base(
    base_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> LeadBase:
    base = db.query(LeadBase).filter(LeadBase.id == base_id).first()
    if not base:
        raise HTTPException(status_code=404, detail="Lead base not found")
    return base


@router.put(
    "/bases/{base_id}",
    response_model=LeadBaseResponse,
    summary="Update a lead base",
)
def update_lead_base(
    base_id: uuid.UUID,
    body: LeadBaseUpdate,
    db: Session = Depends(get_db),
) -> LeadBase:
    base = db.query(LeadBase).filter(LeadBase.id == base_id).first()
    if not base:
        raise HTTPException(status_code=404, detail="Lead base not found")

    if body.nombre is not None:
        base.nombre = body.nombre

    if body.es_default is True:
        db.query(LeadBase).filter(
            LeadBase.cuenta_id == base.cuenta_id, LeadBase.es_default.is_(True)
        ).update({"es_default": False})
        base.es_default = True

    db.commit()
    db.refresh(base)
    return base


@router.delete(
    "/bases/{base_id}",
    status_code=204,
    summary="Delete a lead base",
)
def delete_lead_base(
    base_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    base = db.query(LeadBase).filter(LeadBase.id == base_id).first()
    if not base:
        raise HTTPException(status_code=404, detail="Lead base not found")
    if base.es_default:
        raise HTTPException(status_code=400, detail="Cannot delete the default base")

    db.delete(base)
    db.commit()


# --- Routing Rules ---


@router.post(
    "/bases/{base_id}/rules",
    response_model=RoutingRuleResponse,
    status_code=201,
    summary="Add a routing rule to a base",
)
def create_routing_rule(
    base_id: uuid.UUID,
    body: RoutingRuleCreate,
    db: Session = Depends(get_db),
) -> RoutingRule:
    base = db.query(LeadBase).filter(LeadBase.id == base_id).first()
    if not base:
        raise HTTPException(status_code=404, detail="Lead base not found")

    valid_operators = {"equals", "not_equals", "contains", "greater_than", "less_than"}
    if body.operador not in valid_operators:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid operator. Must be one of: {', '.join(sorted(valid_operators))}",
        )

    rule = RoutingRule(
        lead_base_id=base_id,
        campo=body.campo,
        operador=body.operador,
        valor=body.valor,
        prioridad=body.prioridad,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get(
    "/bases/{base_id}/rules",
    response_model=RoutingRuleListResponse,
    summary="List routing rules for a base",
)
def list_routing_rules(
    base_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> dict:
    base = db.query(LeadBase).filter(LeadBase.id == base_id).first()
    if not base:
        raise HTTPException(status_code=404, detail="Lead base not found")

    rules = (
        db.query(RoutingRule)
        .filter(RoutingRule.lead_base_id == base_id)
        .order_by(RoutingRule.prioridad)
        .all()
    )
    return {"items": rules, "total": len(rules)}


@router.put(
    "/rules/{rule_id}",
    response_model=RoutingRuleResponse,
    summary="Update a routing rule",
)
def update_routing_rule(
    rule_id: uuid.UUID,
    body: RoutingRuleUpdate,
    db: Session = Depends(get_db),
) -> RoutingRule:
    rule = db.query(RoutingRule).filter(RoutingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")

    if body.campo is not None:
        rule.campo = body.campo
    if body.operador is not None:
        valid_operators = {"equals", "not_equals", "contains", "greater_than", "less_than"}
        if body.operador not in valid_operators:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid operator. Must be one of: {', '.join(sorted(valid_operators))}",
            )
        rule.operador = body.operador
    if body.valor is not None:
        rule.valor = body.valor
    if body.prioridad is not None:
        rule.prioridad = body.prioridad

    db.commit()
    db.refresh(rule)
    return rule


@router.delete(
    "/rules/{rule_id}",
    status_code=204,
    summary="Delete a routing rule",
)
def delete_routing_rule(
    rule_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> None:
    rule = db.query(RoutingRule).filter(RoutingRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")

    db.delete(rule)
    db.commit()


# --- Leads by Base ---


@router.get(
    "/accounts/{account_id}/bases/{base_id}/leads",
    response_model=LeadListResponse,
    summary="List leads for a specific base",
)
def list_leads_by_base(
    account_id: uuid.UUID,
    base_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    base = db.query(LeadBase).filter(
        LeadBase.id == base_id, LeadBase.cuenta_id == account_id
    ).first()
    if not base:
        raise HTTPException(status_code=404, detail="Lead base not found")

    query = db.query(Lead).filter(Lead.lead_base_id == base_id)
    total = query.count()
    leads = (
        query.order_by(Lead.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = []
    for lead in leads:
        items.append({
            "id": lead.id,
            "cuenta_id": lead.cuenta_id,
            "record_id": lead.record_id,
            "lead_base_id": lead.lead_base_id,
            "base_nombre": base.nombre,
            "datos": lead.datos,
            "created_at": lead.created_at,
        })

    return {"items": items, "total": total, "page": page, "page_size": page_size}


# --- Move Leads ---


@router.post(
    "/bases/move-leads",
    response_model=MoveLeadsResponse,
    summary="Move leads to another base",
)
def move_leads(
    body: MoveLeadsRequest,
    db: Session = Depends(get_db),
) -> dict:
    target_base = db.query(LeadBase).filter(LeadBase.id == body.target_base_id).first()
    if not target_base:
        raise HTTPException(status_code=404, detail="Target base not found")

    moved = (
        db.query(Lead)
        .filter(Lead.id.in_(body.lead_ids), Lead.cuenta_id == target_base.cuenta_id)
        .update({"lead_base_id": target_base.id}, synchronize_session="fetch")
    )
    db.commit()

    return {"moved": moved}

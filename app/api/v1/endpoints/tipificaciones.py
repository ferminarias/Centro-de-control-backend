"""
API endpoints for Tipificacion and Subtipificacion management.
Provides CRUD operations for lead classification system.
"""
import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.models.account import Account
from app.models.lead import Lead
from app.models.tipificacion import Subtipificacion, Tipificacion
from app.models.user import User
from app.schemas.tipificacion import (
    BulkTipificacionUpdate,
    LeadTipificacionUpdate,
    SubtipificacionCreate,
    SubtipificacionListResponse,
    SubtipificacionResponse,
    SubtipificacionUpdate,
    TipificacionCreate,
    TipificacionListResponse,
    TipificacionResponse,
    TipificacionUpdate,
    TipificacionWithSubtipificacionesResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions
# ─────────────────────────────────────────────────────────────────────────────

def verify_ownership(tip: Tipificacion | Subtipificacion, cuenta_id: uuid.UUID, current_user: User | None = None, db: Session | None = None) -> None:
    """Verify that the resource belongs to the account."""
    # Direct ownership
    if str(tip.cuenta_id) == str(cuenta_id):
        return
    
    # Check ultra admin permission
    if current_user and db and current_user.role_id:
        from app.models.role import Role
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role and role.permisos:
            if "accounts:*" in role.permisos or "*" in role.permisos:
                return
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No tienes permiso para acceder a este recurso"
    )


def verify_account_access(current_user: User, account_id: uuid.UUID, db: Session) -> None:
    """Verify user has access to the account (owns it or is ultra admin)."""
    # User owns the account
    if str(current_user.cuenta_id) == str(account_id):
        return
    
    # Check if user is ultra admin (has accounts:* permission)
    from app.models.role import Role
    if current_user.role_id:
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role and role.permisos:
            if "accounts:*" in role.permisos or "*" in role.permisos:
                return
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acceso denegado"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Tipificacion Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/accounts/{account_id}/tipificaciones",
    response_model=TipificacionListResponse,
    summary="Listar tipificaciones de una cuenta",
    dependencies=[Depends(require_permission("leads:read"))],
)
def list_tipificaciones(
    account_id: uuid.UUID,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List all tipificaciones for an account with their subtipificaciones."""
    # Verify account exists and user has access
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    verify_account_access(current_user, account_id, db)
    
    query = db.query(Tipificacion).filter(Tipificacion.cuenta_id == account_id)
    
    if not include_inactive:
        query = query.filter(Tipificacion.activo.is_(True))
    
    tipificaciones = query.order_by(Tipificacion.orden, Tipificacion.nombre).all()
    
    # Calculate totals
    result = []
    for tip in tipificaciones:
        total_subs = len([s for s in tip.subtipificaciones if s.activo])
        total_leads = db.query(Lead).filter(
            Lead.tipificacion_id == tip.id
        ).count()
        
        tip_dict = {
            "id": tip.id,
            "cuenta_id": tip.cuenta_id,
            "nombre": tip.nombre,
            "descripcion": tip.descripcion,
            "color": tip.color,
            "orden": tip.orden,
            "activo": tip.activo,
            "es_final": tip.es_final,
            "subtipificaciones": [
                {
                    "id": s.id,
                    "tipificacion_id": s.tipificacion_id,
                    "cuenta_id": s.cuenta_id,
                    "nombre": s.nombre,
                    "descripcion": s.descripcion,
                    "color": s.color,
                    "orden": s.orden,
                    "activo": s.activo,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                }
                for s in sorted(tip.subtipificaciones, key=lambda x: (x.orden, x.nombre))
            ],
            "total_subtipificaciones": total_subs,
            "total_leads": total_leads,
            "created_at": tip.created_at,
            "updated_at": tip.updated_at,
        }
        result.append(tip_dict)
    
    return {"items": result, "total": len(result)}


@router.post(
    "/accounts/{account_id}/tipificaciones",
    response_model=TipificacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tipificacion",
    dependencies=[Depends(require_permission("leads:update"))],
)
def create_tipificacion(
    account_id: uuid.UUID,
    body: TipificacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Create a new tipificacion with optional subtipificaciones."""
    # Verify account
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    verify_account_access(current_user, account_id, db)
    
    # Create tipificacion
    tipificacion = Tipificacion(
        cuenta_id=account_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        color=body.color,
        orden=body.orden,
        activo=body.activo,
        es_final=body.es_final,
    )
    db.add(tipificacion)
    db.flush()  # Get the ID
    
    # Create subtipificaciones if provided
    if body.subtipificaciones and not body.es_final:
        for sub_data in body.subtipificaciones:
            sub = Subtipificacion(
                tipificacion_id=tipificacion.id,
                cuenta_id=account_id,
                nombre=sub_data.nombre,
                descripcion=sub_data.descripcion,
                color=sub_data.color,
                orden=sub_data.orden,
                activo=sub_data.activo,
            )
            db.add(sub)
    
    db.commit()
    db.refresh(tipificacion)
    
    logger.info("Tipificacion '%s' created for account %s", tipificacion.nombre, account_id)
    
    return {
        "id": tipificacion.id,
        "cuenta_id": tipificacion.cuenta_id,
        "nombre": tipificacion.nombre,
        "descripcion": tipificacion.descripcion,
        "color": tipificacion.color,
        "orden": tipificacion.orden,
        "activo": tipificacion.activo,
        "es_final": tipificacion.es_final,
        "subtipificaciones": [],
        "total_subtipificaciones": 0,
        "total_leads": 0,
        "created_at": tipificacion.created_at,
        "updated_at": tipificacion.updated_at,
    }


@router.get(
    "/tipificaciones/{tipificacion_id}",
    response_model=TipificacionWithSubtipificacionesResponse,
    summary="Obtener tipificacion",
    dependencies=[Depends(require_permission("leads:read"))],
)
def get_tipificacion(
    tipificacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tipificacion:
    """Get a specific tipificacion with its subtipificaciones."""
    tip = db.query(Tipificacion).filter(Tipificacion.id == tipificacion_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="Tipificacion no encontrada")
    
    verify_ownership(tip, current_user.cuenta_id, current_user, db)
    
    return tip


@router.put(
    "/tipificaciones/{tipificacion_id}",
    response_model=TipificacionResponse,
    summary="Actualizar tipificacion",
    dependencies=[Depends(require_permission("leads:update"))],
)
def update_tipificacion(
    tipificacion_id: uuid.UUID,
    body: TipificacionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update a tipificacion."""
    tip = db.query(Tipificacion).filter(Tipificacion.id == tipificacion_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="Tipificacion no encontrada")
    
    verify_ownership(tip, current_user.cuenta_id, current_user, db)
    
    # Update fields
    if body.nombre is not None:
        tip.nombre = body.nombre
    if body.descripcion is not None:
        tip.descripcion = body.descripcion
    if body.color is not None:
        tip.color = body.color
    if body.orden is not None:
        tip.orden = body.orden
    if body.activo is not None:
        tip.activo = body.activo
    if body.es_final is not None:
        tip.es_final = body.es_final
    
    db.commit()
    db.refresh(tip)
    
    logger.info("Tipificacion '%s' updated", tip.nombre)
    
    total_subs = len([s for s in tip.subtipificaciones if s.activo])
    total_leads = db.query(Lead).filter(Lead.tipificacion_id == tip.id).count()
    
    return {
        "id": tip.id,
        "cuenta_id": tip.cuenta_id,
        "nombre": tip.nombre,
        "descripcion": tip.descripcion,
        "color": tip.color,
        "orden": tip.orden,
        "activo": tip.activo,
        "es_final": tip.es_final,
        "subtipificaciones": [
            {
                "id": s.id,
                "tipificacion_id": s.tipificacion_id,
                "cuenta_id": s.cuenta_id,
                "nombre": s.nombre,
                "descripcion": s.descripcion,
                "color": s.color,
                "orden": s.orden,
                "activo": s.activo,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in sorted(tip.subtipificaciones, key=lambda x: (x.orden, x.nombre))
        ],
        "total_subtipificaciones": total_subs,
        "total_leads": total_leads,
        "created_at": tip.created_at,
        "updated_at": tip.updated_at,
    }


@router.delete(
    "/tipificaciones/{tipificacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar tipificacion",
    dependencies=[Depends(require_permission("leads:delete"))],
)
def delete_tipificacion(
    tipificacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a tipificacion and all its subtipificaciones."""
    tip = db.query(Tipificacion).filter(Tipificacion.id == tipificacion_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="Tipificacion no encontrada")
    
    verify_ownership(tip, current_user.cuenta_id, current_user, db)
    
    # Check if any leads are using this tipificacion
    leads_count = db.query(Lead).filter(Lead.tipificacion_id == tipificacion_id).count()
    if leads_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: {leads_count} lead(s) están usando esta tipificacion"
        )
    
    db.delete(tip)
    db.commit()
    
    logger.info("Tipificacion '%s' deleted", tip.nombre)


# ─────────────────────────────────────────────────────────────────────────────
# Subtipificacion Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/tipificaciones/{tipificacion_id}/subtipificaciones",
    response_model=SubtipificacionListResponse,
    summary="Listar subtipificaciones",
    dependencies=[Depends(require_permission("leads:read"))],
)
def list_subtipificaciones(
    tipificacion_id: uuid.UUID,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """List all subtipificaciones for a tipificacion."""
    tip = db.query(Tipificacion).filter(Tipificacion.id == tipificacion_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="Tipificacion no encontrada")
    
    verify_ownership(tip, current_user.cuenta_id, current_user, db)
    
    query = db.query(Subtipificacion).filter(
        Subtipificacion.tipificacion_id == tipificacion_id
    )
    
    if not include_inactive:
        query = query.filter(Subtipificacion.activo.is_(True))
    
    subtipificaciones = query.order_by(Subtipificacion.orden, Subtipificacion.nombre).all()
    
    return {
        "items": subtipificaciones,
        "total": len(subtipificaciones)
    }


@router.post(
    "/tipificaciones/{tipificacion_id}/subtipificaciones",
    response_model=SubtipificacionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear subtipificacion",
    dependencies=[Depends(require_permission("leads:update"))],
)
def create_subtipificacion(
    tipificacion_id: uuid.UUID,
    body: SubtipificacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Subtipificacion:
    """Create a new subtipificacion under a tipificacion."""
    tip = db.query(Tipificacion).filter(Tipificacion.id == tipificacion_id).first()
    if not tip:
        raise HTTPException(status_code=404, detail="Tipificacion no encontrada")
    
    verify_ownership(tip, current_user.cuenta_id, current_user, db)
    
    # Check if tipificacion is final (doesn't allow subtipificaciones)
    if tip.es_final:
        raise HTTPException(
            status_code=400,
            detail="Esta tipificacion es final y no permite subtipificaciones"
        )
    
    sub = Subtipificacion(
        tipificacion_id=tipificacion_id,
        cuenta_id=tip.cuenta_id,  # Usar cuenta_id del tip padre, no del usuario
        nombre=body.nombre,
        descripcion=body.descripcion,
        color=body.color,
        orden=body.orden,
        activo=body.activo,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    
    logger.info("Subtipificacion '%s' created under '%s'", sub.nombre, tip.nombre)
    
    return sub


@router.put(
    "/subtipificaciones/{subtipificacion_id}",
    response_model=SubtipificacionResponse,
    summary="Actualizar subtipificacion",
    dependencies=[Depends(require_permission("leads:update"))],
)
def update_subtipificacion(
    subtipificacion_id: uuid.UUID,
    body: SubtipificacionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Subtipificacion:
    """Update a subtipificacion."""
    sub = db.query(Subtipificacion).filter(Subtipificacion.id == subtipificacion_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subtipificacion no encontrada")
    
    verify_ownership(sub, current_user.cuenta_id, current_user, db)
    
    if body.nombre is not None:
        sub.nombre = body.nombre
    if body.descripcion is not None:
        sub.descripcion = body.descripcion
    if body.color is not None:
        sub.color = body.color
    if body.orden is not None:
        sub.orden = body.orden
    if body.activo is not None:
        sub.activo = body.activo
    
    db.commit()
    db.refresh(sub)
    
    logger.info("Subtipificacion '%s' updated", sub.nombre)
    
    return sub


@router.delete(
    "/subtipificaciones/{subtipificacion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar subtipificacion",
    dependencies=[Depends(require_permission("leads:delete"))],
)
def delete_subtipificacion(
    subtipificacion_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a subtipificacion."""
    sub = db.query(Subtipificacion).filter(Subtipificacion.id == subtipificacion_id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="Subtipificacion no encontrada")
    
    verify_ownership(sub, current_user.cuenta_id, current_user, db)
    
    # Check if any leads are using this subtipificacion
    leads_count = db.query(Lead).filter(Lead.subtipificacion_id == subtipificacion_id).count()
    if leads_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: {leads_count} lead(s) están usando esta subtipificacion"
        )
    
    db.delete(sub)
    db.commit()
    
    logger.info("Subtipificacion '%s' deleted", sub.nombre)


# ─────────────────────────────────────────────────────────────────────────────
# Lead Tipification Endpoints
# ─────────────────────────────────────────────────────────────────────────────


@router.put(
    "/leads/{lead_id}/tipificacion",
    summary="Actualizar tipificacion de un lead",
    dependencies=[Depends(require_permission("leads:update"))],
)
def update_lead_tipificacion(
    lead_id: uuid.UUID,
    body: LeadTipificacionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Update the tipificacion of a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    verify_account_access(current_user, lead.cuenta_id, db)
    
    # Validate tipificacion exists and belongs to account
    if body.tipificacion_id:
        tip = db.query(Tipificacion).filter(
            Tipificacion.id == body.tipificacion_id,
            Tipificacion.cuenta_id == current_user.cuenta_id
        ).first()
        if not tip:
            raise HTTPException(status_code=404, detail="Tipificacion no encontrada")
    
    # Validate subtipificacion exists and belongs to tipificacion
    if body.subtipificacion_id:
        sub = db.query(Subtipificacion).filter(
            Subtipificacion.id == body.subtipificacion_id,
            Subtipificacion.cuenta_id == current_user.cuenta_id
        ).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Subtipificacion no encontrada")
        
        # If subtipificacion is provided, verify it belongs to the selected tipificacion
        if body.tipificacion_id and str(sub.tipificacion_id) != str(body.tipificacion_id):
            raise HTTPException(
                status_code=400,
                detail="La subtipificacion no pertenece a la tipificacion seleccionada"
            )
        
        # If only subtipificacion is provided, auto-set tipificacion
        if not body.tipificacion_id:
            body.tipificacion_id = sub.tipificacion_id
    
    # Update lead
    lead.tipificacion_id = body.tipificacion_id
    lead.subtipificacion_id = body.subtipificacion_id
    
    db.commit()
    
    logger.info("Lead %s tipificado como %s / %s", 
                lead_id, 
                body.tipificacion_id, 
                body.subtipificacion_id)
    
    return {
        "success": True,
        "lead_id": lead_id,
        "tipificacion_id": body.tipificacion_id,
        "subtipificacion_id": body.subtipificacion_id,
    }


@router.post(
    "/leads/bulk-tipificacion",
    summary="Actualizar tipificacion de múltiples leads",
    dependencies=[Depends(require_permission("leads:update"))],
)
def bulk_update_tipificacion(
    body: BulkTipificacionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Bulk update tipificacion for multiple leads."""
    # Use account_id from first lead or current user
    from app.models.lead import Lead
    first_lead = db.query(Lead).filter(Lead.id.in_(body.lead_ids)).first()
    if first_lead:
        verify_account_access(current_user, first_lead.cuenta_id, db)
        cuenta_id = first_lead.cuenta_id
    else:
        cuenta_id = current_user.cuenta_id
    
    # Validate tipificacion if provided
    if body.tipificacion_id:
        tip = db.query(Tipificacion).filter(
            Tipificacion.id == body.tipificacion_id,
            Tipificacion.cuenta_id == cuenta_id
        ).first()
        if not tip:
            raise HTTPException(status_code=404, detail="Tipificacion no encontrada")
    
    # Validate subtipificacion if provided
    if body.subtipificacion_id:
        sub = db.query(Subtipificacion).filter(
            Subtipificacion.id == body.subtipificacion_id,
            Subtipificacion.cuenta_id == cuenta_id
        ).first()
        if not sub:
            raise HTTPException(status_code=404, detail="Subtipificacion no encontrada")
        
        # Auto-set tipificacion from subtipificacion if not provided
        if not body.tipificacion_id:
            body.tipificacion_id = sub.tipificacion_id
        elif str(sub.tipificacion_id) != str(body.tipificacion_id):
            raise HTTPException(
                status_code=400,
                detail="La subtipificacion no pertenece a la tipificacion seleccionada"
            )
    
    # Update leads
    updated = db.query(Lead).filter(
        Lead.id.in_(body.lead_ids),
        Lead.cuenta_id == cuenta_id
    ).update({
        "tipificacion_id": body.tipificacion_id,
        "subtipificacion_id": body.subtipificacion_id,
    }, synchronize_session=False)
    
    db.commit()
    
    logger.info("Bulk tipificacion update: %d leads updated", updated)
    
    return {
        "success": True,
        "updated": updated,
        "tipificacion_id": body.tipificacion_id,
        "subtipificacion_id": body.subtipificacion_id,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Stats Endpoint
# ─────────────────────────────────────────────────────────────────────────────


@router.get(
    "/accounts/{account_id}/tipificaciones/stats",
    summary="Estadísticas de tipificaciones",
    dependencies=[Depends(require_permission("leads:read"))],
)
def get_tipificaciones_stats(
    account_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get statistics of leads by tipificacion."""
    verify_account_access(current_user, account_id, db)
    
    tipificaciones = db.query(Tipificacion).filter(
        Tipificacion.cuenta_id == account_id,
        Tipificacion.activo.is_(True)
    ).all()
    
    stats = []
    for tip in tipificaciones:
        count = db.query(Lead).filter(Lead.tipificacion_id == tip.id).count()
        sub_stats = []
        for sub in tip.subtipificaciones:
            if sub.activo:
                sub_count = db.query(Lead).filter(Lead.subtipificacion_id == sub.id).count()
                sub_stats.append({
                    "id": sub.id,
                    "nombre": sub.nombre,
                    "color": sub.color,
                    "count": sub_count,
                })
        
        stats.append({
            "id": tip.id,
            "nombre": tip.nombre,
            "color": tip.color,
            "count": count,
            "subtipificaciones": sub_stats,
        })
    
    return {"stats": stats}

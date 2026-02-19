"""
API endpoints para CRM Extras:
- Actividades
- Tareas
- Notas
- Tags
- Audit Log
"""
import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.models.account import Account
from app.models.crm_extras import Actividad, AuditLog, LeadTag, Nota, Tag, Tarea
from app.models.lead import Lead
from app.models.user import User
from app.schemas.crm_extras import (
    ActividadCreate,
    ActividadListResponse,
    ActividadResponse,
    ActividadUpdate,
    AuditLogListResponse,
    LeadTagAssign,
    LeadTimelineItem,
    NotaCreate,
    NotaListResponse,
    NotaResponse,
    NotaUpdate,
    TagCreate,
    TagListResponse,
    TagResponse,
    TagUpdate,
    TareaComplete,
    TareaCreate,
    TareaListResponse,
    TareaResponse,
    TareaStats,
    TareaUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# HELPERS
# =============================================================================

def verificar_ownership_lead(db: Session, lead_id: uuid.UUID, cuenta_id: uuid.UUID, current_user: User | None = None) -> Lead:
    """Verifica que el lead pertenezca a la cuenta."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead no encontrado")
    
    # Check if user owns the lead's account
    if str(lead.cuenta_id) == str(cuenta_id):
        return lead
    
    # Check if user is ultra admin
    if current_user and current_user.role_id:
        from app.models.role import Role
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role and role.permisos:
            if "accounts:*" in role.permisos or "*" in role.permisos:
                return lead
    
    raise HTTPException(status_code=403, detail="Acceso denegado a este lead")
    return lead


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


def crear_audit_log(
    db: Session,
    cuenta_id: uuid.UUID,
    user_id: uuid.UUID | None,
    entidad_tipo: str,
    entidad_id: uuid.UUID,
    accion: str,
    campo: str | None = None,
    valor_anterior: str | None = None,
    valor_nuevo: str | None = None,
    snapshot: dict | None = None,
    ip_address: str | None = None,
    endpoint: str | None = None,
):
    """Crea un registro de auditoría."""
    log = AuditLog(
        cuenta_id=cuenta_id,
        user_id=user_id,
        entidad_tipo=entidad_tipo,
        entidad_id=entidad_id,
        accion=accion,
        campo=campo,
        valor_anterior=valor_anterior,
        valor_nuevo=valor_nuevo,
        snapshot=snapshot,
        ip_address=ip_address,
        endpoint=endpoint,
    )
    db.add(log)


# =============================================================================
# ACTIVIDADES
# =============================================================================

@router.get(
    "/accounts/{account_id}/actividades",
    response_model=ActividadListResponse,
    summary="Listar actividades de una cuenta",
    dependencies=[Depends(require_permission("leads:read"))],
)
def list_actividades(
    account_id: uuid.UUID,
    lead_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    tipo: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Listar actividades con filtros opcionales."""
    verify_account_access(current_user, account_id, db)
    
    query = db.query(Actividad).filter(Actividad.cuenta_id == account_id)
    
    if lead_id:
        query = query.filter(Actividad.lead_id == lead_id)
    if user_id:
        query = query.filter(Actividad.user_id == user_id)
    if tipo:
        query = query.filter(Actividad.tipo == tipo)
    if desde:
        query = query.filter(Actividad.fecha_inicio >= desde)
    if hasta:
        query = query.filter(Actividad.fecha_inicio <= hasta)
    
    total = query.count()
    items = (
        query.order_by(desc(Actividad.fecha_inicio))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    return {"items": items, "total": total}


@router.post(
    "/accounts/{account_id}/actividades",
    response_model=ActividadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear actividad",
    dependencies=[Depends(require_permission("leads:update"))],
)
def create_actividad(
    account_id: uuid.UUID,
    body: ActividadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Actividad:
    """Crear una nueva actividad (llamada, email, reunión, etc.)."""
    # Verificar acceso a la cuenta (soporta ultra admin)
    verify_account_access(current_user, account_id, db)
    
    # Verificar lead
    verificar_ownership_lead(db, body.lead_id, account_id, current_user)
    
    actividad = Actividad(
        cuenta_id=account_id,
        lead_id=body.lead_id,
        user_id=body.user_id or current_user.id,
        tipo=body.tipo,
        direccion=body.direccion,
        asunto=body.asunto,
        descripcion=body.descripcion,
        metadata_=body.metadata_,
        fecha_inicio=body.fecha_inicio,
        fecha_fin=body.fecha_fin,
        resultado=body.resultado,
    )
    db.add(actividad)
    
    # Audit log
    crear_audit_log(
        db=db,
        cuenta_id=account_id,
        user_id=current_user.id,
        entidad_tipo="actividad",
        entidad_id=actividad.id,
        accion="create",
    )
    
    db.commit()
    db.refresh(actividad)
    
    logger.info(f"Actividad {actividad.tipo} creada para lead {body.lead_id}")
    return actividad


@router.get(
    "/actividades/{actividad_id}",
    response_model=ActividadResponse,
    summary="Obtener actividad",
    dependencies=[Depends(require_permission("leads:read"))],
)
def get_actividad(
    actividad_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Actividad:
    """Obtener una actividad por ID."""
    act = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    if str(act.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return act


@router.put(
    "/actividades/{actividad_id}",
    response_model=ActividadResponse,
    summary="Actualizar actividad",
    dependencies=[Depends(require_permission("leads:update"))],
)
def update_actividad(
    actividad_id: uuid.UUID,
    body: ActividadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Actividad:
    """Actualizar una actividad."""
    act = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    if str(act.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Guardar valores anteriores para audit
    cambios = []
    
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "metadata_":
            field = "metadata"
        old_val = getattr(act, field)
        if old_val != value:
            cambios.append((field, str(old_val), str(value)))
            setattr(act, field, value)
    
    # Audit log
    for campo, anterior, nuevo in cambios:
        crear_audit_log(
            db=db,
            cuenta_id=current_user.cuenta_id,
            user_id=current_user.id,
            entidad_tipo="actividad",
            entidad_id=act.id,
            accion="update",
            campo=campo,
            valor_anterior=anterior,
            valor_nuevo=nuevo,
        )
    
    db.commit()
    db.refresh(act)
    return act


@router.delete(
    "/actividades/{actividad_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar actividad",
    dependencies=[Depends(require_permission("leads:delete"))],
)
def delete_actividad(
    actividad_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Eliminar una actividad."""
    act = db.query(Actividad).filter(Actividad.id == actividad_id).first()
    if not act:
        raise HTTPException(status_code=404, detail="Actividad no encontrada")
    if str(act.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    crear_audit_log(
        db=db,
        cuenta_id=current_user.cuenta_id,
        user_id=current_user.id,
        entidad_tipo="actividad",
        entidad_id=act.id,
        accion="delete",
    )
    
    db.delete(act)
    db.commit()


# =============================================================================
# TAREAS
# =============================================================================

@router.get(
    "/accounts/{account_id}/tareas",
    response_model=TareaListResponse,
    summary="Listar tareas",
    dependencies=[Depends(require_permission("leads:read"))],
)
def list_tareas(
    account_id: uuid.UUID,
    lead_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    estado: str | None = None,
    prioridad: str | None = None,
    vencidas: bool | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Listar tareas con filtros."""
    verify_account_access(current_user, account_id, db)
    
    query = db.query(Tarea).filter(Tarea.cuenta_id == account_id)
    
    if lead_id:
        query = query.filter(Tarea.lead_id == lead_id)
    if user_id:
        query = query.filter(Tarea.user_id == user_id)
    if estado:
        query = query.filter(Tarea.estado == estado)
    if prioridad:
        query = query.filter(Tarea.prioridad == prioridad)
    if vencidas is True:
        query = query.filter(
            and_(Tarea.fecha_vencimiento < func.now(), Tarea.estado != "completada")
        )
    
    total = query.count()
    items = (
        query.order_by(Tarea.fecha_vencimiento)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    return {"items": items, "total": total}


@router.get(
    "/accounts/{account_id}/tareas/stats",
    response_model=TareaStats,
    summary="Estadísticas de tareas",
    dependencies=[Depends(require_permission("leads:read"))],
)
def get_tareas_stats(
    account_id: uuid.UUID,
    user_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtener estadísticas de tareas."""
    verify_account_access(current_user, account_id, db)
    
    query = db.query(Tarea).filter(Tarea.cuenta_id == account_id)
    if user_id:
        query = query.filter(Tarea.user_id == user_id)
    
    pendientes = query.filter(Tarea.estado.in_(["pendiente", "en_progreso"])).count()
    vencidas = query.filter(
        and_(Tarea.fecha_vencimiento < func.now(), Tarea.estado != "completada")
    ).count()
    
    # Completadas hoy
    from datetime import date, timedelta
    hoy = date.today()
    completadas_hoy = query.filter(
        func.date(Tarea.fecha_completada) == hoy
    ).count()
    
    # Completadas esta semana
    semana_pasada = hoy - timedelta(days=7)
    completadas_semana = query.filter(
        func.date(Tarea.fecha_completada) >= semana_pasada
    ).count()
    
    return {
        "pendientes": pendientes,
        "vencidas": vencidas,
        "completadas_hoy": completadas_hoy,
        "completadas_semana": completadas_semana,
    }


@router.post(
    "/accounts/{account_id}/tareas",
    response_model=TareaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tarea",
    dependencies=[Depends(require_permission("leads:update"))],
)
def create_tarea(
    account_id: uuid.UUID,
    body: TareaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tarea:
    """Crear una nueva tarea."""
    verify_account_access(current_user, account_id, db)
    
    if body.lead_id:
        verificar_ownership_lead(db, body.lead_id, account_id, current_user)
    
    tarea = Tarea(
        cuenta_id=account_id,
        lead_id=body.lead_id,
        user_id=body.user_id,
        titulo=body.titulo,
        descripcion=body.descripcion,
        tipo=body.tipo,
        prioridad=body.prioridad,
        estado=body.estado,
        fecha_vencimiento=body.fecha_vencimiento,
        es_recurrente=body.es_recurrente,
        frecuencia=body.frecuencia,
    )
    db.add(tarea)
    db.commit()
    db.refresh(tarea)
    
    logger.info(f"Tarea '{tarea.titulo}' creada")
    return tarea


@router.put(
    "/tareas/{tarea_id}",
    response_model=TareaResponse,
    summary="Actualizar tarea",
    dependencies=[Depends(require_permission("leads:update"))],
)
def update_tarea(
    tarea_id: uuid.UUID,
    body: TareaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tarea:
    """Actualizar una tarea."""
    tarea = db.query(Tarea).filter(Tarea.id == tarea_id).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if str(tarea.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tarea, field, value)
    
    db.commit()
    db.refresh(tarea)
    return tarea


@router.post(
    "/tareas/{tarea_id}/completar",
    response_model=TareaResponse,
    summary="Completar tarea",
    dependencies=[Depends(require_permission("leads:update"))],
)
def completar_tarea(
    tarea_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tarea:
    """Marcar tarea como completada."""
    tarea = db.query(Tarea).filter(Tarea.id == tarea_id).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if str(tarea.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    tarea.estado = "completada"
    tarea.fecha_completada = datetime.now()
    
    db.commit()
    db.refresh(tarea)
    return tarea


@router.delete(
    "/tareas/{tarea_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar tarea",
    dependencies=[Depends(require_permission("leads:delete"))],
)
def delete_tarea(
    tarea_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Eliminar una tarea."""
    tarea = db.query(Tarea).filter(Tarea.id == tarea_id).first()
    if not tarea:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if str(tarea.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    db.delete(tarea)
    db.commit()


# =============================================================================
# NOTAS
# =============================================================================

@router.get(
    "/leads/{lead_id}/notas",
    response_model=NotaListResponse,
    summary="Listar notas de un lead",
    dependencies=[Depends(require_permission("leads:read"))],
)
def list_notas(
    lead_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Listar notas de un lead."""
    lead = verificar_ownership_lead(db, lead_id, current_user.cuenta_id, current_user)
    
    query = db.query(Nota).filter(Nota.lead_id == lead_id)
    
    # Si no es admin, no mostrar notas privadas de otros usuarios
    if not current_user.role or "admin" not in str(current_user.role.nombre).lower():
        query = query.filter(
            (Nota.es_privada == False) | (Nota.user_id == current_user.id)
        )
    
    total = query.count()
    items = (
        query.order_by(desc(Nota.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    return {"items": items, "total": total}


@router.post(
    "/leads/{lead_id}/notas",
    response_model=NotaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear nota",
    dependencies=[Depends(require_permission("leads:update"))],
)
def create_nota(
    lead_id: uuid.UUID,
    body: NotaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Nota:
    """Crear una nota para un lead."""
    lead = verificar_ownership_lead(db, lead_id, current_user.cuenta_id, current_user)
    
    nota = Nota(
        cuenta_id=current_user.cuenta_id,
        lead_id=lead_id,
        user_id=current_user.id,
        contenido=body.contenido,
        tipo=body.tipo,
        es_privada=body.es_privada,
    )
    db.add(nota)
    db.commit()
    db.refresh(nota)
    
    return nota


@router.put(
    "/notas/{nota_id}",
    response_model=NotaResponse,
    summary="Actualizar nota",
    dependencies=[Depends(require_permission("leads:update"))],
)
def update_nota(
    nota_id: uuid.UUID,
    body: NotaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Nota:
    """Actualizar una nota."""
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    if str(nota.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Solo el creador o admin puede editar
    if nota.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede editar esta nota")
    
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(nota, field, value)
    
    db.commit()
    db.refresh(nota)
    return nota


@router.delete(
    "/notas/{nota_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar nota",
    dependencies=[Depends(require_permission("leads:delete"))],
)
def delete_nota(
    nota_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Eliminar una nota."""
    nota = db.query(Nota).filter(Nota.id == nota_id).first()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota no encontrada")
    if str(nota.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # Solo el creador o admin puede eliminar
    if nota.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Solo el creador puede eliminar esta nota")
    
    db.delete(nota)
    db.commit()


# =============================================================================
# TAGS
# =============================================================================

@router.get(
    "/accounts/{account_id}/tags",
    response_model=TagListResponse,
    summary="Listar tags",
    dependencies=[Depends(require_permission("leads:read"))],
)
def list_tags(
    account_id: uuid.UUID,
    activos: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Listar tags de la cuenta."""
    verify_account_access(current_user, account_id, db)
    
    query = db.query(Tag).filter(Tag.cuenta_id == account_id)
    if activos:
        query = query.filter(Tag.activo == True)
    
    items = query.order_by(Tag.orden, Tag.nombre).all()
    
    # Calcular total de leads por tag
    result = []
    for tag in items:
        total_leads = db.query(LeadTag).filter(LeadTag.tag_id == tag.id).count()
        tag_dict = {
            "id": tag.id,
            "cuenta_id": tag.cuenta_id,
            "nombre": tag.nombre,
            "color": tag.color,
            "descripcion": tag.descripcion,
            "es_sistema": tag.es_sistema,
            "activo": tag.activo,
            "orden": tag.orden,
            "created_at": tag.created_at,
            "total_leads": total_leads,
        }
        result.append(tag_dict)
    
    return {"items": result, "total": len(result)}


@router.post(
    "/accounts/{account_id}/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear tag",
    dependencies=[Depends(require_permission("leads:update"))],
)
def create_tag(
    account_id: uuid.UUID,
    body: TagCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tag:
    """Crear un nuevo tag."""
    verify_account_access(current_user, account_id, db)
    
    tag = Tag(
        cuenta_id=account_id,
        nombre=body.nombre,
        color=body.color,
        descripcion=body.descripcion,
        orden=body.orden,
        activo=body.activo,
        es_sistema=False,
    )
    db.add(tag)
    db.commit()
    db.refresh(tag)
    
    return tag


@router.put(
    "/tags/{tag_id}",
    response_model=TagResponse,
    summary="Actualizar tag",
    dependencies=[Depends(require_permission("leads:update"))],
)
def update_tag(
    tag_id: uuid.UUID,
    body: TagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Tag:
    """Actualizar un tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    if str(tag.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    # No permitir modificar tags de sistema
    if tag.es_sistema:
        raise HTTPException(status_code=400, detail="No se pueden modificar tags de sistema")
    
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(tag, field, value)
    
    db.commit()
    db.refresh(tag)
    return tag


@router.delete(
    "/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar tag",
    dependencies=[Depends(require_permission("leads:delete"))],
)
def delete_tag(
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Eliminar un tag."""
    tag = db.query(Tag).filter(Tag.id == tag_id).first()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag no encontrado")
    if str(tag.cuenta_id) != str(current_user.cuenta_id):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    
    if tag.es_sistema:
        raise HTTPException(status_code=400, detail="No se pueden eliminar tags de sistema")
    
    # Verificar si tiene leads asignados
    leads_count = db.query(LeadTag).filter(LeadTag.tag_id == tag_id).count()
    if leads_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: {leads_count} lead(s) usan este tag"
        )
    
    db.delete(tag)
    db.commit()


# =============================================================================
# ASIGNAR TAGS A LEADS
# =============================================================================

@router.get(
    "/leads/{lead_id}/tags",
    response_model=list[TagResponse],
    summary="Obtener tags de un lead",
    dependencies=[Depends(require_permission("leads:read"))],
)
def get_lead_tags(
    lead_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Obtener tags asignados a un lead."""
    lead = verificar_ownership_lead(db, lead_id, current_user.cuenta_id, current_user)
    
    tags = (
        db.query(Tag)
        .join(LeadTag, LeadTag.tag_id == Tag.id)
        .filter(LeadTag.lead_id == lead_id)
        .all()
    )
    
    return tags


@router.put(
    "/leads/{lead_id}/tags",
    summary="Asignar tags a un lead",
    dependencies=[Depends(require_permission("leads:update"))],
)
def assign_tags_to_lead(
    lead_id: uuid.UUID,
    body: LeadTagAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Asignar/quitar tags de un lead."""
    lead = verificar_ownership_lead(db, lead_id, current_user.cuenta_id, current_user)
    
    # Eliminar tags actuales
    db.query(LeadTag).filter(LeadTag.lead_id == lead_id).delete()
    
    # Agregar nuevos tags
    for tag_id in body.tag_ids:
        # Verificar que el tag exista y pertenezca a la cuenta
        tag = db.query(Tag).filter(
            Tag.id == tag_id,
            Tag.cuenta_id == current_user.cuenta_id
        ).first()
        
        if tag:
            lead_tag = LeadTag(
                lead_id=lead_id,
                tag_id=tag_id,
                user_id=current_user.id
            )
            db.add(lead_tag)
    
    db.commit()
    
    return {"success": True, "lead_id": lead_id, "tags_count": len(body.tag_ids)}


# =============================================================================
# AUDIT LOG
# =============================================================================

@router.get(
    "/accounts/{account_id}/audit-logs",
    response_model=AuditLogListResponse,
    summary="Ver logs de auditoría",
    dependencies=[Depends(require_permission("audit:read"))],
)
def list_audit_logs(
    account_id: uuid.UUID,
    entidad_tipo: str | None = None,
    entidad_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    accion: str | None = None,
    desde: datetime | None = None,
    hasta: datetime | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Ver logs de auditoría (solo admins)."""
    verify_account_access(current_user, account_id, db)
    
    # TODO: Verificar que el usuario tenga permiso de admin
    # Por ahora, cualquier usuario autenticado puede ver
    
    query = db.query(AuditLog).filter(AuditLog.cuenta_id == account_id)
    
    if entidad_tipo:
        query = query.filter(AuditLog.entidad_tipo == entidad_tipo)
    if entidad_id:
        query = query.filter(AuditLog.entidad_id == entidad_id)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if accion:
        query = query.filter(AuditLog.accion == accion)
    if desde:
        query = query.filter(AuditLog.created_at >= desde)
    if hasta:
        query = query.filter(AuditLog.created_at <= hasta)
    
    total = query.count()
    logs = (
        query.order_by(desc(AuditLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    # Obtener datos de usuarios
    user_ids = [log.user_id for log in logs if log.user_id]
    users = {}
    if user_ids:
        user_records = db.query(User).filter(User.id.in_(user_ids)).all()
        users = {str(u.id): u for u in user_records}
    
    # Formatear respuesta
    items = []
    for log in logs:
        user = users.get(str(log.user_id)) if log.user_id else None
        items.append({
            "id": log.id,
            "cuenta_id": log.cuenta_id,
            "user_id": log.user_id,
            "entidad_tipo": log.entidad_tipo,
            "entidad_id": log.entidad_id,
            "accion": log.accion,
            "campo": log.campo,
            "valor_anterior": log.valor_anterior,
            "valor_nuevo": log.valor_nuevo,
            "snapshot": log.snapshot,
            "ip_address": log.ip_address,
            "endpoint": log.endpoint,
            "created_at": log.created_at,
            "user_nombre": user.nombre if user else None,
            "user_email": user.email if user else None,
        })
    
    return {"items": items, "total": total}


# =============================================================================
# TIMELINE DE LEAD
# =============================================================================

@router.get(
    "/leads/{lead_id}/timeline",
    response_model=list[LeadTimelineItem],
    summary="Obtener timeline completo de un lead",
    dependencies=[Depends(require_permission("leads:read"))],
)
def get_lead_timeline(
    lead_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Obtener timeline combinado de actividades, notas, tareas y cambios."""
    lead = verificar_ownership_lead(db, lead_id, current_user.cuenta_id, current_user)
    
    timeline = []
    
    # Actividades
    actividades = db.query(Actividad).filter(
        Actividad.lead_id == lead_id
    ).order_by(desc(Actividad.created_at)).limit(limit).all()
    
    for act in actividades:
        timeline.append(LeadTimelineItem(
            tipo="actividad",
            fecha=act.created_at,
            titulo=f"{act.tipo}: {act.asunto or 'Sin asunto'}",
            descripcion=act.descripcion,
            usuario=act.user.nombre if act.user else None,
            metadata={"tipo": act.tipo, "resultado": act.resultado}
        ))
    
    # Notas
    notas = db.query(Nota).filter(
        Nota.lead_id == lead_id
    ).order_by(desc(Nota.created_at)).limit(limit).all()
    
    for nota in notas:
        timeline.append(LeadTimelineItem(
            tipo="nota",
            fecha=nota.created_at,
            titulo="Nota agregada",
            descripcion=nota.contenido[:200] if nota.contenido else None,
            usuario=nota.user.nombre if nota.user else None,
            metadata={"es_privada": nota.es_privada}
        ))
    
    # Ordenar por fecha descendente
    timeline.sort(key=lambda x: x.fecha, reverse=True)
    
    return timeline[:limit]

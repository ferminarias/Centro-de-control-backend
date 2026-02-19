"""
API endpoints para Campañas de Contact Center
- Gestión de campañas (Admin)
- Distribución de leads a agentes
- Gestión de fichas (Agentes)
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import and_, desc, func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.models.account import Account
from app.models.campaign import (
    Campania, CampaniaAgente, CampaniaBase, ColaLead, AgenteCampaniaLog,
    EstadoCampania, EstadoCola, EstadoAgenteEnCampania, TipoDiscador
)
from app.models.crm_extras import Actividad
from app.models.lead import Lead
from app.models.lead_base import LeadBase
from app.models.role import Role
from app.models.tipificacion import Tipificacion
from app.models.user import User
from app.models.voip import Agent as VoipAgent
from app.schemas.campania import (
    CampaniaCreate, CampaniaUpdate, CampaniaResponse, CampaniaListResponse,
    CampaniaBaseAssign, CampaniaBaseResponse,
    CampaniaAgenteAssign, CampaniaAgenteResponse, AgenteEstadoUpdate,
    ColaLeadResponse, ColaLeadListResponse,
    LeadPendienteResponse, GestionFichaRequest, SolicitarFichaResponse,
    MetricasCampania,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# =============================================================================
# Helper Functions
# =============================================================================

def verify_account_access(current_user: User, account_id: uuid.UUID, db: Session) -> None:
    """Verify user has access to the account (owns it or is ultra admin)."""
    if str(current_user.cuenta_id) == str(account_id):
        return
    
    if current_user.role_id:
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role and role.permisos:
            if "accounts:*" in role.permisos or "*" in role.permisos:
                return
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")


def get_next_lead_for_agent(
    db: Session, 
    campania_id: uuid.UUID, 
    agente_id: uuid.UUID
) -> ColaLead | None:
    """
    Algoritmo de distribución de leads.
    Busca el siguiente lead disponible según prioridad y orden.
    """
    # Verificar si el agente ya tiene una ficha asignada
    ficha_actual = db.query(ColaLead).filter(
        ColaLead.campania_id == campania_id,
        ColaLead.agente_asignado_id == agente_id,
        ColaLead.estado.in_([EstadoCola.ASIGNADO, EstadoCola.GESTIONANDO])
    ).first()
    
    if ficha_actual:
        return ficha_actual
    
    # Buscar siguiente lead pendiente
    lead_pendiente = db.query(ColaLead).filter(
        ColaLead.campania_id == campania_id,
        ColaLead.estado == EstadoCola.PENDIENTE,
        ColaLead.proximo_intento.is_(None) | (ColaLead.proximo_intento <= datetime.utcnow())
    ).order_by(
        desc(ColaLead.prioridad),
        ColaLead.added_at
    ).with_for_update(skip_locked=True).first()
    
    if lead_pendiente:
        # Asignar al agente
        lead_pendiente.estado = EstadoCola.ASIGNADO
        lead_pendiente.agente_asignado_id = agente_id
        lead_pendiente.assigned_at = datetime.utcnow()
        db.commit()
        db.refresh(lead_pendiente)
    
    return lead_pendiente


# =============================================================================
# CRUD Campañas (Admin)
# =============================================================================

@router.get(
    "/accounts/{account_id}/campanias",
    response_model=CampaniaListResponse,
    summary="Listar campañas",
    dependencies=[Depends(require_permission("leads:read"))],
)
def list_campanias(
    account_id: uuid.UUID,
    estado: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Listar campañas de una cuenta."""
    verify_account_access(current_user, account_id, db)
    
    query = db.query(Campania).filter(Campania.cuenta_id == account_id)
    
    if estado:
        query = query.filter(Campania.estado == estado)
    
    campanias = query.order_by(desc(Campania.created_at)).all()
    
    # Agregar contadores
    result = []
    for c in campanias:
        camp_dict = {
            "id": c.id,
            "cuenta_id": c.cuenta_id,
            "nombre": c.nombre,
            "descripcion": c.descripcion,
            "tipo_discador": c.tipo_discador,
            "estado": c.estado,
            "config_discador": c.config_discador,
            "permite_llamada_manual": c.permite_llamada_manual,
            "grabar_llamadas": c.grabar_llamadas,
            "horario_inicio": c.horario_inicio,
            "horario_fin": c.horario_fin,
            "dias_operacion": c.dias_operacion,
            "tipificaciones_permitidas": c.tipificaciones_permitidas,
            "prioridad": c.prioridad,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
            "created_by": c.created_by,
            "total_bases": len(c.bases),
            "total_agentes": len([a for a in c.agentes if a.activo]),
            "leads_en_cola": db.query(ColaLead).filter(
                ColaLead.campania_id == c.id,
                ColaLead.estado == EstadoCola.PENDIENTE
            ).count()
        }
        result.append(camp_dict)
    
    return {"items": result, "total": len(result)}


@router.post(
    "/accounts/{account_id}/campanias",
    response_model=CampaniaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear campaña",
    dependencies=[Depends(require_permission("leads:update"))],
)
def create_campania(
    account_id: uuid.UUID,
    body: CampaniaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Crear nueva campaña."""
    verify_account_access(current_user, account_id, db)
    
    # Verificar que exista la cuenta
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Cuenta no encontrada")
    
    # Crear campaña
    campania = Campania(
        cuenta_id=account_id,
        nombre=body.nombre,
        descripcion=body.descripcion,
        tipo_discador=body.tipo_discador,
        config_discador=body.config_discador,
        permite_llamada_manual=body.permite_llamada_manual,
        grabar_llamadas=body.grabar_llamadas,
        horario_inicio=body.horario_inicio,
        horario_fin=body.horario_fin,
        dias_operacion=body.dias_operacion,
        tipificaciones_permitidas=body.tipificaciones_permitidas,
        prioridad=body.prioridad,
        estado=EstadoCampania.BORRADOR,
        created_by=current_user.id,
    )
    db.add(campania)
    db.flush()
    
    # Asignar bases
    for base_id in body.base_ids:
        base = db.query(LeadBase).filter(
            LeadBase.id == base_id,
            LeadBase.cuenta_id == account_id
        ).first()
        if base:
            camp_base = CampaniaBase(
                campania_id=campania.id,
                base_id=base_id,
                activo=True,
                prioridad=5
            )
            db.add(camp_base)
            
            # Agregar leads de la base a la cola
            leads = db.query(Lead).filter(
                Lead.lead_base_id == base_id,
                Lead.cuenta_id == account_id
            ).all()
            
            for lead in leads:
                cola_lead = ColaLead(
                    campania_id=campania.id,
                    lead_id=lead.id,
                    estado=EstadoCola.PENDIENTE,
                    prioridad=0
                )
                db.add(cola_lead)
    
    # Asignar agentes
    for agente_id in body.agente_ids:
        agente = db.query(User).filter(
            User.id == agente_id,
            User.cuenta_id == account_id
        ).first()
        if agente:
            camp_agente = CampaniaAgente(
                campania_id=campania.id,
                agente_id=agente_id,
                activo=True,
                nivel_skill=5,
                max_fichas=1
            )
            db.add(camp_agente)
    
    db.commit()
    db.refresh(campania)
    
    logger.info(f"Campaña '{campania.nombre}' creada por {current_user.username}")
    
    return {
        "id": campania.id,
        "cuenta_id": campania.cuenta_id,
        "nombre": campania.nombre,
        "descripcion": campania.descripcion,
        "tipo_discador": campania.tipo_discador,
        "estado": campania.estado,
        "config_discador": campania.config_discador,
        "permite_llamada_manual": campania.permite_llamada_manual,
        "grabar_llamadas": campania.grabar_llamadas,
        "horario_inicio": campania.horario_inicio,
        "horario_fin": campania.horario_fin,
        "dias_operacion": campania.dias_operacion,
        "tipificaciones_permitidas": campania.tipificaciones_permitidas,
        "prioridad": campania.prioridad,
        "created_at": campania.created_at,
        "updated_at": campania.updated_at,
        "created_by": campania.created_by,
        "total_bases": len(campania.bases),
        "total_agentes": len(campania.agentes),
        "leads_en_cola": len([l for l in campania.cola if l.estado == EstadoCola.PENDIENTE]),
    }


@router.get(
    "/campanias/{campania_id}",
    response_model=CampaniaResponse,
    summary="Obtener campaña",
    dependencies=[Depends(require_permission("leads:read"))],
)
def get_campania(
    campania_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtener detalle de una campaña."""
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    verify_account_access(current_user, campania.cuenta_id, db)
    
    return {
        "id": campania.id,
        "cuenta_id": campania.cuenta_id,
        "nombre": campania.nombre,
        "descripcion": campania.descripcion,
        "tipo_discador": campania.tipo_discador,
        "estado": campania.estado,
        "config_discador": campania.config_discador,
        "permite_llamada_manual": campania.permite_llamada_manual,
        "grabar_llamadas": campania.grabar_llamadas,
        "horario_inicio": campania.horario_inicio,
        "horario_fin": campania.horario_fin,
        "dias_operacion": campania.dias_operacion,
        "tipificaciones_permitidas": campania.tipificaciones_permitidas,
        "prioridad": campania.prioridad,
        "created_at": campania.created_at,
        "updated_at": campania.updated_at,
        "created_by": campania.created_by,
        "total_bases": len(campania.bases),
        "total_agentes": len([a for a in campania.agentes if a.activo]),
        "leads_en_cola": db.query(ColaLead).filter(
            ColaLead.campania_id == campania.id,
            ColaLead.estado == EstadoCola.PENDIENTE
        ).count(),
    }


@router.put(
    "/campanias/{campania_id}",
    response_model=CampaniaResponse,
    summary="Actualizar campaña",
    dependencies=[Depends(require_permission("leads:update"))],
)
def update_campania(
    campania_id: uuid.UUID,
    body: CampaniaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Actualizar campaña."""
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    verify_account_access(current_user, campania.cuenta_id, db)
    
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campania, field, value)
    
    db.commit()
    db.refresh(campania)
    
    return {
        "id": campania.id,
        "cuenta_id": campania.cuenta_id,
        "nombre": campania.nombre,
        "descripcion": campania.descripcion,
        "tipo_discador": campania.tipo_discador,
        "estado": campania.estado,
        "config_discador": campania.config_discador,
        "permite_llamada_manual": campania.permite_llamada_manual,
        "grabar_llamadas": campania.grabar_llamadas,
        "horario_inicio": campania.horario_inicio,
        "horario_fin": campania.horario_fin,
        "dias_operacion": campania.dias_operacion,
        "tipificaciones_permitidas": campania.tipificaciones_permitidas,
        "prioridad": campania.prioridad,
        "created_at": campania.created_at,
        "updated_at": campania.updated_at,
        "created_by": campania.created_by,
        "total_bases": len(campania.bases),
        "total_agentes": len(campania.agentes),
        "leads_en_cola": len([l for l in campania.cola if l.estado == EstadoCola.PENDIENTE]),
    }


@router.delete(
    "/campanias/{campania_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar campaña",
    dependencies=[Depends(require_permission("leads:delete"))],
)
def delete_campania(
    campania_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Eliminar campaña y toda su cola."""
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    verify_account_access(current_user, campania.cuenta_id, db)
    
    db.delete(campania)
    db.commit()
    
    logger.info(f"Campaña '{campania.nombre}' eliminada por {current_user.username}")


# =============================================================================
# Gestión de Agentes en Campaña
# =============================================================================

@router.get(
    "/campanias/{campania_id}/agentes",
    summary="Listar agentes de campaña",
    dependencies=[Depends(require_permission("leads:read"))],
)
def list_agentes_campania(
    campania_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list:
    """Listar agentes asignados a la campaña."""
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    verify_account_access(current_user, campania.cuenta_id, db)
    
    agentes = db.query(CampaniaAgente).filter(
        CampaniaAgente.campania_id == campania_id
    ).all()
    
    result = []
    for ca in agentes:
        # Buscar estado actual
        ultimo_log = db.query(AgenteCampaniaLog).filter(
            AgenteCampaniaLog.campania_id == campania_id,
            AgenteCampaniaLog.agente_id == ca.agente_id,
            AgenteCampaniaLog.ended_at.is_(None)
        ).order_by(desc(AgenteCampaniaLog.started_at)).first()
        
        result.append({
            "agente_id": ca.agente_id,
            "agente_nombre": f"{ca.agente.nombre} {ca.agente.apellido}",
            "agente_email": ca.agente.email,
            "activo": ca.activo,
            "nivel_skill": ca.nivel_skill,
            "max_fichas": ca.max_fichas,
            "added_at": ca.added_at,
            "estado_actual": ultimo_log.estado if ultimo_log else "offline",
            "fichas_gestionadas_hoy": db.query(ColaLead).filter(
                ColaLead.campania_id == campania_id,
                ColaLead.agente_asignado_id == ca.agente_id,
                ColaLead.estado == EstadoCola.COMPLETADO,
                ColaLead.completed_at >= datetime.utcnow().date()
            ).count()
        })
    
    return result


@router.post(
    "/campanias/{campania_id}/agentes",
    summary="Asignar agentes a campaña",
    dependencies=[Depends(require_permission("leads:update"))],
)
def assign_agentes(
    campania_id: uuid.UUID,
    body: CampaniaAgenteAssign,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Asignar agentes a la campaña."""
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    verify_account_access(current_user, campania.cuenta_id, db)
    
    for agente_id in body.agente_ids:
        existing = db.query(CampaniaAgente).filter(
            CampaniaAgente.campania_id == campania_id,
            CampaniaAgente.agente_id == agente_id
        ).first()
        
        if not existing:
            ca = CampaniaAgente(
                campania_id=campania_id,
                agente_id=agente_id,
                activo=True,
                nivel_skill=5,
                max_fichas=1
            )
            db.add(ca)
    
    db.commit()
    
    return {"success": True, "message": "Agentes asignados"}


# =============================================================================
# Cola de Leads
# =============================================================================

@router.get(
    "/campanias/{campania_id}/cola",
    response_model=ColaLeadListResponse,
    summary="Ver cola de leads",
    dependencies=[Depends(require_permission("leads:read"))],
)
def get_cola(
    campania_id: uuid.UUID,
    estado: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Ver leads en cola de la campaña."""
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    verify_account_access(current_user, campania.cuenta_id, db)
    
    query = db.query(ColaLead).filter(ColaLead.campania_id == campania_id)
    
    if estado:
        query = query.filter(ColaLead.estado == estado)
    
    leads = query.order_by(desc(ColaLead.prioridad), ColaLead.added_at).all()
    
    result = []
    for cl in leads:
        datos = cl.lead.datos if cl.lead else {}
        telefono = datos.get("telefono") or datos.get("Telefono") or datos.get("phone") or datos.get("movil")
        
        result.append({
            "id": cl.id,
            "lead_id": cl.lead_id,
            "estado": cl.estado,
            "prioridad": cl.prioridad,
            "intentos": cl.intentos,
            "agente_asignado_id": cl.agente_asignado_id,
            "agente_asignado_nombre": f"{cl.agente.nombre} {cl.agente.apellido}" if cl.agente else None,
            "proximo_intento": cl.proximo_intento,
            "added_at": cl.added_at,
            "lead_datos": datos,
            "lead_telefono": telefono,
        })
    
    return {
        "items": result,
        "total": len(result),
        "pendientes": len([l for l in result if l["estado"] == EstadoCola.PENDIENTE]),
        "asignados": len([l for l in result if l["estado"] == EstadoCola.ASIGNADO]),
        "completados": len([l for l in result if l["estado"] == EstadoCola.COMPLETADO]),
    }


# =============================================================================
# Endpoints para Agentes (Gestión de Contactos)
# =============================================================================

@router.post(
    "/campanias/{campania_id}/entrar",
    summary="Agente entra a la campaña",
)
def agente_entrar_campania(
    campania_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Agente indica que está listo para recibir fichas."""
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    # Verificar que el agente esté asignado
    asignacion = db.query(CampaniaAgente).filter(
        CampaniaAgente.campania_id == campania_id,
        CampaniaAgente.agente_id == current_user.id,
        CampaniaAgente.activo == True
    ).first()
    
    if not asignacion:
        raise HTTPException(status_code=403, detail="No estás asignado a esta campaña")
    
    # Cerrar sesiones anteriores abiertas
    db.query(AgenteCampaniaLog).filter(
        AgenteCampaniaLog.campania_id == campania_id,
        AgenteCampaniaLog.agente_id == current_user.id,
        AgenteCampaniaLog.ended_at.is_(None)
    ).update({"ended_at": datetime.utcnow()})
    
    # Crear nuevo log
    log = AgenteCampaniaLog(
        campania_id=campania_id,
        agente_id=current_user.id,
        estado=EstadoAgenteEnCampania.DISPONIBLE,
        started_at=datetime.utcnow()
    )
    db.add(log)
    db.commit()
    
    return {
        "success": True,
        "message": "Entraste a la campaña",
        "campania": {
            "id": campania.id,
            "nombre": campania.nombre,
            "tipo_discador": campania.tipo_discador,
        }
    }


@router.post(
    "/campanias/{campania_id}/solicitar-ficha",
    response_model=SolicitarFichaResponse,
    summary="Solicitar siguiente ficha",
)
def solicitar_ficha(
    campania_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    El agente solicita una ficha para gestionar.
    Si no tiene ficha asignada, busca una nueva.
    """
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    # Verificar asignación
    asignacion = db.query(CampaniaAgente).filter(
        CampaniaAgente.campania_id == campania_id,
        CampaniaAgente.agente_id == current_user.id,
        CampaniaAgente.activo == True
    ).first()
    
    if not asignacion:
        raise HTTPException(status_code=403, detail="No estás asignado a esta campaña")
    
    # Verificar si ya tiene una ficha asignada
    ficha_existente = db.query(ColaLead).filter(
        ColaLead.campania_id == campania_id,
        ColaLead.agente_asignado_id == current_user.id,
        ColaLead.estado.in_([EstadoCola.ASIGNADO, EstadoCola.GESTIONANDO])
    ).first()
    
    if ficha_existente:
        # Ya tiene ficha, devolverla
        return {
            "success": True,
            "message": "Tienes una ficha pendiente de gestión",
            "ficha": _build_ficha_response(ficha_existente, campania)
        }
    
    # Buscar nueva ficha
    nueva_ficha = get_next_lead_for_agent(db, campania_id, current_user.id)
    
    if not nueva_ficha:
        return {
            "success": False,
            "message": "No hay leads disponibles en este momento",
            "ficha": None
        }
    
    # Actualizar estado del agente
    db.query(AgenteCampaniaLog).filter(
        AgenteCampaniaLog.campania_id == campania_id,
        AgenteCampaniaLog.agente_id == current_user.id,
        AgenteCampaniaLog.ended_at.is_(None)
    ).update({"estado": EstadoAgenteEnCampania.GESTIONANDO})
    db.commit()
    
    return {
        "success": True,
        "message": "Ficha asignada",
        "ficha": _build_ficha_response(nueva_ficha, campania)
    }


def _build_ficha_response(cola_lead: ColaLead, campania: Campania) -> dict:
    """Construir respuesta de ficha con datos completos."""
    lead = cola_lead.lead
    
    # Historial de gestiones previas
    historial = []
    actividades = cola_lead.campania.cuenta.actividades
    # Aquí podrías filtrar actividades de este lead
    
    return {
        "cola_id": cola_lead.id,
        "lead_id": lead.id,
        "campania_id": campania.id,
        "campania_nombre": campania.nombre,
        "lead": {
            "id": lead.id,
            "datos": lead.datos,
            "tipificacion": lead.tipificacion,
            "subtipificacion": lead.subtipificacion,
        },
        "historial": historial,
        "script": f"Script de {campania.nombre}"  # Podría venir de config
    }


@router.post(
    "/campanias/{campania_id}/gestionar-ficha/{cola_id}",
    summary="Guardar gestión de ficha",
)
def gestionar_ficha(
    campania_id: uuid.UUID,
    cola_id: uuid.UUID,
    body: GestionFichaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    El agente guarda la gestión de la ficha.
    Obligatorio: tipificación.
    """
    cola = db.query(ColaLead).filter(
        ColaLead.id == cola_id,
        ColaLead.campania_id == campania_id,
        ColaLead.agente_asignado_id == current_user.id
    ).first()
    
    if not cola:
        raise HTTPException(status_code=404, detail="Ficha no encontrada o no te está asignada")
    
    # Validar tipificación obligatoria
    if not body.tipificacion_id:
        raise HTTPException(status_code=400, detail="Debes tipificar el contacto")
    
    # Actualizar lead
    lead = cola.lead
    lead.tipificacion_id = body.tipificacion_id
    lead.subtipificacion_id = body.subtipificacion_id
    
    # Marcar como completado en cola
    cola.estado = EstadoCola.COMPLETADO
    cola.completed_at = datetime.utcnow()
    
    # Agregar nota si existe
    if body.notas:
        from app.models.crm_extras import Nota
        nota = Nota(
            cuenta_id=cola.campania.cuenta_id,
            lead_id=lead.id,
            user_id=current_user.id,
            contenido=body.notas,
            tipo="gestion"
        )
        db.add(nota)
    
    # Crear actividad
    actividad = Actividad(
        cuenta_id=cola.campania.cuenta_id,
        lead_id=lead.id,
        user_id=current_user.id,
        tipo="llamada" if body.resultado_llamada else "gestion",
        direccion="salida",
        asunto=f"Gestión campaña {cola.campania.nombre}",
        descripcion=body.notas,
        resultado=body.resultado_llamada or "gestionado",
        fecha_inicio=cola.assigned_at or datetime.utcnow(),
        fecha_fin=datetime.utcnow(),
    )
    db.add(actividad)
    
    # Si hay callback, crear nuevo registro en cola
    if body.agendar_callback and body.callback_fecha:
        nuevo_cola = ColaLead(
            campania_id=campania_id,
            lead_id=lead.id,
            estado=EstadoCola.PENDIENTE,
            prioridad=cola.prioridad + 1,  # Mayor prioridad
            proximo_intento=body.callback_fecha,
        )
        db.add(nuevo_cola)
    
    # Liberar agente
    db.query(AgenteCampaniaLog).filter(
        AgenteCampaniaLog.campania_id == campania_id,
        AgenteCampaniaLog.agente_id == current_user.id,
        AgenteCampaniaLog.ended_at.is_(None)
    ).update({
        "estado": EstadoAgenteEnCampania.DISPONIBLE,
        "ended_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {
        "success": True,
        "message": "Ficha gestionada correctamente",
        "proxima_ficha_disponible": True
    }


@router.post(
    "/campanias/{campania_id}/saltar-ficha/{cola_id}",
    summary="Saltar ficha (requiere justificación)",
)
def saltar_ficha(
    campania_id: uuid.UUID,
    cola_id: uuid.UUID,
    motivo: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    El agente solicita saltar una ficha.
    La ficha vuelve a la cola con menor prioridad.
    """
    cola = db.query(ColaLead).filter(
        ColaLead.id == cola_id,
        ColaLead.campania_id == campania_id,
        ColaLead.agente_asignado_id == current_user.id
    ).first()
    
    if not cola:
        raise HTTPException(status_code=404, detail="Ficha no encontrada")
    
    # Liberar la ficha
    cola.estado = EstadoCola.PENDIENTE
    cola.agente_asignado_id = None
    cola.assigned_at = None
    cola.motivo_rechazo = motivo
    cola.prioridad -= 1  # Menor prioridad para la próxima vez
    
    # Liberar agente
    db.query(AgenteCampaniaLog).filter(
        AgenteCampaniaLog.campania_id == campania_id,
        AgenteCampaniaLog.agente_id == current_user.id,
        AgenteCampaniaLog.ended_at.is_(None)
    ).update({
        "estado": EstadoAgenteEnCampania.DISPONIBLE,
        "ended_at": datetime.utcnow()
    })
    
    db.commit()
    
    return {
        "success": True,
        "message": "Ficha liberada, solicita una nueva"
    }


# =============================================================================
# Métricas
# =============================================================================

@router.get(
    "/campanias/{campania_id}/metricas",
    response_model=MetricasCampania,
    summary="Métricas de campaña",
)
def get_metricas(
    campania_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtener métricas en tiempo real de la campaña."""
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    verify_account_access(current_user, campania.cuenta_id, db)
    
    hoy = datetime.utcnow().date()
    
    # Contadores
    total_leads = db.query(ColaLead).filter(ColaLead.campania_id == campania_id).count()
    pendientes = db.query(ColaLead).filter(
        ColaLead.campania_id == campania_id,
        ColaLead.estado == EstadoCola.PENDIENTE
    ).count()
    
    # Agentes
    agentes_conectados = db.query(AgenteCampaniaLog).filter(
        AgenteCampaniaLog.campania_id == campania_id,
        AgenteCampaniaLog.ended_at.is_(None)
    ).count()
    
    return {
        "campania_id": campania_id,
        "campania_nombre": campania.nombre,
        "total_leads": total_leads,
        "leads_pendientes": pendientes,
        "leads_gestionados_hoy": db.query(ColaLead).filter(
            ColaLead.campania_id == campania_id,
            ColaLead.estado == EstadoCola.COMPLETADO,
            ColaLead.completed_at >= hoy
        ).count(),
        "agentes_conectados": agentes_conectados,
        "agentes_disponibles": 0,  # TODO: calcular por estado
        "agentes_en_llamada": 0,
        "agentes_pausados": 0,
        "llamadas_realizadas": 0,
        "llamadas_conectadas": 0,
        "porcentaje_contacto": 0.0,
        "top_tipificaciones": []
    }

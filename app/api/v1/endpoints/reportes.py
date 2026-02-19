"""
Módulo de Reportes y Monitores para Contact Center
Endpoints para métricas, dashboards y exportación de datos
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, desc, and_, or_
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_permission
from app.core.database import get_db
from app.models.account import Account
from app.models.campaign import (
    Campania, CampaniaAgente, ColaLead, EstadoCola, 
    AgenteCampaniaLog, EstadoAgenteEnCampania, TipoDiscador
)
from app.models.lead import Lead, LeadBase
from app.models.tipificacion import Tipificacion, Subtipificacion
from app.models.user import User

logger = logging.getLogger(__name__)
router = APIRouter()


def verify_account_access(current_user: User, account_id: uuid.UUID, db: Session) -> None:
    """Verify user has access to the account."""
    if str(current_user.cuenta_id) == str(account_id):
        return
    
    from app.models.role import Role
    if current_user.role_id:
        role = db.query(Role).filter(Role.id == current_user.role_id).first()
        if role and role.permisos:
            if "accounts:*" in role.permisos or "*" in role.permisos:
                return
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")


# =============================================================================
# Dashboard General
# =============================================================================

@router.get(
    "/reportes/dashboard",
    summary="Dashboard general de reportes",
    dependencies=[Depends(require_permission("reportes:read"))],
)
def get_dashboard(
    account_id: uuid.UUID = Query(..., description="ID de la cuenta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtener métricas generales del dashboard."""
    verify_account_access(current_user, account_id, db)
    
    hoy = datetime.utcnow().date()
    inicio_hoy = datetime.combine(hoy, datetime.min.time())
    
    # Campañas activas
    campanas_activas = db.query(Campania).filter(
        Campania.cuenta_id == account_id,
        Campania.estado == "activa"
    ).count()
    
    # Agentes conectados (logs sin ended_at)
    agentes_conectados = db.query(AgenteCampaniaLog).join(Campania).filter(
        Campania.cuenta_id == account_id,
        AgenteCampaniaLog.ended_at.is_(None)
    ).count()
    
    # Leads gestionados hoy
    leads_gestionados = db.query(ColaLead).join(Campania).filter(
        Campania.cuenta_id == account_id,
        ColaLead.estado == EstadoCola.COMPLETADO,
        ColaLead.completed_at >= inicio_hoy
    ).count()
    
    # Leads pendientes
    leads_pendientes = db.query(ColaLead).join(Campania).filter(
        Campania.cuenta_id == account_id,
        ColaLead.estado == EstadoCola.PENDIENTE
    ).count()
    
    # Gestiones por hora (últimas 24h)
    desde = datetime.utcnow() - timedelta(hours=24)
    gestiones_hora = db.query(
        func.date_trunc('hour', ColaLead.completed_at).label('hora'),
        func.count().label('cantidad')
    ).join(Campania).filter(
        Campania.cuenta_id == account_id,
        ColaLead.estado == EstadoCola.COMPLETADO,
        ColaLead.completed_at >= desde
    ).group_by('hora').order_by('hora').all()
    
    # Top campañas por volumen hoy
    top_campanas = db.query(
        Campania.nombre,
        func.count().label('gestiones')
    ).join(ColaLead).filter(
        Campania.cuenta_id == account_id,
        ColaLead.estado == EstadoCola.COMPLETADO,
        ColaLead.completed_at >= inicio_hoy
    ).group_by(Campania.id).order_by(desc('gestiones')).limit(5).all()
    
    return {
        "fecha": hoy.isoformat(),
        "resumen": {
            "campanas_activas": campanas_activas,
            "agentes_conectados": agentes_conectados,
            "leads_gestionados_hoy": leads_gestionados,
            "leads_pendientes": leads_pendientes,
        },
        "gestiones_por_hora": [
            {"hora": g.hora.isoformat() if g.hora else None, "cantidad": g.cantidad}
            for g in gestiones_hora
        ],
        "top_campanas": [
            {"nombre": c.nombre, "gestiones": c.gestiones}
            for c in top_campanas
        ]
    }


# =============================================================================
# Reporte de Bases
# =============================================================================

@router.get(
    "/reportes/bases",
    summary="Reporte de gestión de bases",
    dependencies=[Depends(require_permission("reportes:read"))],
)
def get_reporte_bases(
    account_id: uuid.UUID = Query(...),
    base_id: uuid.UUID | None = Query(None),
    fecha_desde: datetime | None = Query(None),
    fecha_hasta: datetime | None = Query(None),
    tipificacion_id: uuid.UUID | None = Query(None),
    agente_id: uuid.UUID | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtener reporte detallado de bases con filtros."""
    verify_account_access(current_user, account_id, db)
    
    # Query base
    query = db.query(
        ColaLead,
        Campania.nombre.label('campania_nombre'),
        Lead.nombre.label('lead_nombre'),
        Lead.telefono.label('lead_telefono'),
        LeadBase.nombre.label('base_nombre'),
        User.nombre.label('agente_nombre'),
        Tipificacion.nombre.label('tipificacion_nombre'),
        Subtipificacion.nombre.label('subtipificacion_nombre'),
    ).join(
        Campania, ColaLead.campania_id == Campania.id
    ).join(
        Lead, ColaLead.lead_id == Lead.id
    ).outerjoin(
        LeadBase, Lead.lead_base_id == LeadBase.id
    ).outerjoin(
        User, ColaLead.agente_asignado_id == User.id
    ).outerjoin(
        Tipificacion, Lead.tipificacion_id == Tipificacion.id
    ).outerjoin(
        Subtipificacion, Lead.subtipificacion_id == Subtipificacion.id
    ).filter(
        Campania.cuenta_id == account_id
    )
    
    # Aplicar filtros
    if base_id:
        query = query.filter(Lead.lead_base_id == base_id)
    if fecha_desde:
        query = query.filter(ColaLead.completed_at >= fecha_desde)
    if fecha_hasta:
        query = query.filter(ColaLead.completed_at <= fecha_hasta)
    if tipificacion_id:
        query = query.filter(Lead.tipificacion_id == tipificacion_id)
    if agente_id:
        query = query.filter(ColaLead.agente_asignado_id == agente_id)
    
    # Contar total
    total = query.count()
    
    # Paginar
    results = query.order_by(desc(ColaLead.completed_at)).offset(offset).limit(limit).all()
    
    items = []
    for r in results:
        items.append({
            "cola_id": str(r.ColaLead.id),
            "lead_id": str(r.ColaLead.lead_id),
            "lead_nombre": r.lead_nombre,
            "lead_telefono": r.lead_telefono,
            "base_nombre": r.base_nombre,
            "campania_nombre": r.campania_nombre,
            "estado": r.ColaLead.estado,
            "agente_nombre": r.agente_nombre,
            "tipificacion": r.tipificacion_nombre,
            "subtipificacion": r.subtipificacion_nombre,
            "intentos": r.ColaLead.intentos,
            "completed_at": r.ColaLead.completed_at.isoformat() if r.ColaLead.completed_at else None,
            "assigned_at": r.ColaLead.assigned_at.isoformat() if r.ColaLead.assigned_at else None,
        })
    
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


# =============================================================================
# Estado de Bases
# =============================================================================

@router.get(
    "/reportes/bases/{base_id}/estado",
    summary="Estado de una base específica",
    dependencies=[Depends(require_permission("reportes:read"))],
)
def get_estado_base(
    base_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtener métricas de estado de una base."""
    base = db.query(LeadBase).filter(LeadBase.id == base_id).first()
    if not base:
        raise HTTPException(status_code=404, detail="Base no encontrada")
    
    verify_account_access(current_user, base.cuenta_id, db)
    
    # Total leads en la base
    total_leads = db.query(Lead).filter(Lead.lead_base_id == base_id).count()
    
    # Leads en cola pendientes
    pendientes = db.query(ColaLead).join(Lead).filter(
        Lead.lead_base_id == base_id,
        ColaLead.estado == EstadoCola.PENDIENTE
    ).count()
    
    # Leads gestionados (completados)
    gestionados = db.query(ColaLead).join(Lead).filter(
        Lead.lead_base_id == base_id,
        ColaLead.estado == EstadoCola.COMPLETADO
    ).count()
    
    # Distribución por tipificación
    tipificaciones = db.query(
        Tipificacion.nombre,
        Tipificacion.color,
        func.count().label('cantidad')
    ).join(Lead).filter(
        Lead.lead_base_id == base_id,
        Lead.tipificacion_id.isnot(None)
    ).group_by(Tipificacion.id).all()
    
    return {
        "base": {
            "id": str(base.id),
            "nombre": base.nombre,
        },
        "metricas": {
            "total_leads": total_leads,
            "pendientes": pendientes,
            "gestionados": gestionados,
            "avance": round((gestionados / total_leads * 100), 2) if total_leads > 0 else 0
        },
        "distribucion_tipificaciones": [
            {"nombre": t.nombre, "color": t.color, "cantidad": t.cantidad}
            for t in tipificaciones
        ]
    }


# =============================================================================
# Métricas de Agentes
# =============================================================================

@router.get(
    "/reportes/agentes",
    summary="Métricas de productividad de agentes",
    dependencies=[Depends(require_permission("reportes:read"))],
)
def get_metricas_agentes(
    account_id: uuid.UUID = Query(...),
    campania_id: uuid.UUID | None = Query(None),
    fecha_desde: datetime | None = Query(None),
    fecha_hasta: datetime | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtener métricas de productividad por agente."""
    verify_account_access(current_user, account_id, db)
    
    # Default: últimos 7 días
    if not fecha_desde:
        fecha_desde = datetime.utcnow() - timedelta(days=7)
    if not fecha_hasta:
        fecha_hasta = datetime.utcnow()
    
    # Query base de agentes
    agentes_query = db.query(User).filter(
        User.cuenta_id == account_id,
        User.activo.is_(True)
    )
    
    agentes = agentes_query.all()
    resultados = []
    
    for agente in agentes:
        # Logs de actividad en el período
        logs_query = db.query(AgenteCampaniaLog).join(Campania).filter(
            Campania.cuenta_id == account_id,
            AgenteCampaniaLog.agente_id == agente.id,
            AgenteCampaniaLog.started_at >= fecha_desde,
            AgenteCampaniaLog.started_at <= fecha_hasta
        )
        
        if campania_id:
            logs_query = logs_query.filter(AgenteCampaniaLog.campania_id == campania_id)
        
        logs = logs_query.all()
        
        # Calcular tiempo conectado
        tiempo_conectado = sum(
            (log.duracion_segundos or 0) 
            for log in logs 
            if log.estado != EstadoAgenteEnCampania.PAUSADO
        )
        
        # Calcular tiempo pausado
        tiempo_pausado = sum(
            (log.duracion_segundos or 0) 
            for log in logs 
            if log.estado == EstadoAgenteEnCampania.PAUSADO
        )
        
        # Gestiones completadas
        gestiones_query = db.query(ColaLead).join(Campania).filter(
            Campania.cuenta_id == account_id,
            ColaLead.agente_asignado_id == agente.id,
            ColaLead.estado == EstadoCola.COMPLETADO,
            ColaLead.completed_at >= fecha_desde,
            ColaLead.completed_at <= fecha_hasta
        )
        
        if campania_id:
            gestiones_query = gestiones_query.filter(ColaLead.campania_id == campania_id)
        
        fichas_gestionadas = gestiones_query.count()
        
        # Tipificaciones realizadas
        tipificaciones = db.query(
            Tipificacion.nombre,
            func.count().label('cantidad')
        ).join(Lead).join(ColaLead).join(Campania).filter(
            Campania.cuenta_id == account_id,
            ColaLead.agente_asignado_id == agente.id,
            ColaLead.estado == EstadoCola.COMPLETADO,
            ColaLead.completed_at >= fecha_desde,
            ColaLead.completed_at <= fecha_hasta
        ).group_by(Tipificacion.id).all()
        
        resultados.append({
            "agente_id": str(agente.id),
            "nombre": agente.nombre,
            "email": agente.email,
            "tiempo": {
                "conectado_minutos": round(tiempo_conectado / 60, 2),
                "pausado_minutos": round(tiempo_pausado / 60, 2),
                "conectado_horas": round(tiempo_conectado / 3600, 2),
            },
            "productividad": {
                "fichas_gestionadas": fichas_gestionadas,
                "fichas_por_hora": round(fichas_gestionadas / (tiempo_conectado / 3600), 2) if tiempo_conectado > 0 else 0,
            },
            "tipificaciones": [
                {"nombre": t.nombre, "cantidad": t.cantidad}
                for t in tipificaciones
            ]
        })
    
    # Ordenar por fichas gestionadas
    resultados.sort(key=lambda x: x["productividad"]["fichas_gestionadas"], reverse=True)
    
    return {
        "periodo": {
            "desde": fecha_desde.isoformat(),
            "hasta": fecha_hasta.isoformat(),
        },
        "agentes": resultados
    }


# =============================================================================
# Métricas de Campaña Específica
# =============================================================================

@router.get(
    "/reportes/campanas/{campania_id}/metricas",
    summary="Métricas detalladas de una campaña",
    dependencies=[Depends(require_permission("reportes:read"))],
)
def get_metricas_campana(
    campania_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtener métricas completas de una campaña específica."""
    campania = db.query(Campania).filter(Campania.id == campania_id).first()
    if not campania:
        raise HTTPException(status_code=404, detail="Campaña no encontrada")
    
    verify_account_access(current_user, campania.cuenta_id, db)
    
    hoy = datetime.utcnow().date()
    inicio_hoy = datetime.combine(hoy, datetime.min.time())
    
    # Métricas de cola
    total_leads = db.query(ColaLead).filter(ColaLead.campania_id == campania_id).count()
    pendientes = db.query(ColaLead).filter(
        ColaLead.campania_id == campania_id,
        ColaLead.estado == EstadoCola.PENDIENTE
    ).count()
    completados = db.query(ColaLead).filter(
        ColaLead.campania_id == campania_id,
        ColaLead.estado == EstadoCola.COMPLETADO
    ).count()
    gestionados_hoy = db.query(ColaLead).filter(
        ColaLead.campania_id == campania_id,
        ColaLead.estado == EstadoCola.COMPLETADO,
        ColaLead.completed_at >= inicio_hoy
    ).count()
    
    # Agentes activos
    agentes_activos = db.query(CampaniaAgente).filter(
        CampaniaAgente.campania_id == campania_id,
        CampaniaAgente.activo.is_(True)
    ).count()
    
    agentes_conectados = db.query(AgenteCampaniaLog).filter(
        AgenteCampaniaLog.campania_id == campania_id,
        AgenteCampaniaLog.ended_at.is_(None)
    ).count()
    
    # Distribución por tipificación
    tipificaciones = db.query(
        Tipificacion.nombre,
        Tipificacion.color,
        func.count().label('cantidad')
    ).join(Lead).join(ColaLead).filter(
        ColaLead.campania_id == campania_id,
        ColaLead.estado == EstadoCola.COMPLETADO,
        Lead.tipificacion_id.isnot(None)
    ).group_by(Tipificacion.id).all()
    
    # Gestiones por día (últimos 14 días)
    desde = datetime.utcnow() - timedelta(days=14)
    gestiones_dia = db.query(
        func.date(ColaLead.completed_at).label('fecha'),
        func.count().label('cantidad')
    ).filter(
        ColaLead.campania_id == campania_id,
        ColaLead.estado == EstadoCola.COMPLETADO,
        ColaLead.completed_at >= desde
    ).group_by(func.date(ColaLead.completed_at)).order_by('fecha').all()
    
    return {
        "campania": {
            "id": str(campania.id),
            "nombre": campania.nombre,
            "estado": campania.estado,
            "tipo_discador": campania.tipo_discador,
        },
        "metricas": {
            "total_leads": total_leads,
            "pendientes": pendientes,
            "completados": completados,
            "gestionados_hoy": gestionados_hoy,
            "porcentaje_avance": round((completados / total_leads * 100), 2) if total_leads > 0 else 0,
            "agentes_asignados": agentes_activos,
            "agentes_conectados": agentes_conectados,
        },
        "tipificaciones": [
            {"nombre": t.nombre, "color": t.color, "cantidad": t.cantidad}
            for t in tipificaciones
        ],
        "gestiones_por_dia": [
            {"fecha": str(g.fecha), "cantidad": g.cantidad}
            for g in gestiones_dia
        ]
    }


# =============================================================================
# Monitor en Tiempo Real
# =============================================================================

@router.get(
    "/reportes/monitor",
    summary="Monitor en tiempo real",
    dependencies=[Depends(require_permission("reportes:monitor"))],
)
def get_monitor(
    account_id: uuid.UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Obtener estado actual en tiempo real de la operación."""
    verify_account_access(current_user, account_id, db)
    
    # Campañas activas con agentes conectados
    campanas = db.query(Campania).filter(
        Campania.cuenta_id == account_id,
        Campania.estado == "activa"
    ).all()
    
    campanas_data = []
    for camp in campanas:
        # Agentes conectados a esta campaña
        agentes_logs = db.query(
            AgenteCampaniaLog,
            User.nombre.label('agente_nombre')
        ).join(User).filter(
            AgenteCampaniaLog.campania_id == camp.id,
            AgenteCampaniaLog.ended_at.is_(None)
        ).all()
        
        agentes = []
        for log in agentes_logs:
            # Ficha actual (si está gestionando)
            ficha_actual = db.query(ColaLead).filter(
                ColaLead.campania_id == camp.id,
                ColaLead.agente_asignado_id == log.AgenteCampaniaLog.agente_id,
                ColaLead.estado == EstadoCola.GESTIONANDO
            ).first()
            
            agentes.append({
                "agente_id": str(log.AgenteCampaniaLog.agente_id),
                "nombre": log.agente_nombre,
                "estado": log.AgenteCampaniaLog.estado,
                "tiempo_en_estado": (
                    datetime.utcnow() - log.AgenteCampaniaLog.started_at
                ).total_seconds() // 60,  # minutos
                "ficha_actual": str(ficha_actual.id) if ficha_actual else None,
            })
        
        # Leads en cola pendientes
        cola_size = db.query(ColaLead).filter(
            ColaLead.campania_id == camp.id,
            ColaLead.estado == EstadoCola.PENDIENTE
        ).count()
        
        campanas_data.append({
            "campania_id": str(camp.id),
            "nombre": camp.nombre,
            "tipo_discador": camp.tipo_discador,
            "agentes_conectados": len(agentes),
            "agentes": agentes,
            "cola_pendientes": cola_size,
        })
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "campanas_activas": len(campanas_data),
        "campanas": campanas_data,
    }

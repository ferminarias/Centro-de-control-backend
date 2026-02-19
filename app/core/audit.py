"""
Sistema de Auditoría Centralizado
Registra automáticamente cambios en entidades
"""
import uuid
import logging
from datetime import datetime
from typing import Any, TypeVar, Callable
from functools import wraps
from sqlalchemy.orm import Session

from app.models.crm_extras import AuditLog
from app.models.user import User

logger = logging.getLogger(__name__)

T = TypeVar('T')


def log_action(
    db: Session,
    cuenta_id: uuid.UUID,
    user_id: uuid.UUID | None,
    entidad_tipo: str,
    entidad_id: uuid.UUID,
    accion: str,  # create, update, delete, view, login, logout
    campo: str | None = None,
    valor_anterior: Any = None,
    valor_nuevo: Any = None,
    snapshot: dict | None = None,
    ip_address: str | None = None,
    endpoint: str | None = None,
):
    """Registra una acción en el log de auditoría."""
    try:
        log = AuditLog(
            cuenta_id=cuenta_id,
            user_id=user_id,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            accion=accion,
            campo=campo,
            valor_anterior=str(valor_anterior) if valor_anterior is not None else None,
            valor_nuevo=str(valor_nuevo) if valor_nuevo is not None else None,
            snapshot=snapshot,
            ip_address=ip_address,
            endpoint=endpoint,
        )
        db.add(log)
        db.flush()  # No hacemos commit aquí, dejamos que la transacción principal lo maneje
    except Exception as e:
        logger.error(f"Error al crear audit log: {e}")


def log_entity_change(
    db: Session,
    cuenta_id: uuid.UUID,
    user_id: uuid.UUID | None,
    entidad_tipo: str,
    entidad_id: uuid.UUID,
    accion: str,
    old_data: dict | None = None,
    new_data: dict | None = None,
    ip_address: str | None = None,
    endpoint: str | None = None,
):
    """
    Registra cambios en una entidad, detectando automáticamente qué campos cambiaron.
    """
    if accion == "create":
        log_action(
            db=db,
            cuenta_id=cuenta_id,
            user_id=user_id,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            accion="create",
            snapshot=new_data,
            ip_address=ip_address,
            endpoint=endpoint,
        )
    elif accion == "delete":
        log_action(
            db=db,
            cuenta_id=cuenta_id,
            user_id=user_id,
            entidad_tipo=entidad_tipo,
            entidad_id=entidad_id,
            accion="delete",
            snapshot=old_data,
            ip_address=ip_address,
            endpoint=endpoint,
        )
    elif accion == "update" and old_data and new_data:
        # Detectar cambios campo por campo
        for campo, nuevo_valor in new_data.items():
            viejo_valor = old_data.get(campo)
            if viejo_valor != nuevo_valor:
                log_action(
                    db=db,
                    cuenta_id=cuenta_id,
                    user_id=user_id,
                    entidad_tipo=entidad_tipo,
                    entidad_id=entidad_id,
                    accion="update",
                    campo=campo,
                    valor_anterior=viejo_valor,
                    valor_nuevo=nuevo_valor,
                    ip_address=ip_address,
                    endpoint=endpoint,
                )


def audit_entity(entidad_tipo: str, acciones: list[str] = None):
    """
    Decorador para auditar automáticamente endpoints.
    Uso: @audit_entity("lead", ["create", "update", "delete"])
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extraer db y current_user de los kwargs
            db = kwargs.get('db')
            current_user = kwargs.get('current_user')
            
            result = func(*args, **kwargs)
            
            # TODO: Implementar lógica de auditoría automática
            # Esto requiere acceso al request para obtener IP y endpoint
            
            return result
        return wrapper
    return decorator

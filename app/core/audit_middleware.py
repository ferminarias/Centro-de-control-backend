"""
Middleware de Auditoría Automática
Registra automáticamente todas las operaciones de escritura (POST, PUT, PATCH, DELETE)
"""
import json
import logging
import uuid
from typing import Optional
from datetime import datetime

from fastapi import Request, Response
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.database import SessionLocal
from app.models.crm_extras import AuditLog
from app.models.user import User
from app.core.auth import get_current_user

logger = logging.getLogger(__name__)

# Endpoints que NO se auditan (health checks, etc)
EXCLUDED_PATHS = [
    "/health",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
]

# Campos sensibles que se enmascaran
SENSITIVE_FIELDS = [
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "api_key",
    "secret",
]


def mask_sensitive_data(data: dict | list) -> dict | list:
    """Enmascara campos sensibles en los datos."""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                result[key] = "***MASKED***"
            elif isinstance(value, (dict, list)):
                result[key] = mask_sensitive_data(value)
            else:
                result[key] = value
        return result
    elif isinstance(data, list):
        return [mask_sensitive_data(item) if isinstance(item, (dict, list)) else item for item in data]
    return data


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware que audita automáticamente las operaciones de escritura."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        # Verificar si el path está excluido
        path = request.url.path
        if any(path.startswith(excluded) for excluded in EXCLUDED_PATHS):
            return await call_next(request)
        
        # Solo auditar métodos de escritura
        method = request.method
        if method not in ["POST", "PUT", "PATCH", "DELETE"]:
            return await call_next(request)
        
        # Capturar información de la request
        client_ip = request.client.host if request.client else None
        
        # Intentar obtener el usuario autenticado
        user_id = None
        cuenta_id = None
        try:
            # Extraer token del header Authorization
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.replace("Bearer ", "")
                # Crear sesión temporal para obtener usuario
                db = SessionLocal()
                try:
                    from jose import jwt
                    from app.core.config import settings
                    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
                    user_id_str = payload.get("sub")
                    if user_id_str:
                        user = db.query(User).filter(User.id == uuid.UUID(user_id_str)).first()
                        if user:
                            user_id = user.id
                            cuenta_id = user.cuenta_id
                except Exception:
                    pass
                finally:
                    db.close()
        except Exception:
            pass
        
        # Capturar body de la request (solo para métodos que tienen body)
        body_snapshot = None
        if method in ["POST", "PUT", "PATCH"]:
            try:
                body_bytes = await request.body()
                if body_bytes:
                    body_str = body_bytes.decode("utf-8")
                    try:
                        body_json = json.loads(body_str)
                        body_snapshot = mask_sensitive_data(body_json)
                    except json.JSONDecodeError:
                        body_snapshot = {"raw": body_str[:1000]}  # Limitar tamaño
                # Reconstruir el body para que la request continúe normalmente
                async def receive():
                    return {"type": "http.request", "body": body_bytes}
                request._receive = receive
            except Exception as e:
                logger.debug(f"Error capturando body: {e}")
        
        # Ejecutar la request
        response = await call_next(request)
        
        # Determinar la acción basada en el método y status code
        if response.status_code >= 200 and response.status_code < 300:
            action_map = {
                "POST": "create",
                "PUT": "update",
                "PATCH": "update",
                "DELETE": "delete",
            }
            action = action_map.get(method, "unknown")
            
            # Intentar extraer ID de entidad del path
            # Ejemplo: /api/v1/admin/leads/12345 -> entidad: lead, id: 12345
            entidad_tipo, entidad_id = self._extract_entity_info(path)
            
            # Guardar en audit log
            try:
                db = SessionLocal()
                try:
                    audit_log = AuditLog(
                        cuenta_id=cuenta_id,
                        user_id=user_id,
                        entidad_tipo=entidad_tipo,
                        entidad_id=entidad_id,
                        accion=action,
                        snapshot=body_snapshot,
                        ip_address=client_ip,
                        endpoint=f"{method} {path}",
                    )
                    db.add(audit_log)
                    db.commit()
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Error guardando audit log: {e}")
        
        return response
    
    def _extract_entity_info(self, path: str) -> tuple[str, Optional[uuid.UUID]]:
        """Extrae el tipo de entidad y ID del path."""
        parts = path.split("/")
        
        # Mapeo de paths a tipos de entidad
        entity_mapping = {
            "leads": "lead",
            "accounts": "account",
            "users": "user",
            "roles": "role",
            "fields": "field",
            "records": "record",
            "lotes": "lote",
            "bases": "base",
            "webhooks": "webhook",
            "automations": "automation",
            "actividades": "actividad",
            "tareas": "tarea",
            "notas": "nota",
            "tags": "tag",
            "tipificaciones": "tipificacion",
            "subtipificaciones": "subtipificacion",
            "campanias": "campania",
        }
        
        entidad_tipo = "unknown"
        entidad_id = None
        
        for i, part in enumerate(parts):
            if part in entity_mapping:
                entidad_tipo = entity_mapping[part]
                # Intentar obtener el ID que viene después
                if i + 1 < len(parts):
                    try:
                        entidad_id = uuid.UUID(parts[i + 1])
                    except ValueError:
                        pass
                break
        
        return entidad_tipo, entidad_id

#!/usr/bin/env python3
"""
Script para actualizar permisos del Ultra Admin con los nuevos módulos.
Ejecutar después de agregar nuevos módulos al sistema.
"""
import uuid
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.extras

psycopg2.extras.register_default_jsonb()

DB_CONFIG = {
    "host": "yamabiko.proxy.rlwy.net",
    "database": "railway",
    "user": "postgres",
    "password": "DMUblWGALdIxQlXgvLnPvNitgGcoYRyT",
    "port": 12756
}

# Todos los permisos actualizados 2026
ALL_PERMISSIONS = [
    # Wildcard
    "*",
    
    # Módulos wildcards
    "accounts:*", "users:*", "roles:*", "leads:*", "fields:*", "records:*",
    "webhooks:*", "automations:*", "lotes:*", "bases:*", "voip:*",
    "tipificaciones:*", "subtipificaciones:*",
    "actividades:*", "tareas:*", "notas:*", "tags:*", "lead_tags:*",
    "campanias:*", "reportes:*", "audit:*",
    
    # Accounts
    "accounts:create", "accounts:read", "accounts:update", "accounts:delete",
    
    # Users
    "users:create", "users:read", "users:update", "users:delete",
    "users:assign", "users:permissions",
    
    # Roles
    "roles:create", "roles:read", "roles:update", "roles:delete",
    "roles:permissions:manage",
    
    # Leads
    "leads:create", "leads:read", "leads:update", "leads:delete",
    "leads:import", "leads:export", "leads:assign", "leads:bulk_update",
    "leads:move", "leads:merge",
    
    # Fields
    "fields:create", "fields:read", "fields:update", "fields:delete",
    
    # Records
    "records:create", "records:read", "records:update", "records:delete",
    
    # Webhooks
    "webhooks:create", "webhooks:read", "webhooks:update", "webhooks:delete",
    "webhooks:test", "webhooks:logs",
    
    # Automations
    "automations:create", "automations:read", "automations:update", "automations:delete",
    "automations:toggle", "automations:logs",
    
    # Lotes
    "lotes:create", "lotes:read", "lotes:update", "lotes:delete",
    "lotes:import", "lotes:process",
    
    # Bases
    "bases:create", "bases:read", "bases:update", "bases:delete",
    "bases:import", "bases:export", "bases:stats",
    
    # VoIP
    "voip:manage", "voip:providers", "voip:trunks", "voip:pbx",
    "voip:agents", "voip:cdr", "voip:dnc",
    
    # Tipificaciones
    "tipificaciones:create", "tipificaciones:read", "tipificaciones:update", "tipificaciones:delete",
    "subtipificaciones:create", "subtipificaciones:read", "subtipificaciones:update", "subtipificaciones:delete",
    
    # CRM Extras
    "actividades:create", "actividades:read", "actividades:update", "actividades:delete",
    "actividades:assign",
    "tareas:create", "tareas:read", "tareas:update", "tareas:delete",
    "tareas:complete", "tareas:assign",
    "notas:create", "notas:read", "notas:update", "notas:delete",
    "tags:create", "tags:read", "tags:update", "tags:delete",
    "tags:assign", "tags:remove",
    "lead_tags:create", "lead_tags:read", "lead_tags:update", "lead_tags:delete",
    
    # Campañas
    "campanias:create", "campanias:read", "campanias:update", "campanias:delete",
    "campanias:activate", "campanias:pause", "campanias:stop",
    "campanias:agents:assign", "campanias:agents:remove",
    "campanias:bases:assign", "campanias:bases:remove",
    "campanias:gestion", "campanias:fichas:manage",
    "campanias:tipificaciones:config",
    
    # Reportes
    "reportes:dashboard", "reportes:bases", "reportes:agentes",
    "reportes:campanas", "reportes:monitor", "reportes:export",
    "reportes:stats", "reportes:custom",
    
    # Auditoría
    "audit:read", "audit:export", "audit:delete", "audit:config",
    "audit:login", "audit:security",
    
    # Sistema
    "system:config", "system:backup", "system:restore",
    "system:logs", "system:maintenance",
]


def main():
    print("Conectando a la base de datos...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Buscar rol Ultra Admin
        cursor.execute(
            "SELECT id, nombre, permisos FROM roles WHERE nombre = %s",
            ("Ultra Admin",)
        )
        role = cursor.fetchone()
        
        if not role:
            print("[ERROR] Rol 'Ultra Admin' no encontrado")
            sys.exit(1)
        
        print(f"[OK] Rol encontrado: {role['nombre']} (ID: {role['id']})")
        
        # Actualizar permisos
        cursor.execute(
            "UPDATE roles SET permisos = %s::jsonb WHERE id = %s",
            (json.dumps(ALL_PERMISSIONS), str(role['id']))
        )
        conn.commit()
        
        print(f"[OK] Permisos actualizados")
        print(f"  Total permisos: {len(ALL_PERMISSIONS)}")
        
        # Mostrar nuevos permisos agregados
        permisos_anteriores = set(role['permisos'] if role['permisos'] else [])
        permisos_nuevos = set(ALL_PERMISSIONS)
        
        agregados = permisos_nuevos - permisos_anteriores
        if agregados:
            print(f"\n[+] Nuevos permisos agregados ({len(agregados)}):")
            for p in sorted(agregados):
                print(f"   + {p}")
        
        print("\n✅ Actualización completada exitosamente")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
        print("\nConexión cerrada")


if __name__ == "__main__":
    main()

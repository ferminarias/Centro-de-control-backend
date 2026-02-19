#!/usr/bin/env python3
"""
Script para crear un usuario Ultra Admin en la base de datos.
Este usuario tendra acceso completo al sistema multi-tenant.
"""
import uuid
import sys
import os
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
import psycopg2.extras

# Register JSON adapter
psycopg2.extras.register_default_jsonb()

# Configuracion de la base de datos de Railway
DB_CONFIG = {
    "host": "yamabiko.proxy.rlwy.net",
    "database": "railway",
    "user": "postgres",
    "password": "DMUblWGALdIxQlXgvLnPvNitgGcoYRyT",
    "port": 12756
}

# Configuracion del admin
ADMIN_USERNAME = "ultraadmin"
ADMIN_PASSWORD = "admin123"  # Cambiar en produccion
ADMIN_EMAIL = "admin@centrodecontrol.com"
ADMIN_NOMBRE = "Ultra"
ADMIN_APELLIDO = "Administrador"


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode(), salt)
    return hashed.decode()


def main():
    print("Conectando a la base de datos de Railway...")
    
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # 1. Verificar si ya existe una cuenta
        print("\nVerificando cuentas existentes...")
        cursor.execute("SELECT id, nombre FROM accounts WHERE activo = TRUE")
        accounts = cursor.fetchall()
        
        if accounts:
            print(f"   Encontradas {len(accounts)} cuenta(s) activa(s):")
            for acc in accounts:
                print(f"      - {acc['nombre']} (ID: {acc['id']})")
            cuenta_id = accounts[0]['id']
        else:
            print("   No hay cuentas activas. Creando cuenta 'Sistema'...")
            cuenta_id = uuid.uuid4()
            api_key = f"cc_{uuid.uuid4().hex}"
            
            cursor.execute(
                """
                INSERT INTO accounts (id, nombre, api_key, activo, auto_crear_campos)
                VALUES (%s, %s, %s, TRUE, TRUE)
                """,
                (str(cuenta_id), "Sistema", api_key)
            )
            conn.commit()
            print(f"   Cuenta creada: ID={cuenta_id}")
        
        # 2. Crear rol Ultra Admin
        print("\nVerificando/Creando rol 'Ultra Admin'...")
        cursor.execute(
            "SELECT id FROM roles WHERE cuenta_id = %s AND nombre = %s",
            (str(cuenta_id), "Ultra Admin")
        )
        role = cursor.fetchone()
        
        # Todos los permisos posibles - ACTUALIZADO 2026
        all_permissions = [
            # Wildcard - super admin access
            "*",
            
            # === MÓDULOS PRINCIPALES (wildcards) ===
            "accounts:*", "users:*", "roles:*", "leads:*", "fields:*", "records:*",
            "webhooks:*", "automations:*", "lotes:*", "bases:*", "voip:*",
            "tipificaciones:*", "subtipificaciones:*",
            "actividades:*", "tareas:*", "notas:*", "tags:*", "lead_tags:*",
            "campanias:*", "reportes:*", "audit:*", 
            
            # === ACCOUNTS ===
            "accounts:create", "accounts:read", "accounts:update", "accounts:delete",
            
            # === USERS ===
            "users:create", "users:read", "users:update", "users:delete",
            "users:assign", "users:permissions",
            
            # === ROLES ===
            "roles:create", "roles:read", "roles:update", "roles:delete",
            "roles:permissions:manage",
            
            # === LEADS ===
            "leads:create", "leads:read", "leads:update", "leads:delete",
            "leads:import", "leads:export", "leads:assign", "leads:bulk_update",
            "leads:move", "leads:merge",
            
            # === FIELDS ===
            "fields:create", "fields:read", "fields:update", "fields:delete",
            
            # === RECORDS ===
            "records:create", "records:read", "records:update", "records:delete",
            
            # === WEBHOOKS ===
            "webhooks:create", "webhooks:read", "webhooks:update", "webhooks:delete",
            "webhooks:test", "webhooks:logs",
            
            # === AUTOMATIONS ===
            "automations:create", "automations:read", "automations:update", "automations:delete",
            "automations:toggle", "automations:logs",
            
            # === LOTES ===
            "lotes:create", "lotes:read", "lotes:update", "lotes:delete",
            "lotes:import", "lotes:process",
            
            # === BASES ===
            "bases:create", "bases:read", "bases:update", "bases:delete",
            "bases:import", "bases:export", "bases:stats",
            
            # === VOIP / CALL CENTER ===
            "voip:manage", "voip:providers", "voip:trunks", "voip:pbx",
            "voip:agents", "voip:cdr", "voip:dnc",
            
            # === TIPIFICACIONES ===
            "tipificaciones:create", "tipificaciones:read", "tipificaciones:update", "tipificaciones:delete",
            "subtipificaciones:create", "subtipificaciones:read", "subtipificaciones:update", "subtipificaciones:delete",
            
            # === CRM EXTRAS ===
            "actividades:create", "actividades:read", "actividades:update", "actividades:delete",
            "actividades:assign",
            "tareas:create", "tareas:read", "tareas:update", "tareas:delete",
            "tareas:complete", "tareas:assign",
            "notas:create", "notas:read", "notas:update", "notas:delete",
            "tags:create", "tags:read", "tags:update", "tags:delete",
            "tags:assign", "tags:remove",
            "lead_tags:create", "lead_tags:read", "lead_tags:update", "lead_tags:delete",
            
            # === CAMPAÑAS / CONTACT CENTER ===
            "campanias:create", "campanias:read", "campanias:update", "campanias:delete",
            "campanias:activate", "campanias:pause", "campanias:stop",
            "campanias:agents:assign", "campanias:agents:remove",
            "campanias:bases:assign", "campanias:bases:remove",
            "campanias:gestion", "campanias:fichas:manage",
            "campanias:tipificaciones:config",
            
            # === REPORTES ===
            "reportes:dashboard", "reportes:bases", "reportes:agentes",
            "reportes:campanas", "reportes:monitor", "reportes:export",
            "reportes:stats", "reportes:custom",
            
            # === AUDITORÍA / LOGS ===
            "audit:read", "audit:export", "audit:delete", "audit:config",
            "audit:login", "audit:security",
            
            # === SISTEMA ===
            "system:config", "system:backup", "system:restore",
            "system:logs", "system:maintenance",
        ]
        
        if role:
            role_id = role['id']
            print(f"   Rol 'Ultra Admin' ya existe (ID: {role_id})")
            # Actualizar permisos
            cursor.execute(
                "UPDATE roles SET permisos = %s::jsonb WHERE id = %s",
                (json.dumps(all_permissions), str(role_id))
            )
            conn.commit()
            print("   Permisos actualizados")
        else:
            role_id = uuid.uuid4()
            cursor.execute(
                """
                INSERT INTO roles (id, cuenta_id, nombre, descripcion, permisos)
                VALUES (%s, %s, %s, %s, %s::jsonb)
                """,
                (
                    str(role_id),
                    str(cuenta_id),
                    "Ultra Admin",
                    "Acceso completo a todas las funcionalidades del sistema",
                    json.dumps(all_permissions)
                )
            )
            conn.commit()
            print(f"   Rol 'Ultra Admin' creado (ID: {role_id})")
        
        # 3. Crear usuario Ultra Admin
        print(f"\nVerificando/Creando usuario '{ADMIN_USERNAME}'...")
        cursor.execute(
            "SELECT id, activo FROM users WHERE username = %s AND cuenta_id = %s",
            (ADMIN_USERNAME, str(cuenta_id))
        )
        user = cursor.fetchone()
        
        password_hash = get_password_hash(ADMIN_PASSWORD)
        
        if user:
            user_id = user['id']
            cursor.execute(
                """
                UPDATE users 
                SET password_hash = %s, 
                    activo = TRUE, 
                    role_id = %s,
                    email = %s,
                    nombre = %s,
                    apellido = %s
                WHERE id = %s
                """,
                (password_hash, str(role_id), ADMIN_EMAIL, ADMIN_NOMBRE, ADMIN_APELLIDO, str(user_id))
            )
            conn.commit()
            print(f"   Usuario actualizado (ID: {user_id})")
        else:
            user_id = uuid.uuid4()
            cursor.execute(
                """
                INSERT INTO users (id, cuenta_id, role_id, nombre, apellido, email, username, password_hash, activo)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                """,
                (
                    str(user_id),
                    str(cuenta_id),
                    str(role_id),
                    ADMIN_NOMBRE,
                    ADMIN_APELLIDO,
                    ADMIN_EMAIL,
                    ADMIN_USERNAME,
                    password_hash
                )
            )
            conn.commit()
            print(f"   Usuario creado (ID: {user_id})")
        
        # Resumen
        print("\n" + "="*60)
        print("ULTRA ADMIN CREADO/ACTUALIZADO EXITOSAMENTE")
        print("="*60)
        print(f"""
CREDENCIALES DE ACCESO:
   Usuario:    {ADMIN_USERNAME}
   Contrasena: {ADMIN_PASSWORD}
   Email:      {ADMIN_EMAIL}

DATOS DEL SISTEMA:
   Cuenta ID:  {cuenta_id}
   Rol ID:     {role_id}
   Usuario ID: {user_id}

URL DE ACCESO:
   Frontend: http://localhost:3000
   Backend:  https://web-production-7d1a.up.railway.app

IMPORTANTE:
   - Cambia la contrasena despues del primer login
   - Este usuario tiene acceso COMPLETO a todo el sistema
   - Puede acceder a todas las cuentas (multi-tenant)
""")
        
    except Exception as e:
        conn.rollback()
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()
        print("\nConexion cerrada")


if __name__ == "__main__":
    main()

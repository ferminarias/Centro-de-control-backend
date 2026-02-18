#!/usr/bin/env python3
"""Script para aplicar la migracion automaticamente."""

import sys
import psycopg2

DB_CONFIG = {
    "host": "yamabiko.proxy.rlwy.net",
    "port": 12756,
    "database": "railway",
    "user": "postgres",
    "password": "DMUblWGALdIxQlXgvLnPvNitgGcoYRyT"
}

SQL_COMMANDS = [
    ("Creando tabla tipificaciones", """
        CREATE TABLE IF NOT EXISTS tipificaciones (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            nombre VARCHAR(100) NOT NULL,
            descripcion VARCHAR(500),
            color VARCHAR(7) DEFAULT '#6B7280',
            orden INTEGER DEFAULT 0,
            activo BOOLEAN DEFAULT true,
            es_final BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """),
    ("Indice tipificaciones cuenta_id", "CREATE INDEX IF NOT EXISTS ix_tipificaciones_cuenta_id ON tipificaciones(cuenta_id)"),
    ("Indice tipificaciones activo", "CREATE INDEX IF NOT EXISTS ix_tipificaciones_activo ON tipificaciones(activo)"),
    
    ("Creando tabla subtipificaciones", """
        CREATE TABLE IF NOT EXISTS subtipificaciones (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tipificacion_id UUID NOT NULL REFERENCES tipificaciones(id) ON DELETE CASCADE,
            cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            nombre VARCHAR(100) NOT NULL,
            descripcion VARCHAR(500),
            color VARCHAR(7),
            orden INTEGER DEFAULT 0,
            activo BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """),
    ("Indice subtipificaciones tipificacion_id", "CREATE INDEX IF NOT EXISTS ix_subtipificaciones_tipificacion_id ON subtipificaciones(tipificacion_id)"),
    ("Indice subtipificaciones cuenta_id", "CREATE INDEX IF NOT EXISTS ix_subtipificaciones_cuenta_id ON subtipificaciones(cuenta_id)"),
    ("Indice subtipificaciones activo", "CREATE INDEX IF NOT EXISTS ix_subtipificaciones_activo ON subtipificaciones(activo)"),
    
    ("Creando tabla ui_modules", """
        CREATE TABLE IF NOT EXISTS ui_modules (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cuenta_id UUID REFERENCES accounts(id) ON DELETE CASCADE,
            codigo VARCHAR(50) NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            descripcion VARCHAR(500),
            ruta VARCHAR(200) NOT NULL,
            icono VARCHAR(50),
            orden INTEGER DEFAULT 0,
            es_submodulo BOOLEAN DEFAULT false,
            parent_code VARCHAR(50),
            acciones JSONB DEFAULT '{}',
            es_sistema BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """),
    ("Indice ui_modules cuenta_id", "CREATE INDEX IF NOT EXISTS ix_ui_modules_cuenta_id ON ui_modules(cuenta_id)"),
    ("Indice ui_modules codigo", "CREATE INDEX IF NOT EXISTS ix_ui_modules_codigo ON ui_modules(codigo)"),
    
    ("Creando tabla role_module_permissions", """
        CREATE TABLE IF NOT EXISTS role_module_permissions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            module_id UUID NOT NULL REFERENCES ui_modules(id) ON DELETE CASCADE,
            acciones_permitidas JSONB DEFAULT '[]',
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            UNIQUE(role_id, module_id)
        )
    """),
    ("Indice role_module_permissions role_id", "CREATE INDEX IF NOT EXISTS ix_role_module_permissions_role_id ON role_module_permissions(role_id)"),
    ("Indice role_module_permissions module_id", "CREATE INDEX IF NOT EXISTS ix_role_module_permissions_module_id ON role_module_permissions(module_id)"),
    
    ("Columna tipificacion_id en leads", "ALTER TABLE leads ADD COLUMN IF NOT EXISTS tipificacion_id UUID REFERENCES tipificaciones(id) ON DELETE SET NULL"),
    ("Indice leads tipificacion_id", "CREATE INDEX IF NOT EXISTS ix_leads_tipificacion_id ON leads(tipificacion_id)"),
    ("Columna subtipificacion_id en leads", "ALTER TABLE leads ADD COLUMN IF NOT EXISTS subtipificacion_id UUID REFERENCES subtipificaciones(id) ON DELETE SET NULL"),
    ("Indice leads subtipificacion_id", "CREATE INDEX IF NOT EXISTS ix_leads_subtipificacion_id ON leads(subtipificacion_id)"),
]


def main():
    print("*" * 70)
    print("MIGRACION DE BASE DE DATOS - Railway")
    print("*" * 70)
    
    conn = None
    try:
        print(f"\nConectando a {DB_CONFIG['host']}...")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("[OK] Conectado")
        
        success = 0
        failed = 0
        
        for desc, sql in SQL_COMMANDS:
            print(f"\n[+] {desc}...", end=" ")
            try:
                cursor.execute(sql)
                conn.commit()
                print("OK")
                success += 1
            except Exception as e:
                error = str(e).lower()
                if "already exists" in error:
                    print("YA EXISTE")
                    success += 1
                else:
                    print(f"ERROR: {e}")
                    failed += 1
        
        print("\n" + "=" * 70)
        print(f"RESULTADO: {success} exitosos, {failed} fallidos")
        print("=" * 70)
        
        # Verificacion
        print("\nVerificacion:")
        tables = ['tipificaciones', 'subtipificaciones', 'ui_modules', 'role_module_permissions']
        for table in tables:
            cursor.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = %s)", (table,))
            exists = cursor.fetchone()[0]
            print(f"  {'[OK]' if exists else '[FALTA]'} {table}")
        
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'leads' AND column_name IN ('tipificacion_id', 'subtipificacion_id')")
        cols = [r[0] for r in cursor.fetchall()]
        print(f"  {'[OK]' if 'tipificacion_id' in cols else '[FALTA]'} leads.tipificacion_id")
        print(f"  {'[OK]' if 'subtipificacion_id' in cols else '[FALTA]'} leads.subtipificacion_id")
        
        print("\n" + "*" * 70)
        print("MIGRACION COMPLETADA")
        print("*" * 70)
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        if conn:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()

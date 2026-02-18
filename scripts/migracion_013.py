#!/usr/bin/env python3
"""Script para aplicar migracion 013 - CRM Extras."""

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
    # 1. Columnas de asignación en leads
    ("Columna assigned_to_id en leads", 
     "ALTER TABLE leads ADD COLUMN IF NOT EXISTS assigned_to_id UUID REFERENCES users(id) ON DELETE SET NULL"),
    ("Indice assigned_to_id", 
     "CREATE INDEX IF NOT EXISTS ix_leads_assigned_to_id ON leads(assigned_to_id)"),
    ("Columna assigned_at", 
     "ALTER TABLE leads ADD COLUMN IF NOT EXISTS assigned_at TIMESTAMP WITH TIME ZONE"),
    ("Columna assigned_by_rule", 
     "ALTER TABLE leads ADD COLUMN IF NOT EXISTS assigned_by_rule VARCHAR(50)"),
    ("Columna score", 
     "ALTER TABLE leads ADD COLUMN IF NOT EXISTS score INTEGER"),
    ("Columna temperatura", 
     "ALTER TABLE leads ADD COLUMN IF NOT EXISTS temperatura VARCHAR(20)"),
    ("Columna updated_at en leads", 
     "ALTER TABLE leads ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()"),
    
    # 2. Tabla actividades
    ("Tabla actividades", """
        CREATE TABLE IF NOT EXISTS actividades (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            tipo VARCHAR(50) NOT NULL,
            direccion VARCHAR(20) DEFAULT 'salida',
            asunto VARCHAR(255),
            descripcion TEXT,
            metadata JSONB DEFAULT '{}',
            fecha_inicio TIMESTAMP WITH TIME ZONE NOT NULL,
            fecha_fin TIMESTAMP WITH TIME ZONE,
            resultado VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """),
    ("Indices actividades", 
     "CREATE INDEX IF NOT EXISTS ix_actividades_cuenta_id ON actividades(cuenta_id); CREATE INDEX IF NOT EXISTS ix_actividades_lead_id ON actividades(lead_id); CREATE INDEX IF NOT EXISTS ix_actividades_user_id ON actividades(user_id); CREATE INDEX IF NOT EXISTS ix_actividades_fecha_inicio ON actividades(fecha_inicio)"),
    
    # 3. Tabla tareas
    ("Tabla tareas", """
        CREATE TABLE IF NOT EXISTS tareas (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            lead_id UUID REFERENCES leads(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            titulo VARCHAR(255) NOT NULL,
            descripcion TEXT,
            tipo VARCHAR(50) DEFAULT 'seguimiento',
            prioridad VARCHAR(20) DEFAULT 'media',
            estado VARCHAR(30) DEFAULT 'pendiente',
            fecha_vencimiento TIMESTAMP WITH TIME ZONE,
            fecha_completada TIMESTAMP WITH TIME ZONE,
            recordatorio_enviado BOOLEAN DEFAULT false,
            recordatorio_fecha TIMESTAMP WITH TIME ZONE,
            es_recurrente BOOLEAN DEFAULT false,
            frecuencia VARCHAR(30),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """),
    ("Indices tareas", 
     "CREATE INDEX IF NOT EXISTS ix_tareas_cuenta_id ON tareas(cuenta_id); CREATE INDEX IF NOT EXISTS ix_tareas_lead_id ON tareas(lead_id); CREATE INDEX IF NOT EXISTS ix_tareas_user_id ON tareas(user_id); CREATE INDEX IF NOT EXISTS ix_tareas_fecha_vencimiento ON tareas(fecha_vencimiento)"),
    
    # 4. Tabla notas
    ("Tabla notas", """
        CREATE TABLE IF NOT EXISTS notas (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            contenido TEXT NOT NULL,
            tipo VARCHAR(50) DEFAULT 'general',
            es_privada BOOLEAN DEFAULT false,
            es_sistema BOOLEAN DEFAULT false,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """),
    ("Indices notas", 
     "CREATE INDEX IF NOT EXISTS ix_notas_cuenta_id ON notas(cuenta_id); CREATE INDEX IF NOT EXISTS ix_notas_lead_id ON notas(lead_id)"),
    
    # 5. Tabla tags
    ("Tabla tags", """
        CREATE TABLE IF NOT EXISTS tags (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            nombre VARCHAR(100) NOT NULL,
            color VARCHAR(7) DEFAULT '#6B7280',
            descripcion VARCHAR(500),
            es_sistema BOOLEAN DEFAULT false,
            orden INTEGER DEFAULT 0,
            activo BOOLEAN DEFAULT true,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """),
    ("Indices tags", 
     "CREATE INDEX IF NOT EXISTS ix_tags_cuenta_id ON tags(cuenta_id); CREATE INDEX IF NOT EXISTS ix_tags_activo ON tags(activo)"),
    
    # 6. Tabla lead_tags
    ("Tabla lead_tags", """
        CREATE TABLE IF NOT EXISTS lead_tags (
            lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
            tag_id UUID NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
            PRIMARY KEY (lead_id, tag_id)
        )
    """),
    
    # 7. Tabla audit_logs
    ("Tabla audit_logs", """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            entidad_tipo VARCHAR(50) NOT NULL,
            entidad_id UUID NOT NULL,
            accion VARCHAR(30) NOT NULL,
            campo VARCHAR(100),
            valor_anterior TEXT,
            valor_nuevo TEXT,
            snapshot JSONB,
            ip_address VARCHAR(45),
            user_agent VARCHAR(500),
            endpoint VARCHAR(255),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
        )
    """),
    ("Indices audit_logs", 
     "CREATE INDEX IF NOT EXISTS ix_audit_logs_cuenta_id ON audit_logs(cuenta_id); CREATE INDEX IF NOT EXISTS ix_audit_logs_entidad ON audit_logs(entidad_tipo, entidad_id); CREATE INDEX IF NOT EXISTS ix_audit_logs_user_id ON audit_logs(user_id); CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs(created_at)"),
]


def main():
    print("*" * 70)
    print("MIGRACION 013: CRM Extras")
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
        print("\nVerificando tablas:")
        tables = ['actividades', 'tareas', 'notas', 'tags', 'lead_tags', 'audit_logs']
        for table in tables:
            cursor.execute(f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_schema = 'public' AND table_name = '{table}')")
            exists = cursor.fetchone()[0]
            print(f"  {'[OK]' if exists else '[FALTA]'} {table}")
        
        print("\nVerificando columnas de leads:")
        cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'leads' AND column_name IN ('assigned_to_id', 'score', 'temperatura')")
        cols = [r[0] for r in cursor.fetchall()]
        for col in ['assigned_to_id', 'score', 'temperatura']:
            print(f"  {'[OK]' if col in cols else '[FALTA]'} leads.{col}")
        
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

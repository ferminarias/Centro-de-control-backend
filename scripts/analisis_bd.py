#!/usr/bin/env python3
"""
Script de analisis profundo de la base de datos.
Verifica el estado actual de las tablas, columnas y relaciones.
Genera un reporte detallado y un script de migracion si es necesario.
"""

import sys
import psycopg2
from contextlib import contextmanager

# Configuracion de conexion
DB_CONFIG = {
    "host": "yamabiko.proxy.rlwy.net",
    "port": 12756,
    "database": "railway",
    "user": "postgres",
    "password": "DMUblWGALdIxQlXgvLnPvNitgGcoYRyT"
}

@contextmanager
def get_connection():
    """Context manager para conexion a BD."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
    except Exception as e:
        print(f"[ERROR] Error de conexion: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


def check_table_exists(cursor, table_name):
    """Verifica si una tabla existe."""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]


def get_table_columns(cursor, table_name):
    """Obtiene las columnas de una tabla."""
    cursor.execute("""
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = %s
        ORDER BY ordinal_position;
    """, (table_name,))
    return cursor.fetchall()


def get_foreign_keys(cursor, table_name):
    """Obtiene las foreign keys de una tabla."""
    cursor.execute("""
        SELECT
            tc.constraint_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND tc.table_name = %s;
    """, (table_name,))
    return cursor.fetchall()


def get_indexes(cursor, table_name):
    """Obtiene los indices de una tabla."""
    cursor.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = %s
        AND schemaname = 'public';
    """, (table_name,))
    return cursor.fetchall()


def get_row_count(cursor, table_name):
    """Obtiene el conteo de filas de una tabla."""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        return cursor.fetchone()[0]
    except:
        return "N/A"


def analyze_table(cursor, table_name, expected_columns=None):
    """Analiza una tabla completa."""
    print(f"\n{'='*70}")
    print(f"TABLA: {table_name}")
    print('='*70)
    
    # Verificar si existe
    exists = check_table_exists(cursor, table_name)
    if not exists:
        print(f"[FALTA] La tabla NO EXISTE")
        return False, expected_columns or []
    
    print(f"[OK] Tabla existe")
    
    # Conteo de filas
    count = get_row_count(cursor, table_name)
    print(f"Filas: {count}")
    
    # Columnas actuales
    columns = get_table_columns(cursor, table_name)
    column_names = [col[0] for col in columns]
    
    print(f"\nCOLUMNAS ({len(columns)}):")
    print("-" * 70)
    print(f"{'Columna':<30} {'Tipo':<20} {'Nullable':<10}")
    print("-" * 70)
    
    for col in columns:
        col_name, data_type, is_nullable, default = col
        print(f"{col_name:<30} {data_type:<20} {is_nullable:<10}")
    
    # Verificar columnas esperadas
    if expected_columns:
        print(f"\nVERIFICACION DE COLUMNAS ESPERADAS:")
        missing = []
        for col in expected_columns:
            if col in column_names:
                print(f"  [OK] {col}")
            else:
                print(f"  [FALTA] {col}")
                missing.append(col)
    else:
        missing = []
    
    # Foreign Keys
    fks = get_foreign_keys(cursor, table_name)
    if fks:
        print(f"\nFOREIGN KEYS:")
        for fk in fks:
            print(f"  {fk[1]} -> {fk[2]}.{fk[3]}")
    
    # Indices
    indexes = get_indexes(cursor, table_name)
    if indexes:
        print(f"\nINDICES ({len(indexes)}):")
        for idx in indexes:
            print(f"  - {idx[0]}")
    
    return True, missing


def generate_migration_script(missing_tables, missing_columns):
    """Genera script de migracion SQL."""
    script = """-- ============================================
-- SCRIPT DE MIGRACION GENERADO AUTOMATICAMENTE
-- Fecha: 2026-02-18
-- ============================================

BEGIN;

"""
    
    # Tablas que faltan
    if 'tipificaciones' in missing_tables:
        script += """
-- ============================================
-- CREAR TABLA: tipificaciones
-- ============================================
CREATE TABLE tipificaciones (
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
);

CREATE INDEX ix_tipificaciones_cuenta_id ON tipificaciones(cuenta_id);
CREATE INDEX ix_tipificaciones_activo ON tipificaciones(activo);

"""
    
    if 'subtipificaciones' in missing_tables:
        script += """
-- ============================================
-- CREAR TABLA: subtipificaciones
-- ============================================
CREATE TABLE subtipificaciones (
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
);

CREATE INDEX ix_subtipificaciones_tipificacion_id ON subtipificaciones(tipificacion_id);
CREATE INDEX ix_subtipificaciones_cuenta_id ON subtipificaciones(cuenta_id);
CREATE INDEX ix_subtipificaciones_activo ON subtipificaciones(activo);

"""
    
    if 'ui_modules' in missing_tables:
        script += """
-- ============================================
-- CREAR TABLA: ui_modules (Sistema de Roles Modular)
-- ============================================
CREATE TABLE ui_modules (
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
);

CREATE INDEX ix_ui_modules_cuenta_id ON ui_modules(cuenta_id);
CREATE INDEX ix_ui_modules_codigo ON ui_modules(codigo);

CREATE TABLE role_module_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    module_id UUID NOT NULL REFERENCES ui_modules(id) ON DELETE CASCADE,
    acciones_permitidas JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    UNIQUE(role_id, module_id)
);

CREATE INDEX ix_role_module_permissions_role_id ON role_module_permissions(role_id);
CREATE INDEX ix_role_module_permissions_module_id ON role_module_permissions(module_id);

"""
    
    # Columnas que faltan en leads
    if 'leads' in missing_columns:
        cols_to_add = [col for col in missing_columns['leads'] if col in ['tipificacion_id', 'subtipificacion_id']]
        if cols_to_add:
            script += """
-- ============================================
-- AGREGAR COLUMNAS A leads
-- ============================================
"""
            if 'tipificacion_id' in cols_to_add:
                script += """
ALTER TABLE leads 
ADD COLUMN IF NOT EXISTS tipificacion_id UUID REFERENCES tipificaciones(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_leads_tipificacion_id ON leads(tipificacion_id);
"""
            if 'subtipificacion_id' in cols_to_add:
                script += """
ALTER TABLE leads 
ADD COLUMN IF NOT EXISTS subtipificacion_id UUID REFERENCES subtipificaciones(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_leads_subtipificacion_id ON leads(subtipificacion_id);
"""
    
    script += """
COMMIT;

-- ============================================
-- MIGRACION COMPLETADA
-- ============================================
"""
    
    return script


def main():
    print("="*70)
    print("ANALISIS PROFUNDO DE BASE DE DATOS - Railway")
    print("="*70)
    print(f"Host: {DB_CONFIG['host']}")
    print(f"Database: {DB_CONFIG['database']}")
    print(f"User: {DB_CONFIG['user']}")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Verificar version de PostgreSQL
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"\nPostgreSQL: {version}")
        
        # Tablas a analizar
        tables_to_check = {
            'accounts': [],
            'leads': ['tipificacion_id', 'subtipificacion_id'],
            'roles': [],
            'tipificaciones': [],
            'subtipificaciones': [],
            'ui_modules': [],
            'role_module_permissions': [],
        }
        
        missing_tables = []
        missing_columns = {}
        
        for table, expected_cols in tables_to_check.items():
            exists, missing = analyze_table(cursor, table, expected_cols)
            if not exists:
                missing_tables.append(table)
            elif missing:
                missing_columns[table] = missing
        
        # Resumen
        print("\n" + "="*70)
        print("RESUMEN DEL ANALISIS")
        print("="*70)
        
        if not missing_tables and not missing_columns:
            print("[OK] TODO ESTA CORRECTO")
            print("   Todas las tablas y columnas existen.")
        else:
            if missing_tables:
                print(f"\n[FALTA] TABLAS FALTANTES ({len(missing_tables)}):")
                for t in missing_tables:
                    print(f"   - {t}")
            
            if missing_columns:
                print(f"\n[FALTA] COLUMNAS FALTANTES:")
                for table, cols in missing_columns.items():
                    print(f"   - {table}: {', '.join(cols)}")
            
            # Generar script de migracion
            print("\n" + "="*70)
            print("GENERANDO SCRIPT DE MIGRACION...")
            print("="*70)
            
            script = generate_migration_script(missing_tables, missing_columns)
            
            # Guardar script
            script_path = "migracion_generada.sql"
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(script)
            
            print(f"[OK] Script guardado en: {script_path}")
            print("\nPara aplicar la migracion, ejecuta:")
            print(f"   psql -h {DB_CONFIG['host']} -U {DB_CONFIG['user']} -p {DB_CONFIG['port']} -d {DB_CONFIG['database']} -f {script_path}")
            print(f"\nO copia y pega el contenido en la consola de Railway.")
            
            # Mostrar el script
            print("\n" + "="*70)
            print("CONTENIDO DEL SCRIPT:")
            print("="*70)
            print(script)


if __name__ == "__main__":
    main()

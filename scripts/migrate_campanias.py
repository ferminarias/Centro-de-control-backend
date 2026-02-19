#!/usr/bin/env python3
"""
Script de migración para crear tablas de Campañas (Contact Center)
Ejecutar: python scripts/migrate_campanias.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

DB_CONFIG = {
    "host": "yamabiko.proxy.rlwy.net",
    "database": "railway",
    "user": "postgres",
    "password": "DMUblWGALdIxQlXgvLnPvNitgGcoYRyT",
    "port": 12756
}

MIGRATION_SQL = """
-- Tabla principal de Campañas
CREATE TABLE IF NOT EXISTS campanias (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cuenta_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    estado VARCHAR(20) DEFAULT 'borrador',
    tipo_discador VARCHAR(20) DEFAULT 'sin_discador',
    config_discador JSONB DEFAULT '{}',
    permite_llamada_manual BOOLEAN DEFAULT TRUE,
    grabar_llamadas BOOLEAN DEFAULT FALSE,
    horario_inicio VARCHAR(5),
    horario_fin VARCHAR(5),
    dias_operacion JSONB DEFAULT '[]',
    tipificaciones_permitidas JSONB DEFAULT '[]',
    prioridad INTEGER DEFAULT 5,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_campanias_cuenta ON campanias(cuenta_id);
CREATE INDEX IF NOT EXISTS idx_campanias_estado ON campanias(estado);

-- Relación Campaña-Bases
CREATE TABLE IF NOT EXISTS campania_bases (
    campania_id UUID REFERENCES campanias(id) ON DELETE CASCADE,
    base_id UUID REFERENCES lead_bases(id) ON DELETE CASCADE,
    activo BOOLEAN DEFAULT TRUE,
    prioridad INTEGER DEFAULT 5,
    filtros JSONB,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (campania_id, base_id)
);

-- Relación Campaña-Agentes
CREATE TABLE IF NOT EXISTS campania_agentes (
    campania_id UUID REFERENCES campanias(id) ON DELETE CASCADE,
    agente_id UUID REFERENCES users(id) ON DELETE CASCADE,
    activo BOOLEAN DEFAULT TRUE,
    nivel_skill INTEGER DEFAULT 5,
    max_fichas INTEGER DEFAULT 1,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (campania_id, agente_id)
);

CREATE INDEX IF NOT EXISTS idx_campania_agentes_agente ON campania_agentes(agente_id);

-- Cola de Leads (la "fila" de leads pendientes)
CREATE TABLE IF NOT EXISTS cola_leads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campania_id UUID NOT NULL REFERENCES campanias(id) ON DELETE CASCADE,
    lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    estado VARCHAR(20) DEFAULT 'pendiente',
    agente_asignado_id UUID REFERENCES users(id) ON DELETE SET NULL,
    prioridad INTEGER DEFAULT 0,
    intentos INTEGER DEFAULT 0,
    ultimo_intento TIMESTAMP WITH TIME ZONE,
    proximo_intento TIMESTAMP WITH TIME ZONE,
    motivo_rechazo VARCHAR(255),
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    assigned_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_cola_leads_campania ON cola_leads(campania_id);
CREATE INDEX IF NOT EXISTS idx_cola_leads_estado ON cola_leads(estado);
CREATE INDEX IF NOT EXISTS idx_cola_leads_agente ON cola_leads(agente_asignado_id);
CREATE INDEX IF NOT EXISTS idx_cola_leads_proximo ON cola_leads(proximo_intento);

-- Log de actividad de agentes en campañas
CREATE TABLE IF NOT EXISTS agente_campania_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campania_id UUID NOT NULL REFERENCES campanias(id) ON DELETE CASCADE,
    agente_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    estado VARCHAR(20) NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ended_at TIMESTAMP WITH TIME ZONE,
    duracion_segundos INTEGER,
    motivo VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_agente_logs_campania ON agente_campania_logs(campania_id);
CREATE INDEX IF NOT EXISTS idx_agente_logs_agente ON agente_campania_logs(agente_id);
CREATE INDEX IF NOT EXISTS idx_agente_logs_activo ON agente_campania_logs(ended_at) WHERE ended_at IS NULL;

-- Trigger para actualizar updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_campanias_updated_at ON campanias;
CREATE TRIGGER update_campanias_updated_at
    BEFORE UPDATE ON campanias
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;
"""

def main():
    print("=" * 60)
    print("MIGRACION: Creando tablas de Campanas (Contact Center)")
    print("=" * 60)
    
    conn = None
    try:
        print("\n1. Conectando a la base de datos...")
        conn = psycopg2.connect(**DB_CONFIG)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        print("2. Ejecutando migracion...")
        cursor.execute(MIGRATION_SQL)
        
        print("3. Verificando tablas creadas...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('campanias', 'campania_bases', 'campania_agentes', 'cola_leads', 'agente_campania_logs')
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        print("\n[OK] Tablas creadas exitosamente:")
        for table in tables:
            print(f"   - {table[0]}")
        
        print("\n" + "=" * 60)
        print("MIGRACION COMPLETADA")
        print("=" * 60)
        print("""
Resumen:
- campanias: Tabla principal de campanas
- campania_bases: Relacion campana-bases de datos
- campania_agentes: Relacion campana-agentes
- cola_leads: Cola de leads pendientes por gestionar
- agente_campania_logs: Log de sesiones de agentes
""")
        
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()
            print("\nConexion cerrada.")

if __name__ == "__main__":
    main()

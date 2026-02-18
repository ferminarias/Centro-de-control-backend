-- ============================================
-- SCRIPT DE MIGRACION GENERADO AUTOMATICAMENTE
-- Fecha: 2026-02-18
-- ============================================

BEGIN;


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


-- ============================================
-- AGREGAR COLUMNAS A leads
-- ============================================

ALTER TABLE leads 
ADD COLUMN IF NOT EXISTS tipificacion_id UUID REFERENCES tipificaciones(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_leads_tipificacion_id ON leads(tipificacion_id);

ALTER TABLE leads 
ADD COLUMN IF NOT EXISTS subtipificacion_id UUID REFERENCES subtipificaciones(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_leads_subtipificacion_id ON leads(subtipificacion_id);

COMMIT;

-- ============================================
-- MIGRACION COMPLETADA
-- ============================================

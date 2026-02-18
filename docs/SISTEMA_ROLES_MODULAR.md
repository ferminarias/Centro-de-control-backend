# Sistema de Roles Modular - Documentación

## Resumen

Se ha implementado un sistema de roles modular que permite definir permisos sobre pantallas específicas del frontend, manteniendo total compatibilidad con el sistema anterior.

## Cambios Realizados

### Backend

#### 1. Nuevos Modelos (`app/models/ui_module.py`)
- `UIModule`: Representa una pantalla/módulo del frontend
- `RoleModulePermission`: Relación entre roles, módulos y acciones permitidas

#### 2. Servicio (`app/services/ui_module_service.py`)
- Gestión de módulos y permisos
- Módulos por defecto pre-configurados

#### 3. Endpoints Nuevos (`app/api/v1/endpoints/ui_modules.py`)
- `GET /api/v1/accounts/{id}/modules` - Listar módulos
- `POST /api/v1/accounts/{id}/modules/sync` - Sincronizar desde frontend
- `GET /api/v1/roles/{id}/module-permissions` - Permisos de un rol
- `PUT /api/v1/roles/{id}/module-permissions` - Asignar permisos
- `GET /api/v1/auth/me/permissions` - Permisos del usuario actual
- `GET /api/v1/auth/me/modules` - Módulos accesibles para el usuario

#### 4. Migración (`alembic/versions/011_add_ui_modules.py`)
- Crea tablas `ui_modules` y `role_module_permissions`

### Frontend

#### 1. Registro de Módulos (`src/modules/registry.ts`)
- Define todos los módulos disponibles
- Cada módulo tiene: código, nombre, ruta, icono, acciones

#### 2. Hook de Permisos (`src/hooks/usePermissions.ts`)
- `usePermissions()`: Obtiene permisos del usuario
- `useModulePermission(code)`: Permisos para un módulo específico
- Funciones: `can()`, `canView()`, `canCreate()`, `canEdit()`, `canDelete()`

#### 3. Componentes de Protección (`src/components/auth/`)
- `ProtectedRoute`: Protege rutas basado en permisos
- `ProtectedContent`: Oculta contenido sin permiso
- `PermissionButton`: Botón condicional a permisos

#### 4. Sidebar Dinámica (`src/components/layout/Sidebar.tsx`)
- Muestra solo módulos que el usuario puede ver
- Agrupa submódulos automáticamente

## Compatibilidad

✅ **100% Compatible hacia atrás**
- El sistema anterior de permisos (`users:read`, `leads:create`, etc.) sigue funcionando igual
- Los endpoints existentes no cambian
- Los JWT tokens mantienen el mismo formato
- Los roles existentes siguen funcionando

## Módulos Pre-configurados

| Módulo | Ruta | Acciones Disponibles |
|--------|------|---------------------|
| fields | /fields | view, create, edit, delete |
| leads | /leads | view, create, edit, delete, export, import |
| bases | /bases | view, create, edit, delete |
| datasources | /datasources | view, create, edit, delete |
| move_leads | /move-leads | view, execute |

## Uso

### Backend - Asignar Permisos a un Rol

```bash
# Asignar permisos de "view" y "create" en leads a un rol
curl -X PUT http://localhost:8000/api/v1/roles/{role_id}/module-permissions \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "module_id": "{module_uuid}",
    "acciones_permitidas": ["view", "create"]
  }'
```

### Frontend - Proteger una Ruta

```tsx
import { ProtectedRoute } from "@/components/auth";

<Route 
  path="/leads" 
  element={
    <ProtectedRoute module="leads">
      <LeadsPage />
    </ProtectedRoute>
  } 
/>
```

### Frontend - Botón Condicional

```tsx
import { PermissionButton } from "@/components/auth";

<PermissionButton 
  module="leads" 
  action="create"
  onClick={() => openModal()}
  className="btn-primary"
>
  Nuevo Lead
</PermissionButton>
```

### Frontend - Hook de Permisos

```tsx
import { usePermissions } from "@/hooks/usePermissions";

function MyComponent() {
  const { canView, canCreate, canEdit } = usePermissions();
  
  return (
    <div>
      {canView("leads") && <LeadsList />}
      {canCreate("leads") && <NewLeadButton />}
      {canEdit("leads") && <EditButton />}
    </div>
  );
}
```

## Agregar un Nuevo Módulo

### 1. Registrar en Frontend

Editar `src/modules/registry.ts`:

```typescript
export const MODULES_REGISTRY = {
  // ... existing modules
  
  myNewModule: {
    code: "my_new_module",
    name: "Mi Nuevo Módulo",
    description: "Descripción del módulo",
    route: "/my-route",
    icon: "MyIcon",
    order: 10,
    actions: {
      view: { label: "Ver", description: "Ver el módulo" },
      create: { label: "Crear", description: "Crear items" },
      edit: { label: "Editar", description: "Editar items" },
      delete: { label: "Eliminar", description: "Eliminar items" },
    },
  },
};
```

### 2. Sincronizar con Backend

El frontend sincroniza automáticamente los módulos al iniciar, o manualmente:

```typescript
import { syncModules } from "@/api/modules";
import { getModulesForSync } from "@/modules/registry";

await syncModules(accountId, { modules: getModulesForSync() });
```

### 3. Usar en Componentes

```tsx
<ProtectedRoute module="my_new_module">
  <MyNewModulePage />
</ProtectedRoute>
```

## Migración de Datos

Para inicializar los módulos del sistema:

```bash
# Inicializar módulos por defecto (ejecutar una vez)
curl -X POST http://localhost:8000/api/v1/admin/modules/initialize \
  -H "Authorization: Bearer {admin_token}"
```

## Próximos Pasos Sugeridos

1. **Panel de Administración de Roles**: Crear una UI para asignar permisos a roles
2. **Módulos Condicionales**: Mostrar/ocultar acciones específicas dentro de cada pantalla
3. **Permisos a Nivel de Campo**: Controlar qué campos puede ver/editar cada rol
4. **Audit Logging**: Registrar qué permisos se usan

## Notas

- El sistema legacy (`permisos` JSONB en Role) sigue funcionando independientemente
- Los nuevos permisos modulares son adicionales, no reemplazan los existentes
- Un usuario con permiso `*` en un módulo tiene acceso a todas las acciones
- Los módulos pueden ser "de sistema" (disponibles para todas las cuentas) o por cuenta

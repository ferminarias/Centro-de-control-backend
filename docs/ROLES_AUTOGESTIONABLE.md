# Sistema de Roles Autogestionable

## Resumen

Se ha implementado un sistema de roles completamente autogestionable que permite:

1. **Sincronización automática** entre frontend y backend
2. **Gestión visual** de permisos por módulo
3. **Doble sistema**: Permisos modulares (nuevo) + Permisos legacy (API)
4. **Detección automática** de nuevos módulos al agregar páginas

## Cómo Funciona

### Flujo de Trabajo

```
┌─────────────────────────────────────────────────────────────────┐
│  1. REGISTRAR MÓDULO EN FRONTEND                                │
│     └─> Editar src/modules/registry.ts                          │
│         Agregar nuevo módulo con sus acciones                   │
├─────────────────────────────────────────────────────────────────┤
│  2. SINCRONIZACIÓN AUTOMÁTICA                                   │
│     └─> Al abrir panel de Roles se sincronizan los módulos      │
│         con el backend automáticamente                          │
├─────────────────────────────────────────────────────────────────┤
│  3. CONFIGURAR PERMISOS                                         │
│     └─> Desde la UI de Roles, asignar acciones por módulo       │
│         a cada rol de forma visual                              │
├─────────────────────────────────────────────────────────────────┤
│  4. APLICAR EN FRONTEND                                         │
│     └─> Usar usePermissions() o ProtectedRoute para             │
│         proteger rutas y componentes                            │
└─────────────────────────────────────────────────────────────────┘
```

## Estructura de Módulos

### Jerarquía

Los módulos pueden ser:

- **Módulos Padre**: Navegación principal (ej: "Bases de Datos", "Call Center")
- **Submódulos**: Items dentro de un padre (ej: "DataSources", "Campañas")
- **Módulos Simples**: Sin hijos (ej: "Leads", "Webhooks")

### Ejemplo de Registro

```typescript
// src/modules/registry.ts
export const MODULES_REGISTRY = {
  // Módulo simple
  leads: {
    code: "leads",
    name: "Leads",
    route: "/leads",
    icon: "Users",
    order: 1,
    actions: {
      view: { label: "Ver", description: "Ver lista" },
      create: { label: "Crear", description: "Crear leads" },
      edit: { label: "Editar", description: "Editar leads" },
      delete: { label: "Eliminar", description: "Eliminar leads" },
    },
  },
  
  // Módulo padre
  bases: {
    code: "bases",
    name: "Bases de Datos",
    route: "/bases",
    icon: "HardDrive",
    order: 2,
    actions: {
      view: { label: "Ver", description: "Ver bases" },
      create: { label: "Crear", description: "Crear bases" },
    },
  },
  
  // Submódulo
  datasources: {
    code: "datasources",
    name: "DataSources",
    route: "/datasources",
    icon: "GitBranch",
    order: 3,
    isSubModule: true,
    parentCode: "bases",  // <-- Pertenece a "bases"
    actions: {
      view: { label: "Ver", description: "Ver fuentes" },
      create: { label: "Crear", description: "Crear fuentes" },
    },
  },
}
```

## Uso en Componentes

### Proteger una Ruta

```tsx
import { ProtectedRoute } from "@/components/auth";

<Route 
  path="/callcenter/campaigns" 
  element={
    <ProtectedRoute module="campaigns" action="view">
      <Campaigns />
    </ProtectedRoute>
  } 
/>
```

### Botón Condicional

```tsx
import { PermissionButton } from "@/components/auth";

<PermissionButton 
  module="campaigns" 
  action="create"
  onClick={() => openCreateModal()}
  className="btn-primary"
>
  Nueva Campaña
</PermissionButton>
```

### Hook de Permisos

```tsx
import { usePermissions, useModulePermission } from "@/hooks/usePermissions";

// Opción 1: Hook general
function MyComponent() {
  const { can, canView, canCreate, canEdit, canDelete } = usePermissions();
  
  return (
    <div>
      {canView("campaigns") && <CampaignsList />}
      {canCreate("campaigns") && <NewCampaignButton />}
      {can("campaigns", "start") && <StartButton />}
    </div>
  );
}

// Opción 2: Hook específico por módulo
function CampaignComponent() {
  const { canView, canCreate, canEdit, canDelete } = useModulePermission("campaigns");
  
  return (...);
}
```

## Panel de Administración de Roles

### Acceso

Ir a **Administración → Roles** en el sidebar.

### Funcionalidades

1. **Crear Rol**: Botón "Crear rol"
2. **Editar Rol**: Click en "Editar" en la tabla
3. **Eliminar Rol**: Click en el ícono de basura
4. **Sincronizar Módulos**: Botón "Sincronizar" (actualiza con cambios del frontend)

### Tabs de Permisos

#### Tab "Permisos por Módulo" (Recomendado)

- Muestra todos los módulos registrados
- Cada módulo muestra sus acciones disponibles
- Click en "Todo" para seleccionar todas las acciones
- Click individual en cada acción
- Módulos padre pueden expandirse para ver submódulos
- Se guardan automáticamente al hacer "Guardar cambios"

#### Tab "Permisos Legacy" (API)

- Mantiene compatibilidad con el sistema anterior
- Permisos tipo `resource:action` (ej: `users:read`)
- Selección por grupos (Usuarios, Leads, etc.)

## Agregar una Nueva Pantalla (Checklist)

### Paso 1: Crear el Componente de Página

```tsx
// src/pages/MyNewPage.tsx
export default function MyNewPage() {
  return <div>Mi Nueva Página</div>;
}
```

### Paso 2: Registrar el Módulo

```typescript
// src/modules/registry.ts
export const MODULES_REGISTRY = {
  // ... módulos existentes
  
  myNewModule: {
    code: "my_new_module",
    name: "Mi Nueva Página",
    description: "Descripción opcional",
    route: "/my-new-page",
    icon: "MyIcon",  // Nombre del icono de Lucide
    order: 100,      // Orden en la navegación
    actions: {
      view: { label: "Ver", description: "Ver la página" },
      create: { label: "Crear", description: "Crear items" },
      edit: { label: "Editar", description: "Editar items" },
      delete: { label: "Eliminar", description: "Eliminar items" },
      customAction: { label: "Acción Custom", description: "..." },
    },
  },
}
```

### Paso 3: Agregar la Ruta

```tsx
// src/App.tsx
import MyNewPage from "./pages/MyNewPage";

<Route path="/my-new-page" element={<MyNewPage />} />
// O con protección:
<Route path="/my-new-page" element={
  <ProtectedRoute module="my_new_module">
    <MyNewPage />
  </ProtectedRoute>
} />
```

### Paso 4: Sincronizar y Configurar

1. Ir a **Administración → Roles**
2. Click en **Sincronizar** (si no es automático)
3. Editar un rol y asignar permisos en la nueva página
4. Guardar cambios

## Acciones Predefinidas

Acciones comunes que puedes usar:

| Acción | Descripción | Uso típico |
|--------|-------------|------------|
| `view` | Ver/Acceder | Acceso a la página |
| `create` | Crear | Botón "Nuevo" |
| `edit` | Editar | Botón editar en filas |
| `delete` | Eliminar | Botón eliminar |
| `export` | Exportar | Exportar a Excel |
| `import` | Importar | Importar desde archivo |
| `execute` | Ejecutar | Acciones especiales |
| `activate` | Activar/Desactivar | Toggle switches |
| `start` | Iniciar | Iniciar campañas |
| `stop` | Detener | Detener campañas |

## Iconos Disponibles

Los iconos se toman de [Lucide React](https://lucide.dev/icons/). Algunos útiles:

- `Users`, `User`, `UserCog` - Usuarios
- `Database` - Datos/Bases
- `HardDrive` - Almacenamiento
- `Phone`, `PhoneCall`, `Headset` - Call center
- `Megaphone` - Campañas
- `Settings`, `Shield`, `Lock` - Admin/Configuración
- `Webhook`, `Workflow` - Automatizaciones
- `GitBranch` - Fuentes de datos
- `Package` - Lotes
- `Globe`, `Server`, `Link` - Infraestructura

## Compatibilidad

- ✅ Todo el sistema anterior sigue funcionando
- ✅ Los permisos legacy se mantienen en la pestaña "Permisos Legacy"
- ✅ Los nuevos permisos modulares funcionan en paralelo
- ✅ Un usuario puede tener ambos tipos de permisos

## Solución de Problemas

### No aparecen los módulos nuevos

1. Click en **Sincronizar** en el panel de Roles
2. Verificar que el módulo esté bien registrado en `registry.ts`
3. Revisar la consola del navegador por errores

### Los cambios no se guardan

1. Verificar que el rol tenga un nombre
2. Revisar que el backend esté respondiendo
3. Verificar que el usuario tenga permiso `roles:update`

### El módulo no aparece en el sidebar

1. Verificar que el usuario tenga permiso `view` para ese módulo
2. Revisar que `parentCode` esté correcto (si es submódulo)
3. Verificar que no haya errores en la petición `/auth/me/modules`

## Ventajas del Sistema

1. **Autogestionable**: Agregar una nueva pantalla es solo registrarla en el registry
2. **Visual**: Los permisos se configuran con clicks, no con códigos
3. **Flexible**: Cada módulo define sus propias acciones
4. **Jerárquico**: Soporta menús anidados de forma natural
5. **Extensible**: Fácil agregar nuevas acciones personalizadas

# Sistema de Tipificaciones - Documentación

## Resumen

Se ha implementado un sistema completo de **tipificaciones jerárquicas** para clasificar leads. El sistema permite crear categorías y subcategorías anidadas de forma autogestionable.

## Estructura

```
Tipificación (Categoría Principal)
├── Subtipificación 1
├── Subtipificación 2
└── Subtipificación 3

Tipificación Final (sin subcategorías)
```

### Ejemplo Práctico

```
Interesado (Verde)
├── Quiere demo (Verde claro)
├── Pide presupuesto (Verde medio)
└── Decide en X días (Verde oscuro)

En seguimiento (Amarillo)
├── Llamar próxima semana
├── Esperando respuesta
└── Reunión agendada

No interesado (Rojo) [Categoría Final]

No contactado (Gris) [Categoría Final]
```

## Componentes Creados

### Backend

| Archivo | Descripción |
|---------|-------------|
| `app/models/tipificacion.py` | Modelos `Tipificacion` y `Subtipificacion` |
| `app/schemas/tipificacion.py` | Schemas Pydantic |
| `app/api/v1/endpoints/tipificaciones.py` | 15 endpoints REST |
| `alembic/versions/012_add_tipificaciones.py` | Migración BD |

### Frontend

| Archivo | Descripción |
|---------|-------------|
| `src/pages/TipificacionesAdmin.tsx` | Panel de administración completo |
| `src/components/leads/TipificacionModal.tsx` | Modal para tipificar leads |
| `src/hooks/useTipificaciones.ts` | Hooks de React Query |
| `src/api/tipificaciones.ts` | API client |

## API Endpoints

### Tipificaciones
```
GET    /api/v1/admin/accounts/{id}/tipificaciones       # Listar
POST   /api/v1/admin/accounts/{id}/tipificaciones       # Crear
GET    /api/v1/admin/tipificaciones/{id}                # Obtener
PUT    /api/v1/admin/tipificaciones/{id}                # Actualizar
DELETE /api/v1/admin/tipificaciones/{id}                # Eliminar
```

### Subtipificaciones
```
GET    /api/v1/admin/tipificaciones/{id}/subtipificaciones    # Listar
POST   /api/v1/admin/tipificaciones/{id}/subtipificaciones    # Crear
PUT    /api/v1/admin/subtipificaciones/{id}                  # Actualizar
DELETE /api/v1/admin/subtipificaciones/{id}                  # Eliminar
```

### Leads
```
PUT    /api/v1/admin/leads/{id}/tipificacion           # Tipificar un lead
POST   /api/v1/admin/leads/bulk-tipificacion           # Tipificar múltiples
```

### Stats
```
GET    /api/v1/admin/accounts/{id}/tipificaciones/stats # Estadísticas
```

## Uso desde la UI

### 1. Crear Tipificaciones

Ir a **Administración → Tipificaciones**

```
[Nueva Tipificación]

Nombre: Interesado
Descripción: Leads que mostraron interés
Color: #22C55E (Verde)
Orden: 1
Activo: ✓
Categoría final: ☐
```

### 2. Crear Subtipificaciones

Expandir la tipificación y click en **"Sub"**

```
[Nueva Subtipificación]

Nombre: Quiere demo
Descripción: Solicitó una demostración
Color: #4ADE80 (Verde claro - opcional)
Orden: 1
Activo: ✓
```

### 3. Tipificar Leads

Desde la tabla de leads, seleccionar uno o varios y usar el modal de tipificación.

## Características

### ✅ Categorías Finales
Las tipificaciones marcadas como "finales" no permiten subtipificaciones. Útiles para estados terminales como:
- "No interesado"
- "Venta cerrada"
- "Imposible contactar"

### ✅ Colores
Cada tipificación y subtipificación tiene un color para identificación visual:
- Selección desde paleta predefinida
- Colores heredados (sub usa color del padre si no tiene)

### ✅ Ordenamiento
Campo `orden` para controlar la secuencia de visualización.

### ✅ Soft Delete
Las tipificaciones se desactivan (no se eliminan) si tienen leads asociados.

### ✅ Validaciones
- No se puede eliminar tipificación con leads
- Subtipificación debe pertenecer al padre seleccionado
- Colores en formato HEX válido

## Integración en Leads

### Mostrar Tipificación en Tabla

```tsx
// Agregar a la tabla de leads
<td>
  {lead.tipificacion && (
    <div className="flex items-center gap-1">
      <div 
        className="w-2 h-2 rounded-full" 
        style={{ backgroundColor: lead.tipificacion_color }}
      />
      <span className="text-sm">
        {lead.tipificacion_nombre}
        {lead.subtipificacion_nombre && (
          <span className="text-muted-foreground">
            → {lead.subtipificacion_nombre}
          </span>
        )}
      </span>
    </div>
  )}
</td>
```

### Tipificar desde la Tabla

```tsx
import TipificacionModal from "@/components/leads/TipificacionModal"

// ...

<TipificacionModal
  open={showTipModal}
  onOpenChange={setShowTipModal}
  leadIds={selectedLeadIds}
  onSuccess={() => refetch()}
/>
```

## Modelo de Datos

```sql
-- Tipificaciones
tipificaciones
  - id: UUID PK
  - cuenta_id: UUID FK
  - nombre: VARCHAR(100)
  - descripcion: VARCHAR(500)
  - color: VARCHAR(7) default '#6B7280'
  - orden: INTEGER default 0
  - activo: BOOLEAN default true
  - es_final: BOOLEAN default false
  - created_at, updated_at: TIMESTAMP

-- Subtipificaciones  
subtipificaciones
  - id: UUID PK
  - tipificacion_id: UUID FK
  - cuenta_id: UUID FK
  - nombre: VARCHAR(100)
  - descripcion: VARCHAR(500)
  - color: VARCHAR(7) nullable
  - orden: INTEGER default 0
  - activo: BOOLEAN default true
  - created_at, updated_at: TIMESTAMP

-- Leads (columnas agregadas)
leads
  - tipificacion_id: UUID FK nullable
  - subtipificacion_id: UUID FK nullable
```

## Ejemplos de Uso

### Crear tipificación con subtipificaciones

```bash
curl -X POST http://localhost:8000/api/v1/admin/accounts/{id}/tipificaciones \
  -H "Content-Type: application/json" \
  -d '{
    "nombre": "Interesado",
    "color": "#22C55E",
    "subtipificaciones": [
      {"nombre": "Quiere demo", "color": "#4ADE80"},
      {"nombre": "Pide presupuesto"}
    ]
  }'
```

### Tipificar un lead

```bash
curl -X PUT http://localhost:8000/api/v1/admin/leads/{lead_id}/tipificacion \
  -H "Content-Type: application/json" \
  -d '{
    "tipificacion_id": "uuid-tip",
    "subtipificacion_id": "uuid-sub"
  }'
```

### Tipificar múltiples leads

```bash
curl -X POST http://localhost:8000/api/v1/admin/leads/bulk-tipificacion \
  -H "Content-Type: application/json" \
  -d '{
    "lead_ids": ["id1", "id2", "id3"],
    "tipificacion_id": "uuid-tip",
    "subtipificacion_id": "uuid-sub"
  }'
```

## Futuras Mejoras

1. **Filtros por tipificación** en la tabla de leads
2. **Estadísticas avanzadas** (tasa de conversión por tipificación)
3. **Automatizaciones** basadas en cambios de tipificación
4. **Tipificación masiva** con reglas automáticas
5. **Histórico de cambios** de tipificación

## Seguridad

- ✅ Validación de ownership (cuenta_id)
- ✅ Permisos requeridos: `leads:read`, `leads:update`, `leads:delete`
- ✅ Protección contra eliminación si tiene leads asociados
- ✅ Sanitización de inputs

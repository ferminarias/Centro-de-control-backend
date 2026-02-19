# Módulo de Reportes y Monitores - Contact Center

## Visión General
Sistema integral de reportes para campañas de contact center que permite visualizar métricas clave, productividad de agentes, estado de bases y exportar datos a Excel.

## Estructura del Módulo

```
/reportes                    → Página principal
  ├── /dashboard            → Vista general de todas las campañas
  ├── /bases                → Reporte de bases con exportación
  ├── /agentes              → Métricas de productividad por agente
  ├── /campanas/:id         → Detalle de campaña específica
  └── /monitor              → Monitor en tiempo real (supervisores)
```

## Componentes Principales

### 1. Dashboard General (/reportes)
**Objetivo**: Vista panorámica de todas las campañas activas

**Widgets**:
- Cards de resumen (Campañas activas, Agentes conectados, Leads gestionados hoy)
- Gráfico de gestiones por hora
- Top campañas por volumen
- Alertas (bases sin gestionar, agentes pausados >30min)

**Datos necesarios**:
```typescript
interface DashboardStats {
  total_campanas_activas: number
  total_agentes_conectados: number
  total_leads_gestionados_hoy: number
  promedio_contactabilidad: number
  gestiones_por_hora: { hora: string; cantidad: number }[]
  top_campanas: { nombre: string; gestiones: number }[]
}
```

### 2. Reporte de Bases (/reportes/bases)
**Objetivo**: Consultar y exportar gestión de bases

**Filtros**:
- Rango de fechas
- Base específica o todas
- Tipificación
- Agente

**Columnas del reporte**:
| Campo | Descripción |
|-------|-------------|
| lead_id | ID del lead |
| datos_lead | Nombre, teléfono, email (dinámico por cuenta) |
| base | Nombre de la base |
| fecha_ingreso | Cuándo entró a la base |
| ultima_gestion | Fecha de última gestión |
| tipificacion | Última tipificación |
| subtipificacion | Última subtipificación |
| agente | Quién lo gestionó |
| campaña | En qué campaña |
| observaciones | Notas de la gestión |

**Exportación**: Excel (.xlsx) con todas las columnas

### 3. Estado de Bases (/reportes/bases/estado)
**Objetivo**: Visualizar el estado actual de cada base

**Vista**:
- Tabla de bases con métricas
- Gráfico de torta: Distribución por tipificación
- Barras: Gestiones por día

**Métricas por base**:
```typescript
interface BaseEstado {
  base_id: string
  nombre: string
  total_leads: number
  pendientes: number
  gestionados: number
  contactados: number
  no_contactados: number
  por_tipificacion: { nombre: string; cantidad: number; color: string }[]
  ultima_actualizacion: Date
}
```

### 4. Métricas de Agentes (/reportes/agentes)
**Objetivo**: Productividad individual y grupal

**Filtros**:
- Rango de fechas
- Campaña específica
- Agente específico

**Métricas por agente**:
```typescript
interface AgenteMetricas {
  agente_id: string
  nombre: string
  // Tiempo
  tiempo_conectado_minutos: number
  tiempo_pausado_minutos: number
  tiempo_en_llamada_minutos: number
  
  // Productividad
  fichas_gestionadas: number
  llamadas_realizadas: number
  llamadas_conectadas: number
  
  // Eficiencia
  tiempo_promedio_gestion_minutos: number
  contactabilidad: number // %
  
  // Por tipificación
  tipificaciones: { nombre: string; cantidad: number }[]
}
```

**Vistas**:
- Tabla comparativa de agentes
- Gráfico de líneas: Gestiones por día/agente
- Ranking de productividad

### 5. Detalle de Campaña (/reportes/campanas/:id)
**Objetivo**: Métricas específicas de una campaña

**Secciones**:
1. **KPIs Principales**: Contactabilidad, Intentos promedio, Tiempo promedio
2. **Avance**: Gráfico de progreso (pendientes vs gestionados)
3. **Agentes**: Tabla de agentes en la campaña con métricas
4. **Tipificaciones**: Distribución de gestiones
5. **Histórico**: Gráfico de gestiones por día

### 6. Monitor en Tiempo Real (/reportes/monitor)
**Objetivo**: Supervisión live de operación

**Widgets**:
- Agentes online (estado actual)
- Llamadas en curso
- Cola de espera
- Alertas en tiempo real

**Auto-refresh**: Cada 10-30 segundos

## Endpoints API Necesarios

```
GET /api/v1/admin/reportes/dashboard
GET /api/v1/admin/reportes/bases
GET /api/v1/admin/reportes/bases/:id/estado
GET /api/v1/admin/reportes/agentes
GET /api/v1/admin/reportes/agentes/:id
GET /api/v1/admin/reportes/campanas/:id/metricas
GET /api/v1/admin/reportes/campanas/:id/agentes
GET /api/v1/admin/reportes/exportar/bases
```

## Tablas de Base de Datos

Ya existentes:
- `campanias` - Campañas
- `cola_leads` - Cola de leads
- `agente_campania_logs` - Logs de agentes
- `tipificaciones` / `subtipificaciones` - Clasificaciones

A crear:
- `llamadas` - Registro de llamadas (para métricas de contacto)
- `gestiones` - Histórico de gestiones (backup de cola_leads completados)

## Integración con CRM

Los reportes deben poder:
1. **Filtrar por campos personalizados** del CRM
2. **Mostrar datos del lead** según configuración de la cuenta
3. **Exportar con campos CRM** incluidos
4. **Sincronizar tipificaciones** entre campañas y CRM general

## Permisos

- `reportes:read` - Ver reportes
- `reportes:export` - Exportar a Excel
- `reportes:monitor` - Acceso a monitor en tiempo real
- `reportes:all` - Ver reportes de todas las cuentas (ultra admin)

## UI/UX

- **Filtros persistentes**: Guardar filtros preferidos
- **Exportación programada**: Enviar reportes por email periódicamente
- **Responsive**: Tablas scrollables en móvil
- **Gráficos interactivos**: Recharts o Chart.js
- **Dark mode**: Soporte para tema oscuro

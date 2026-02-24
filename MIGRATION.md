# Guía de Migración - Mejoras Arquitectónicas

Este documento describe los cambios realizados y cómo migrar tu instalación existente.

## 📋 Resumen de Cambios

### 1. Seguridad Mejorada
- CORS restringido (ya no acepta `*`)
- Eliminado `AUTH_ENABLED` (auth siempre activa)
- Rate limiting implementado

### 2. Testing Framework
- pytest configurado
- Tests para auth, leads, ingest, campaigns
- Fixtures para DB y autenticación

### 3. Consolidación de Campañas
- Tablas `campaigns` y `campanias` unificadas
- `Campania` ahora incluye campos VoIP
- FKs actualizadas en `campaign_agents`, `campaign_leads`, `call_records`

### 4. Procesamiento Async (Celery)
- Automatizaciones ahora son async
- Webhooks con retry automático
- Redis como broker

### 5. Performance
- Índices optimizados en leads, records, campaign_leads
- Eager loading para evitar N+1 queries
- Rate limiting por endpoint

### 6. Observabilidad
- Logging estructurado con structlog
- Métricas Prometheus en `/metrics`
- JSON logs en producción

---

## 🚀 Pasos de Migración

### Paso 1: Actualizar Dependencias

```bash
pip install -r requirements.txt
```

Nuevas dependencias:
- pytest, pytest-asyncio, pytest-cov
- celery, redis
- structlog, prometheus-client

### Paso 2: Actualizar Variables de Entorno

Edita tu `.env`:

```bash
# Eliminar (ya no existe)
# AUTH_ENABLED=false

# Nuevas variables
ALLOWED_ORIGINS=https://app.tudominio.com,https://admin.tudominio.com

# Seguridad (cambiar en producción)
ADMIN_API_KEY=tu-api-key-seguro
SECRET_KEY=tu-secret-key-minimo-32-caracteres

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
```

### Paso 3: Aplicar Migraciones de Base de Datos

```bash
# Crear migración (si no existe)
docker compose exec app alembic revision --autogenerate -m "consolidate campaigns"

# Aplicar todas las migraciones
docker compose exec app alembic upgrade head
```

Migraciones nuevas:
- `016_consolidate_campaigns.py` - Unifica tablas de campañas
- `017_add_performance_indexes.py` - Agrega índices optimizados

### Paso 4: Iniciar Servicios

```bash
# Reconstruir containers con nuevos servicios
docker compose up -d --build

# Verificar servicios
docker compose ps
```

Servicios nuevos:
- `redis` - Cache y broker de Celery
- `worker` - Procesador de tareas async
- `beat` - Scheduler para tareas periódicas

### Paso 5: Verificar Instalación

```bash
# Ejecutar script de verificación
docker compose exec app python scripts/verify_setup.py

# Correr tests
docker compose exec app pytest -v

# Verificar métricas
curl http://localhost:8000/metrics
```

---

## ⚠️ Breaking Changes

### Cambios en API

1. **Modelo Campaign unificado**
   - Endpoint sigue siendo `/api/v1/admin/accounts/{id}/campaigns`
   - Respuesta ahora incluye campos VoIP (`trunk_id`, `caller_id`, etc.)
   - Estados cambiados: `draft` → `borrador`, `running` → `activa`, etc.

2. **Automatizaciones async**
   - Las automatizaciones ahora se ejecutan en background
   - El endpoint de ingest retorna inmediatamente
   - Revisar logs de worker para errores: `docker compose logs -f worker`

3. **Rate Limiting**
   - Login: 5 intentos/minuto
   - Ingest: 100 requests/minuto
   - Headers de rate limit en respuestas

### Migración de Datos

La migración `016` migra automáticamente:
- Registros de `campaigns` → `campanias`
- Actualiza FKs en tablas relacionadas
- Mapea estados: draft→borrador, running→activa, etc.
- Renombra tabla vieja a `campaigns_backup`

**Verificar después de migrar:**
```sql
-- Contar campañas migradas
SELECT COUNT(*) FROM campanias WHERE trunk_id IS NOT NULL;

-- Verificar backup existe
SELECT COUNT(*) FROM campaigns_backup;
```

---

## 🔧 Configuración Adicional

### Rate Limiting Personalizado

En `app/core/rate_limiter.py`:

```python
# Ejemplo: limitar endpoint específico
@router.post("/api/import")
@rate_limit(10, "1/minute")  # 10 imports por minuto
def import_data(...):
    ...
```

### Métricas Personalizadas

```python
from app.core.metrics import record_lead_created

# En tu endpoint
record_lead_created(str(cuenta_id))
```

### Logging Estructurado

```python
from app.core.logging_config import get_logger

logger = get_logger(__name__)
logger.info("lead_created", lead_id=str(lead.id), cuenta_id=str(cuenta_id))
```

---

## 🧪 Testing

### Correr Tests

```bash
# Todos los tests
docker compose exec app pytest

# Con cobertura
docker compose exec app pytest --cov=app --cov-report=html

# Tests específicos
docker compose exec app pytest tests/test_auth.py -v
```

### Agregar Nuevos Tests

```python
# tests/test_feature.py
def test_new_feature(client, auth_headers):
    response = client.get("/api/endpoint", headers=auth_headers)
    assert response.status_code == 200
```

---

## 📊 Monitoreo

### Métricas Disponibles

- `http_requests_total` - Total de requests HTTP
- `http_request_duration_seconds` - Latencia
- `leads_ingested_total` - Leads ingresados
- `automation_executions_total` - Automatizaciones ejecutadas

### Logs

```bash
# App logs (JSON en producción)
docker compose logs -f app

# Worker logs
docker compose logs -f worker

# Filtrar por nivel
 docker compose logs -f app | grep "ERROR"
```

---

## 🆘 Troubleshooting

### Error: "No module named 'celery'"

```bash
# Reconstruir imagen
docker compose up -d --build
```

### Error: "Campaign not found" después de migrar

```bash
# Verificar migraciones aplicadas
docker compose exec app alembic current

# Si falta, aplicar manualmente
docker compose exec app alembic upgrade 016
```

### Error: "Rate limit exceeded" en development

```bash
# Usar memory backend para rate limiting
# En .env:
ENVIRONMENT=development
```

### Automatizaciones no se ejecutan

```bash
# Verificar worker está corriendo
docker compose ps worker

# Verificar logs
docker compose logs -f worker

# Verificar Redis
docker compose exec redis redis-cli ping
```

---

## 📈 Próximos Pasos Recomendados

1. **Grafana Dashboard** - Importar dashboard para métricas Prometheus
2. **Alerting** - Configurar alertas para errores y rate limits
3. **Backup** - Automatizar backup de `campaigns_backup` antes de eliminar
4. **Tests E2E** - Agregar tests con playwright/cypress
5. **Documentación API** - Actualizar swagger con ejemplos

---

## 📞 Soporte

Para problemas o preguntas:
1. Revisar logs: `docker compose logs`
2. Ejecutar verificación: `python scripts/verify_setup.py`
3. Revisar este documento y AGENTS.md

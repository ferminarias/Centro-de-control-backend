# Centro de Control - Multi-Tenant CRM Ingest Backend

Backend multi-tenant en FastAPI para ingesta de datos de CRM con auto-creación dinámica de campos por cuenta.

## Stack

- **FastAPI** + Pydantic v2
- **PostgreSQL 16** con JSONB
- **SQLAlchemy 2.0** ORM
- **Alembic** migraciones
- **Docker Compose**

## Levantar el proyecto

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Levantar servicios
docker compose up --build -d

# 3. (Opcional) Crear cuenta de prueba
docker compose exec app python scripts/seed.py
```

La API estará disponible en `http://localhost:8000`.
Documentación interactiva: `http://localhost:8000/docs`

## Workflow recomendado

```
1. Crear cuenta nueva        → auto_crear_campos = True
2. Enviar primeros webhooks  → campos se auto-crean desde el JSON
3. Admin revisa campos       → ajusta descripciones y tipos de dato
4. Desactivar auto-creación  → PATCH toggle-auto-create
5. Producción                → solo se aceptan campos definidos
```

## Crear la primera cuenta admin

La API usa Bearer token para rutas admin. El token se configura con `ADMIN_API_KEY` en `.env`.

```bash
# Crear cuenta
curl -X POST http://localhost:8000/api/v1/admin/accounts \
  -H "Authorization: Bearer cc-admin-key-change-me-in-production" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "UEES", "auto_crear_campos": true}'
```

Guardar el `api_key` de la respuesta: se usa en la URL de ingesta.

## Ejemplos de curl

### Ingesta (webhook)

```bash
# Enviar datos de CRM (la api_key va en la URL)
curl -X POST http://localhost:8000/api/v1/ingest/cc_test_uees_key_12345 \
  -H "Content-Type: application/json" \
  -d '{
    "TXTNOMBREAPELLIDO": "SusanaAlarcon",
    "TXTAPELLIDO": "Alarcon",
    "LSTTIPODEDOCUMENTO": "DNI",
    "TXTDNI": "",
    "EMLMAIL": "susanaalarconr@gmail.com",
    "TELTELEFONO": "+351912743033",
    "TELWHATSAPP": "+351912743033",
    "TXTCARRETAINTERES": "TT",
    "TXTMEDIO": "nativo",
    "txtPuesto": "Lifting facial",
    "txtInicioEstudio": "en_30_días"
  }'
```

### Admin - Cuentas

```bash
AUTH="Authorization: Bearer cc-admin-key-change-me-in-production"

# Listar cuentas
curl -H "$AUTH" http://localhost:8000/api/v1/admin/accounts

# Detalle de cuenta
curl -H "$AUTH" http://localhost:8000/api/v1/admin/accounts/{account_id}

# Actualizar cuenta
curl -X PUT -H "$AUTH" -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/admin/accounts/{account_id} \
  -d '{"nombre": "UEES Actualizado"}'

# Toggle auto-creación de campos
curl -X PATCH -H "$AUTH" \
  http://localhost:8000/api/v1/admin/accounts/{account_id}/toggle-auto-create

# Soft-delete cuenta
curl -X DELETE -H "$AUTH" \
  http://localhost:8000/api/v1/admin/accounts/{account_id}
```

### Admin - Campos

```bash
# Listar campos de una cuenta
curl -H "$AUTH" http://localhost:8000/api/v1/admin/accounts/{account_id}/fields

# Crear campo manual
curl -X POST -H "$AUTH" -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/admin/accounts/{account_id}/fields \
  -d '{"nombre_campo": "NUEVO_CAMPO", "tipo_dato": "string", "descripcion": "Campo de prueba"}'

# Actualizar campo
curl -X PUT -H "$AUTH" -H "Content-Type: application/json" \
  http://localhost:8000/api/v1/admin/fields/{field_id} \
  -d '{"tipo_dato": "email", "descripcion": "Email del contacto"}'

# Eliminar campo
curl -X DELETE -H "$AUTH" http://localhost:8000/api/v1/admin/fields/{field_id}
```

### Admin - Registros

```bash
# Listar registros de una cuenta (con paginación)
curl -H "$AUTH" "http://localhost:8000/api/v1/admin/accounts/{account_id}/records?page=1&page_size=10"

# Detalle de un registro
curl -H "$AUTH" http://localhost:8000/api/v1/admin/records/{record_id}
```

## Dashboard: campos auto-creados (últimas 24h)

Consultar directamente en PostgreSQL:

```sql
SELECT a.nombre AS cuenta,
       COUNT(cf.id) AS campos_creados_24h
FROM custom_fields cf
JOIN accounts a ON a.id = cf.cuenta_id
WHERE cf.created_at >= NOW() - INTERVAL '24 hours'
GROUP BY a.nombre
ORDER BY campos_creados_24h DESC;
```

O vía API: listar campos de una cuenta y filtrar por `created_at`.

## Variables de entorno

| Variable | Descripción | Default |
|---|---|---|
| `DATABASE_URL` | URL de conexión PostgreSQL | `postgresql://centro:centro_pass@db:5432/centro_control` |
| `ADMIN_API_KEY` | API key para rutas admin | `cc-admin-key-change-me-in-production` |
| `SECRET_KEY` | Clave secreta | `change-me-to-a-random-secret-key` |
| `ENVIRONMENT` | `development` / `production` | `development` |

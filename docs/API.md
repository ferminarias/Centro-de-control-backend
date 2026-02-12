# Centro de Control - Documentacion de API

Base URL: `http://localhost:8000`

## Autenticacion

Los endpoints bajo `/api/v1/admin/*` requieren un Bearer token.

```
Authorization: Bearer <ADMIN_API_KEY>
```

Si `AUTH_ENABLED=false` (por defecto en desarrollo), la autenticacion esta deshabilitada y no se necesita token.

---

## Health Check

### `GET /health`

Verifica que el servidor este corriendo.

**Respuesta:**
```json
{ "status": "ok" }
```

---

## Ingest (Webhook publico)

### `POST /api/v1/ingest/{account_api_key}`

Recibe datos de un CRM externo. Crea un **Record** (registro crudo) y un **Lead** vinculado a la cuenta.

- **No requiere autenticacion** - se identifica por la `api_key` de la cuenta en la URL.
- Si la cuenta tiene `auto_crear_campos=true`, los campos nuevos se crean automaticamente.
- Si `auto_crear_campos=false`, los campos desconocidos se reportan en la respuesta.

**Path params:**

| Param | Tipo | Descripcion |
|-------|------|-------------|
| `account_api_key` | string | API key de la cuenta destino |

**Body:** JSON libre (el payload del webhook)

```json
{
  "nombre": "Juan Perez",
  "email": "juan@example.com",
  "telefono": "+5491155551234",
  "empresa": "ACME Corp"
}
```

**Respuesta (200):**

```json
{
  "success": true,
  "record_id": "uuid",
  "lead_id": "uuid",
  "unknown_fields": [],
  "auto_create_enabled": true,
  "fields_created": ["nombre", "email", "telefono", "empresa"]
}
```

**Errores:**

| Codigo | Detalle |
|--------|---------|
| 404 | Account not found or inactive |

---

## Admin - Accounts

Todos los endpoints requieren Bearer token (si AUTH_ENABLED=true).

### `POST /api/v1/admin/accounts`

Crea una nueva cuenta. Genera automaticamente una `api_key` unica.

**Body:**

```json
{
  "nombre": "Mi Empresa",
  "auto_crear_campos": true
}
```

**Respuesta (201):**

```json
{
  "id": "uuid",
  "nombre": "Mi Empresa",
  "api_key": "cc_xxxxx",
  "activo": true,
  "auto_crear_campos": true,
  "created_at": "2026-02-12T00:00:00Z",
  "updated_at": "2026-02-12T00:00:00Z"
}
```

### `GET /api/v1/admin/accounts`

Lista todas las cuentas activas con paginacion.

**Query params:**

| Param | Default | Min | Max | Descripcion |
|-------|---------|-----|-----|-------------|
| `page` | 1 | 1 | - | Pagina |
| `page_size` | 20 | 1 | 100 | Items por pagina |

**Respuesta (200):**

```json
{
  "items": [ ... ],
  "total": 5
}
```

### `GET /api/v1/admin/accounts/{account_id}`

Detalle de una cuenta.

**Respuesta (200):** Objeto `AccountResponse`

### `PUT /api/v1/admin/accounts/{account_id}`

Actualiza una cuenta. Todos los campos son opcionales.

**Body:**

```json
{
  "nombre": "Nuevo Nombre",
  "activo": true,
  "auto_crear_campos": false
}
```

### `DELETE /api/v1/admin/accounts/{account_id}`

Soft-delete: marca la cuenta como `activo=false`.

**Respuesta:** 204 No Content

### `PATCH /api/v1/admin/accounts/{account_id}/toggle-auto-create`

Invierte el valor de `auto_crear_campos`.

**Respuesta (200):** Objeto `AccountResponse` actualizado.

---

## Admin - Fields

### `GET /api/v1/admin/accounts/{account_id}/fields`

Lista los campos personalizados de una cuenta.

**Query params:**

| Param | Default | Min | Max |
|-------|---------|-----|-----|
| `page` | 1 | 1 | - |
| `page_size` | 50 | 1 | 200 |

**Respuesta (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "cuenta_id": "uuid",
      "nombre_campo": "email",
      "tipo_dato": "email",
      "descripcion": null,
      "es_requerido": false,
      "created_at": "2026-02-12T00:00:00Z"
    }
  ],
  "total": 3
}
```

### `POST /api/v1/admin/accounts/{account_id}/fields`

Crea un campo manualmente.

**Body:**

```json
{
  "nombre_campo": "empresa",
  "tipo_dato": "string",
  "descripcion": "Nombre de la empresa",
  "es_requerido": false
}
```

Tipos validos: `string`, `number`, `boolean`, `datetime`, `email`, `phone`

**Errores:**

| Codigo | Detalle |
|--------|---------|
| 409 | Field already exists for this account |

### `PUT /api/v1/admin/fields/{field_id}`

Actualiza un campo. Todos los campos son opcionales.

**Body:**

```json
{
  "tipo_dato": "email",
  "descripcion": "Correo electronico",
  "es_requerido": true
}
```

### `DELETE /api/v1/admin/fields/{field_id}`

Elimina un campo permanentemente.

**Respuesta:** 204 No Content

---

## Admin - Leads

### `GET /api/v1/admin/accounts/{account_id}/leads`

Lista los leads de una cuenta con paginacion.

**Query params:**

| Param | Default | Min | Max |
|-------|---------|-----|-----|
| `page` | 1 | 1 | - |
| `page_size` | 20 | 1 | 100 |

**Respuesta (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "cuenta_id": "uuid",
      "record_id": "uuid",
      "datos": {
        "nombre": "Juan Perez",
        "email": "juan@example.com"
      },
      "created_at": "2026-02-12T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### `GET /api/v1/admin/leads/{lead_id}`

Detalle de un lead.

**Respuesta (200):** Objeto `LeadResponse`

**Errores:**

| Codigo | Detalle |
|--------|---------|
| 404 | Lead not found |

---

## Admin - Records

### `GET /api/v1/admin/accounts/{account_id}/records`

Lista los registros crudos de una cuenta.

**Query params:**

| Param | Default | Min | Max |
|-------|---------|-----|-----|
| `page` | 1 | 1 | - |
| `page_size` | 20 | 1 | 100 |

**Respuesta (200):**

```json
{
  "items": [
    {
      "id": "uuid",
      "cuenta_id": "uuid",
      "datos": { ... },
      "metadata_": {
        "source_ip": "127.0.0.1",
        "unknown_fields": null
      },
      "created_at": "2026-02-12T00:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### `GET /api/v1/admin/records/{record_id}`

Detalle de un registro.

**Respuesta (200):** Objeto `RecordResponse`

---

## Resumen de endpoints

| # | Metodo | Ruta | Auth | Descripcion |
|---|--------|------|------|-------------|
| 1 | GET | `/health` | No | Health check |
| 2 | POST | `/api/v1/ingest/{api_key}` | No | Webhook de ingesta |
| 3 | POST | `/api/v1/admin/accounts` | Si | Crear cuenta |
| 4 | GET | `/api/v1/admin/accounts` | Si | Listar cuentas |
| 5 | GET | `/api/v1/admin/accounts/{id}` | Si | Detalle cuenta |
| 6 | PUT | `/api/v1/admin/accounts/{id}` | Si | Actualizar cuenta |
| 7 | DELETE | `/api/v1/admin/accounts/{id}` | Si | Soft-delete cuenta |
| 8 | PATCH | `/api/v1/admin/accounts/{id}/toggle-auto-create` | Si | Toggle auto-crear campos |
| 9 | GET | `/api/v1/admin/accounts/{id}/fields` | Si | Listar campos |
| 10 | POST | `/api/v1/admin/accounts/{id}/fields` | Si | Crear campo |
| 11 | PUT | `/api/v1/admin/fields/{id}` | Si | Actualizar campo |
| 12 | DELETE | `/api/v1/admin/fields/{id}` | Si | Eliminar campo |
| 13 | GET | `/api/v1/admin/accounts/{id}/leads` | Si | Listar leads |
| 14 | GET | `/api/v1/admin/leads/{id}` | Si | Detalle lead |
| 15 | GET | `/api/v1/admin/accounts/{id}/records` | Si | Listar records |
| 16 | GET | `/api/v1/admin/records/{id}` | Si | Detalle record |

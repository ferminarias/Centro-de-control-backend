# AGENTS.md - Centro de Control Backend

This file contains essential information for AI coding agents working on the **Centro de Control** project.

---

## Project Overview

**Centro de Control** is a multi-tenant CRM data ingestion backend built with FastAPI. It receives webhook data from external CRMs, stores it dynamically, and provides a complete call center (VoIP) infrastructure with automated workflows.

### Key Capabilities

- **Multi-tenant data ingestion**: Each account has isolated data via `cuenta_id`
- **Dynamic field auto-creation**: Fields are automatically created from incoming webhook payloads
- **Dual-write storage**: Values stored in both JSONB (`datos`) and real PostgreSQL columns
- **Call center (VoIP)**: Full Asterisk integration with campaigns, agents, and dialer modes
- **Automation engine**: Trigger-based workflows with conditions and actions
- **RBAC**: Role-based access control with JWT tokens and granular permissions

---

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Framework | FastAPI | 0.115.6 |
| ORM | SQLAlchemy | 2.0.36 |
| Validation | Pydantic | v2 |
| Database | PostgreSQL | 16 |
| Migrations | Alembic | 1.14.0 |
| Authentication | PyJWT + passlib | - |
| Rate Limiting | slowapi | - |
| Excel Processing | openpyxl | - |
| VoIP Integration | panoramisk | 1.4 |
| Deployment | Docker Compose | - |

---

## Project Structure

```
.
├── app/
│   ├── api/v1/                 # API layer
│   │   ├── endpoints/          # Route handlers (one file per domain)
│   │   │   ├── accounts.py     # Account CRUD
│   │   │   ├── auth.py         # JWT login/me
│   │   │   ├── automations.py  # Workflow automations
│   │   │   ├── fields.py       # Custom field management
│   │   │   ├── ingest.py       # Public webhook ingestion
│   │   │   ├── leads.py        # Lead CRUD + bulk Excel ops
│   │   │   ├── lead_bases.py   # Lead categorization
│   │   │   ├── lotes.py        # Lead batches
│   │   │   ├── records.py      # Raw webhook records
│   │   │   ├── roles.py        # RBAC roles
│   │   │   ├── users.py        # User management
│   │   │   ├── voip.py         # Call center endpoints
│   │   │   └── webhooks.py     # Outgoing webhooks config
│   │   └── router.py           # API router aggregation
│   ├── core/                   # Core infrastructure
│   │   ├── auth.py             # JWT utilities + dependencies
│   │   ├── config.py           # Pydantic Settings
│   │   ├── database.py         # SQLAlchemy engine + session
│   │   ├── permissions.py      # Permission definitions (RBAC)
│   │   └── security.py         # Admin API key verification
│   ├── models/                 # SQLAlchemy models
│   │   ├── account.py          # Account (tenant) model
│   │   ├── automation.py       # Automation workflows
│   │   ├── field.py            # CustomField definition
│   │   ├── lead.py             # Lead (CRM contact)
│   │   ├── lead_base.py        # Lead categorization bases
│   │   ├── lote.py             # Lead batches
│   │   ├── record.py           # Raw webhook records
│   │   ├── role.py             # RBAC roles
│   │   ├── routing_rule.py     # Lead routing logic
│   │   ├── user.py             # System users
│   │   ├── voip.py             # Call center models
│   │   └── webhook.py          # Outgoing webhook configs
│   ├── schemas/                # Pydantic models (request/response)
│   ├── services/               # Business logic layer
│   │   ├── ami_manager.py      # Asterisk AMI integration
│   │   ├── automation_engine.py # Automation execution
│   │   ├── dialer_engine.py    # Predictive dialer logic
│   │   ├── field_auto_creator.py # Dynamic field creation
│   │   ├── lead_id_generator.py # Sequential ID generation
│   │   ├── routing_engine.py   # Lead routing evaluation
│   │   ├── type_inference.py   # Field type detection
│   │   └── webhook_dispatcher.py # Outgoing webhook sender
│   └── utils/                  # Utilities
│       └── column_manager.py   # PostgreSQL column management
├── alembic/                    # Database migrations
│   └── versions/               # Migration files (numbered sequentially)
├── asterisk/                   # Asterisk configuration files
│   ├── extensions.conf         # Dialplan
│   ├── manager.conf            # AMI configuration
│   ├── pjsip.conf              # SIP endpoints
│   └── rtp.conf                # RTP port range
├── scripts/
│   └── seed.py                 # Test account creation script
└── docs/
    └── API.md                  # Spanish API documentation
```

---

## Development Commands

### Local Development (Docker)

```bash
# 1. Copy environment variables
cp .env.example .env

# 2. Start all services (app + postgres + asterisk)
docker compose up --build -d

# 3. Run database migrations (automatic on startup)
docker compose exec app alembic upgrade head

# 4. Create test account
docker compose exec app python scripts/seed.py
```

### Access Points

| Service | URL |
|---------|-----|
| FastAPI App | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

### Database Migrations

```bash
# Create new migration
docker compose exec app alembic revision -m "description" --autogenerate

# Run migrations
docker compose exec app alembic upgrade head

# Downgrade
docker compose exec app alembic downgrade -1
```

---

## Code Style Guidelines

### Language

The project uses **Spanish** for:
- Database column names (`cuenta_id`, `nombre_campo`, `tipo_dato`)
- Variable names and function parameters
- API response messages
- Documentation comments

Use English for:
- Python code (variables, functions, classes)
- Import statements
- Third-party library interactions

### SQLAlchemy Models

```python
class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    cuenta_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    datos: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    account: Mapped["Account"] = relationship(back_populates="leads")  # noqa: F821
```

### Pydantic Schemas

```python
class LeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cuenta_id: uuid.UUID
    datos: dict[str, Any]
    created_at: datetime
```

### API Endpoints

```python
@router.get(
    "/accounts/{account_id}/leads",
    response_model=LeadListResponse,
    summary="List leads for an account",
)
def list_leads(
    account_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> dict:
    # Implementation
```

---

## Authentication & Security

### Two Authentication Layers

1. **Admin API Key** (`verify_admin_key`)
   - Used for: Admin endpoints under `/api/v1/admin/*`
   - Header: `Authorization: Bearer <ADMIN_API_KEY>`
   - Controlled by `AUTH_ENABLED` setting

2. **JWT Token** (`get_current_user`)
   - Used for: User-specific operations
   - Header: `Authorization: Bearer <jwt_token>`
   - Obtained via: `POST /api/v1/auth/login`
   - Expires: 8 hours (`ACCESS_TOKEN_EXPIRE_MINUTES = 480`)

### Environment Variables

```bash
# Required
DATABASE_URL=postgresql://user:pass@host:5432/dbname
ADMIN_API_KEY=your-secure-admin-key
SECRET_KEY=your-jwt-secret-key

# Optional (defaults shown)
AUTH_ENABLED=false                  # Set to true in production
ENVIRONMENT=development
PORT=8000

# Field exclusions from auto-creation
EXCLUDED_FIELDS=["IDLOTE", "USUARIO_PREASIGNADO"]
```

### Permissions (RBAC)

Permissions follow the pattern `resource:action`:

```python
# Available permissions
users:read, users:create, users:update, users:delete
leads:read, leads:create, leads:update, leads:delete
webhooks:read, webhooks:create, webhooks:update, webhooks:delete
automations:read, automations:create, automations:update, automations:delete
voip:read, voip:create, voip:update, voip:delete
# ... (see app/core/permissions.py for full list)
```

Usage in endpoints:
```python
from app.core.auth import require_permission

@router.post("/users", dependencies=[Depends(require_permission("users:create"))])
def create_user(...):
    ...
```

---

## Database Architecture

### Multi-tenancy

All tables have a `cuenta_id` column (UUID) linking to the `accounts` table. All queries must filter by this column.

### Key Tables

| Table | Purpose |
|-------|---------|
| `accounts` | Tenants/clients |
| `leads` | CRM contacts (dual JSONB + columns) |
| `records` | Raw webhook payloads |
| `custom_fields` | Per-account field definitions |
| `lead_bases` | Lead categorization |
| `lotes` | Lead batches |
| `users` | System users (per account) |
| `roles` | RBAC role definitions |
| `automations` | Workflow triggers/actions |
| `webhooks` | Outgoing webhook configs |
| `campaigns` | Call center campaigns |
| `campaign_leads` | Leads assigned to campaigns |
| `agents` | Call center agents |
| `call_records` | CDR (call detail records) |
| `sip_providers` | VoIP carriers |
| `pbx_nodes` | Asterisk instances |

### Dual-Write Strategy

Lead data is stored twice for flexibility:

1. **JSONB `datos`**: Schema-flexible, API-compatible
2. **Real columns**: For SQL queries, prefixed with `cf_`

When a custom field is created:
1. Row added to `custom_fields` table
2. Real column added to `leads` table via `ALTER TABLE`
3. Values synced via `column_manager.sync_lead_columns()`

---

## Testing

**Note**: The project currently has no automated tests. Tests should be added to a `tests/` directory at the project root.

### Manual Testing with curl

```bash
# Health check
curl http://localhost:8000/health

# Create account (admin)
curl -X POST http://localhost:8000/api/v1/admin/accounts \
  -H "Authorization: Bearer $ADMIN_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Test Account", "auto_crear_campos": true}'

# Ingest webhook (public)
curl -X POST http://localhost:8000/api/v1/ingest/$ACCOUNT_API_KEY \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Juan", "email": "juan@test.com"}'
```

---

## Deployment

### Docker Compose (Development)

```bash
docker compose up --build -d
```

Services:
- `db`: PostgreSQL 16
- `app`: FastAPI with auto-reload
- `asterisk`: Asterisk PBX with AMI/ARI

### Production Considerations

1. **Security**
   - Change default `ADMIN_API_KEY` and `SECRET_KEY`
   - Set `AUTH_ENABLED=true`
   - Use HTTPS
   - Restrict CORS origins in `main.py`

2. **Database**
   - Use managed PostgreSQL (e.g., Railway, AWS RDS)
   - Enable connection pooling
   - Set up backups

3. **Asterisk**
   - Secure AMI credentials
   - Configure firewall rules for SIP ports
   - Use TLS for SIP if possible

4. **Environment Variables**
   ```bash
   ENVIRONMENT=production
   AUTH_ENABLED=true
   DATABASE_URL=postgresql://... (external DB)
   ADMIN_API_KEY=<random-secure-key>
   SECRET_KEY=<random-secure-key>
   ```

---

## Key Implementation Details

### Field Auto-Creation

When `account.auto_crear_campos = True`, incoming webhook fields are automatically registered:

```python
# In app/services/field_auto_creator.py
def auto_create_fields(db, cuenta_id, payload, existing_field_names):
    for key, value in payload.items():
        if key not in existing_field_names and key not in EXCLUDED_FIELDS:
            field = CustomField(
                cuenta_id=cuenta_id,
                nombre_campo=key,
                tipo_dato=infer_type(value),  # string/number/boolean/etc
                column_name=sanitize_column_name(key),  # cf_nombre_campo
            )
            db.add(field)
            add_column_to_leads(db, field.column_name)  # ALTER TABLE
```

### Automation Engine

Automations are trigger-based workflows:

```python
# Trigger: lead_created, lead_updated, etc.
# Conditions: field comparisons (equals, contains, greater_than, etc.)
# Actions: webhook, move_to_base, update_field, send_notification

run_automations(db, cuenta_id, "lead_created", lead=lead_obj)
```

### Lead Routing

Leads are automatically assigned to bases based on `routing_rules`:

```python
lead_base_id = evaluate_routing(db, cuenta_id, payload)
# Rules match payload fields and assign to LeadBase
```

### Sequential ID Generation

Each lead gets a per-account sequential ID (`id_lead`):

```python
id_lead = next_id_lead(db, cuenta_id)  # 1, 2, 3... per account
```

---

## Troubleshooting

### Database connection issues
- Check `DATABASE_URL` format (must start with `postgresql://`)
- Ensure PostgreSQL is running: `docker compose ps`
- Check logs: `docker compose logs db`

### Migrations failing
- Run manually: `docker compose exec app alembic upgrade head`
- Check migration files in `alembic/versions/`

### Asterisk connection issues
- Verify AMI credentials in `asterisk/manager.conf`
- Check Asterisk logs: `docker compose logs asterisk`
- Default AMI user: `centro_ami` / `centro_ami_secret`

### Permission denied errors
- Check `AUTH_ENABLED` setting
- Verify `Authorization` header format
- For admin endpoints, use `ADMIN_API_KEY`

---

## Useful Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/)
- [Alembic Documentation](https://alembic.sqlalchemy.org/)
- [Asterisk AMI](https://wiki.asterisk.org/wiki/pages/viewpage.action?pageId=4817299)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

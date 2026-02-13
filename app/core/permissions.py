"""
Permission definitions and JWT-based auth dependency for the admin panel.

Each permission follows the pattern "resource:action".
Roles store a list of these permission strings in their `permisos` JSONB column.
"""

# ── All available permissions ──────────────────────────────────────────────
ALL_PERMISSIONS: list[str] = [
    # Users
    "users:read",
    "users:create",
    "users:update",
    "users:delete",
    # Roles
    "roles:read",
    "roles:create",
    "roles:update",
    "roles:delete",
    # Leads
    "leads:read",
    "leads:create",
    "leads:update",
    "leads:delete",
    # Lead Bases
    "bases:read",
    "bases:create",
    "bases:update",
    "bases:delete",
    # Lotes
    "lotes:read",
    "lotes:create",
    "lotes:update",
    "lotes:delete",
    # Fields
    "fields:read",
    "fields:create",
    "fields:update",
    "fields:delete",
    # Records
    "records:read",
    # Account settings
    "settings:read",
    "settings:update",
]

# Convenience preset: full access
ADMIN_PERMISSIONS: list[str] = list(ALL_PERMISSIONS)

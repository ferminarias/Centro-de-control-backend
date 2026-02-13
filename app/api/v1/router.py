from fastapi import APIRouter

from app.api.v1.endpoints import (
    accounts, auth, fields, ingest, lead_bases, leads, lotes, records, roles, users,
)

api_router = APIRouter(prefix="/api/v1")

# Public
api_router.include_router(ingest.router, tags=["Ingest"])
api_router.include_router(auth.router, tags=["Auth"])

# Admin
api_router.include_router(accounts.router, prefix="/admin", tags=["Admin - Accounts"])
api_router.include_router(fields.router, prefix="/admin", tags=["Admin - Fields"])
api_router.include_router(leads.router, prefix="/admin", tags=["Admin - Leads"])
api_router.include_router(lead_bases.router, prefix="/admin", tags=["Admin - Lead Bases"])
api_router.include_router(lotes.router, prefix="/admin", tags=["Admin - Lotes"])
api_router.include_router(roles.router, prefix="/admin", tags=["Admin - Roles"])
api_router.include_router(users.router, prefix="/admin", tags=["Admin - Users"])
api_router.include_router(records.router, prefix="/admin", tags=["Admin - Records"])

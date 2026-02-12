from fastapi import APIRouter

from app.api.v1.endpoints import accounts, fields, ingest, lead_bases, leads, records

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(ingest.router, tags=["Ingest"])
api_router.include_router(accounts.router, prefix="/admin", tags=["Admin - Accounts"])
api_router.include_router(fields.router, prefix="/admin", tags=["Admin - Fields"])
api_router.include_router(leads.router, prefix="/admin", tags=["Admin - Leads"])
api_router.include_router(lead_bases.router, prefix="/admin", tags=["Admin - Lead Bases"])
api_router.include_router(records.router, prefix="/admin", tags=["Admin - Records"])

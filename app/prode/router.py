from fastapi import APIRouter

from app.prode.endpoints import admin, auth

prode_router = APIRouter(prefix="/api/prode")
prode_router.include_router(auth.router)
prode_router.include_router(admin.router)

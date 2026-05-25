from fastapi import APIRouter

from app.prode.endpoints import admin, auth, partidos, predicciones, tabla

prode_router = APIRouter(prefix="/api/prode")
prode_router.include_router(auth.router)
prode_router.include_router(admin.router)
prode_router.include_router(partidos.router)
prode_router.include_router(predicciones.router)
prode_router.include_router(tabla.router)

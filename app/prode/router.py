from fastapi import APIRouter

from app.prode.endpoints import admin, auth, equipos, nodis, partidos, predicciones, tabla

prode_router = APIRouter(prefix="/api/prode")
prode_router.include_router(auth.router)
prode_router.include_router(admin.router)
prode_router.include_router(partidos.router)
prode_router.include_router(predicciones.router)
prode_router.include_router(tabla.router)
prode_router.include_router(equipos.router)
prode_router.include_router(nodis.router)

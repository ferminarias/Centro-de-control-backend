from fastapi import APIRouter

from app.prode.endpoints import auth

prode_router = APIRouter(prefix="/api/prode")
prode_router.include_router(auth.router)

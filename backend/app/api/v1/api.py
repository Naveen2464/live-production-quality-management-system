from fastapi import APIRouter
from app.api.v1.endpoints import production, master, quality, migration, dashboard

api_router = APIRouter()

api_router.include_router(production.router, prefix="/production", tags=["Production Management"])
api_router.include_router(master.router, prefix="/master", tags=["Master Data"])
api_router.include_router(quality.router, prefix="/quality", tags=["Quality & NC Management"])
api_router.include_router(quality.router, prefix="", tags=["Quality, NC & Rework Direct"])
api_router.include_router(migration.router, prefix="/import", tags=["Excel Data Migration"])
api_router.include_router(migration.router, prefix="", tags=["Data Import & Export Direct"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["Operational Analytics & Dashboards"])



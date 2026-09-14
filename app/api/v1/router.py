from fastapi import APIRouter

from app.api.v1.endpoints import health, ingestion, search

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health")
api_router.include_router(ingestion.router, prefix="/ingestion")
api_router.include_router(search.router)

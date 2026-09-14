from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.ingestion import router as ingestion_router
from app.api.v1.endpoints.search import router as search_router

__all__ = ["health_router", "ingestion_router", "search_router"]

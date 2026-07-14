from fastapi import APIRouter

from app.api.ai import router as ai_router
from app.api.collector import router as collector_router
from app.api.gaps import deep_research_router
from app.api.gaps import router as gaps_router
from app.api.graph import router as graph_router
from app.api.ingestion import router as ingestion_router
from app.api.research import router as research_router
from app.api.search import related_router
from app.api.search import router as search_router
from app.api.training import router as training_router

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(collector_router)
api_router.include_router(research_router)
api_router.include_router(related_router)
api_router.include_router(search_router)
api_router.include_router(graph_router)
api_router.include_router(training_router)
api_router.include_router(gaps_router)
api_router.include_router(deep_research_router)
api_router.include_router(ingestion_router)


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

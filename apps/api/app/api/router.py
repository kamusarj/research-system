from fastapi import APIRouter

from app.api.ai import router as ai_router
from app.api.ai_connections import router as ai_connections_router
from app.api.auth import router as auth_router
from app.api.chat import router as chat_router
from app.api.collector import router as collector_router
from app.api.documents import router as documents_router
from app.api.gaps import deep_research_router
from app.api.gaps import router as gaps_router
from app.api.graph import router as graph_router
from app.api.graph_changes import router as graph_changes_router
from app.api.ingestion import router as ingestion_router
from app.api.intake_receipts import router as intake_receipts_router
from app.api.ontology import router as ontology_router
from app.api.research import router as research_router
from app.api.research_runs import router as research_runs_router
from app.api.search import related_router
from app.api.search import router as search_router
from app.api.system import router as system_router

api_router = APIRouter()
api_router.include_router(ai_router)
api_router.include_router(ai_connections_router)
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(collector_router)
api_router.include_router(documents_router)
api_router.include_router(research_router)
api_router.include_router(research_runs_router)
api_router.include_router(related_router)
api_router.include_router(search_router)
api_router.include_router(graph_router)
api_router.include_router(graph_changes_router)
api_router.include_router(gaps_router)
api_router.include_router(deep_research_router)
api_router.include_router(ingestion_router)
api_router.include_router(intake_receipts_router)
api_router.include_router(ontology_router)
api_router.include_router(system_router)


@api_router.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}

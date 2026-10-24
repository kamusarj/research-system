from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.schemas.system import FeatureFlagsRead, SystemReadinessRead
from app.services.graph_invariants import check_graph_invariants

router = APIRouter(prefix="/system", tags=["system"])


def feature_flags() -> FeatureFlagsRead:
    return FeatureFlagsRead(
        graph_v2=settings.graph_v2_enabled,
        document_workspaces=settings.graph_v2_enabled
        and settings.graph_v2_documents_enabled,
        graph_chat=settings.graph_v2_enabled and settings.graph_v2_chat_enabled,
        rate_limits=settings.rate_limit_enabled,
        research_agent=settings.research_agent_enabled,
    )


@router.get("/features", response_model=FeatureFlagsRead)
def features() -> FeatureFlagsRead:
    return feature_flags()


@router.get("/readiness", response_model=SystemReadinessRead)
def readiness(db: Session = Depends(get_db)) -> SystemReadinessRead:
    graph = check_graph_invariants(db)
    return SystemReadinessRead(
        status="ready" if graph.valid else "degraded",
        features=feature_flags(),
        graph=graph,
    )

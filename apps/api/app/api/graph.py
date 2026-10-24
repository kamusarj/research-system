import logging
import time
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import get_db
from app.schemas.graph import GraphQuery, GraphResponse
from app.services.gaps import list_gaps, serialize_gap
from app.services.graph import (
    ego_graph,
    filter_graph,
    graph_clusters,
    graph_projection,
    graph_repository,
    ontology_graph_projection,
)
from app.services.projection_state import mark_projection_rebuilt, projection_status

router = APIRouter(prefix="/graph", tags=["graph"])
logger = logging.getLogger("research-api.graph-projection")

GRAPH_READ_CACHE_CONTROL = "private, max-age=30, stale-while-revalidate=60"


def _cache_graph_read(response: Response) -> None:
    response.headers["Cache-Control"] = GRAPH_READ_CACHE_CONTROL
    response.headers["Vary"] = "Cookie, Authorization"


def _csv(value: str | None) -> set[str]:
    return {part.strip() for part in (value or "").split(",") if part.strip()}


def _query(
    query: str | None,
    node_types: str | None,
    source_types: str | None,
    min_confidence: float,
    date_from: datetime | None,
    date_to: datetime | None,
    limit: int,
    depth: int,
    root_node_id: str | None,
    view: Literal["relationship", "hierarchy"],
) -> GraphQuery:
    return GraphQuery(
        query=query,
        node_types=_csv(node_types),
        source_types=_csv(source_types),
        min_confidence=min_confidence,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        depth=depth,
        root_node_id=root_node_id,
        view=view,
    )


@router.get("", response_model=GraphResponse, dependencies=[Depends(_cache_graph_read)])
def graph(
    query: str | None = None,
    node_types: str | None = None,
    source_types: str | None = None,
    min_confidence: float = Query(0, ge=0, le=1),
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(settings.graph_default_node_limit, ge=1, le=settings.graph_max_node_limit),
    depth: int = Query(1, ge=1, le=settings.graph_max_depth),
    root_node_id: str | None = None,
    view: Literal["relationship", "hierarchy"] = "relationship",
    db: Session = Depends(get_db),
) -> GraphResponse:
    return graph_repository().query(
        db,
        _query(
            query,
            node_types,
            source_types,
            min_confidence,
            date_from,
            date_to,
            limit,
            depth,
            root_node_id,
            view,
        ),
    )


@router.get("/system", response_model=GraphResponse, dependencies=[Depends(_cache_graph_read)])
def system_graph(
    limit: int = Query(settings.graph_max_node_limit, ge=1, le=settings.graph_max_node_limit),
    db: Session = Depends(get_db),
) -> GraphResponse:
    """Return the canonical Business AI Agents ontology as a separate read-only map."""

    return filter_graph(
        ontology_graph_projection(db),
        GraphQuery(limit=limit, depth=settings.graph_max_depth, view="hierarchy"),
        "postgres-system",
    )


@router.get(
    "/node/{node_id:path}",
    response_model=GraphResponse,
    dependencies=[Depends(_cache_graph_read)],
)
def node(node_id: str, db: Session = Depends(get_db)) -> GraphResponse:
    return graph_repository().query(
        db,
        GraphQuery(
            limit=settings.graph_max_neighbors + 1,
            depth=1,
            root_node_id=node_id,
        ),
    )


@router.get(
    "/nodes/{node_id:path}/neighbors",
    response_model=GraphResponse,
    dependencies=[Depends(_cache_graph_read)],
)
def neighbors(
    node_id: str,
    limit: int = Query(10, ge=1, le=settings.graph_max_neighbors),
    depth: int = Query(1, ge=1, le=settings.graph_max_depth),
    db: Session = Depends(get_db),
) -> GraphResponse:
    return graph_repository().query(
        db,
        GraphQuery(limit=limit + 1, depth=depth, root_node_id=node_id),
    )


@router.get("/search", response_model=GraphResponse, dependencies=[Depends(_cache_graph_read)])
def search(
    query: str = Query(min_length=1),
    node_types: str | None = None,
    limit: int = Query(20, ge=1, le=settings.graph_max_node_limit),
    db: Session = Depends(get_db),
) -> GraphResponse:
    return graph_repository().query(
        db,
        GraphQuery(query=query, node_types=_csv(node_types), limit=limit),
    )


@router.get("/ego/{node_id:path}")
def ego(node_id: str, db: Session = Depends(get_db)) -> dict:
    response = graph_repository().query(
        db,
        GraphQuery(
            limit=settings.graph_max_neighbors + 1,
            depth=1,
            root_node_id=node_id,
        ),
    )
    return ego_graph(response, node_id)


@router.get("/path")
def path(
    source: str = Query(alias="from"),
    target: str = Query(alias="to"),
    db: Session = Depends(get_db),
) -> dict:
    return graph_repository().path(db, source, target)


@router.get("/stats")
def stats(db: Session = Depends(get_db)) -> dict:
    if settings.graph_data_provider == "postgres":
        projection = graph_projection(db)
    else:
        projection = (
            graph_repository()
            .query(
                db,
                GraphQuery(limit=settings.graph_max_node_limit),
            )
            .model_dump()
        )
    by_type: dict[str, int] = {}
    for graph_node in projection["nodes"]:
        by_type[graph_node["type"]] = by_type.get(graph_node["type"], 0) + 1
    return {
        "nodes": len(projection["nodes"]),
        "edges": len(projection["edges"]),
        "clusters": len(graph_clusters(projection)),
        "by_type": by_type,
    }


@router.get("/clusters")
def clusters(db: Session = Depends(get_db)) -> list[dict]:
    return graph_repository().clusters(db)


@router.get("/gaps")
def gaps(db: Session = Depends(get_db)) -> list[dict]:
    return [serialize_gap(gap) for gap in list_gaps(db)]


@router.post("/rebuild")
def rebuild(db: Session = Depends(get_db)) -> dict:
    started = time.monotonic()
    result = graph_repository().rebuild(db)
    views = result.get("views", {})
    logger.info(
        "Graph projection rebuilt",
        extra={
            "action": "graph.projection.rebuilt",
            "provider": result["provider"],
            "outcome": "success",
            "duration_ms": round((time.monotonic() - started) * 1000, 2),
            "graph_node_count": result["nodes"],
            "graph_edge_count": result["edges"],
            "hierarchy_node_count": views.get("hierarchy", {}).get("nodes", 0),
            "hierarchy_edge_count": views.get("hierarchy", {}).get("edges", 0),
        },
    )
    mark_projection_rebuilt(db, target="graph")
    return result


@router.get("/projections")
def projections(db: Session = Depends(get_db)) -> list[dict]:
    """Report which derived projections are behind the canonical graph."""

    return projection_status(db)

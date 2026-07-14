from collections import deque
from datetime import UTC, datetime
from typing import Protocol

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import CollectorSource, KnowledgeGap, ResearchItem, ResearchRelation
from app.schemas.graph import GraphEdge, GraphMeta, GraphNode, GraphQuery, GraphResponse


def graph_key(node_type: str, label: str) -> str:
    normalized = "-".join(label.casefold().split())
    prefix = "tag" if node_type == "Concept" else node_type.casefold()
    return f"{prefix}:{normalized}"


def _classification(item: ResearchItem) -> dict:
    value = (item.metadata_json or {}).get("classification", {})
    return value if isinstance(value, dict) else {}


def graph_projection(db: Session) -> dict[str, list[dict]]:
    """Build the rebuildable PostgreSQL projection before response-level limiting."""
    items = list(
        db.scalars(
            select(ResearchItem)
            .options(selectinload(ResearchItem.tags))
            .where(ResearchItem.status == "approved")
        )
    )
    item_ids = {item.id for item in items}
    nodes: dict[str, dict] = {}
    edges: dict[str, dict] = {}

    def add_taxonomy(item: ResearchItem, values: list[str], node_type: str, edge_type: str) -> None:
        for label in values:
            if not isinstance(label, str) or not label.strip():
                continue
            label = label.strip()
            node_id = graph_key(node_type, label)
            current = nodes.setdefault(
                node_id,
                {
                    "id": node_id,
                    "label": label,
                    "type": node_type,
                    "summary": "",
                    "confidence": 1,
                    "source_count": 0,
                    "published": True,
                },
            )
            current["source_count"] += 1
            edge_id = f"{item.id}:{edge_type.casefold()}:{node_id}"
            edges[edge_id] = {
                "id": edge_id,
                "source": item.id,
                "target": node_id,
                "type": edge_type,
                "confidence": _classification(item).get("confidence", 1),
                "evidence_count": 0,
            }

    source_ids: set[str] = set()
    for item in items:
        classification = _classification(item)
        source_type = (item.metadata_json or {}).get("source_type") or classification.get(
            "content_type"
        )
        nodes[item.id] = {
            "id": item.id,
            "label": item.title,
            "type": "ResearchItem",
            "summary": item.summary or "",
            "confidence": classification.get("confidence", 1),
            "source_count": 1,
            "published": True,
            "display_id": item.display_id,
            "source_type": source_type,
            "source_url": item.source_url,
            "created_at": item.created_at,
        }
        concept_values = [tag.display_name for tag in item.tags]
        concept_values.extend(classification.get("concepts", []))
        unique_concepts = list(
            {value.casefold(): value for value in concept_values if isinstance(value, str)}.values()
        )
        add_taxonomy(item, unique_concepts, "Concept", "RESEARCHES")
        add_taxonomy(item, classification.get("technologies", []), "Technology", "USES_TECH")
        add_taxonomy(
            item,
            classification.get("agent_patterns", []),
            "AgentPattern",
            "IMPLEMENTS_PATTERN",
        )
        add_taxonomy(
            item,
            classification.get("business_domains", []),
            "BusinessDomain",
            "APPLIES_TO",
        )
        for author in item.authors or []:
            if not author.strip():
                continue
            node_id = graph_key("Person", author)
            current = nodes.setdefault(
                node_id,
                {
                    "id": node_id,
                    "label": author,
                    "type": "Person",
                    "summary": "",
                    "confidence": 1,
                    "source_count": 0,
                    "published": True,
                },
            )
            current["source_count"] += 1
            edge_id = f"{item.id}:author:{node_id}"
            edges[edge_id] = {
                "id": edge_id,
                "source": item.id,
                "target": node_id,
                "type": "AUTHORED_BY",
                "confidence": 1,
                "evidence_count": 0,
            }
        collector_source_id = (item.metadata_json or {}).get("collector_source_id")
        if isinstance(collector_source_id, str):
            source_ids.add(collector_source_id)
            node_id = f"source:{collector_source_id}"
            edge_id = f"{item.id}:collected-from:{node_id}"
            edges[edge_id] = {
                "id": edge_id,
                "source": item.id,
                "target": node_id,
                "type": "COLLECTED_FROM",
                "confidence": 1,
                "evidence_count": 0,
            }

    if item_ids:
        relations = db.scalars(
            select(ResearchRelation).where(
                ResearchRelation.source_id.in_(item_ids), ResearchRelation.target_id.in_(item_ids)
            )
        )
        for relation in relations:
            evidence = []
            if relation.reasoning:
                evidence.append({"text": relation.reasoning})
            edges[relation.id] = {
                "id": relation.id,
                "source": relation.source_id,
                "target": relation.target_id,
                "type": relation.relation_type.upper(),
                "confidence": relation.confidence if relation.confidence is not None else 1,
                "evidence_count": len(evidence),
                "evidence": evidence,
            }

    if source_ids:
        sources = db.scalars(select(CollectorSource).where(CollectorSource.id.in_(source_ids)))
        for source in sources:
            node_id = f"source:{source.id}"
            nodes[node_id] = {
                "id": node_id,
                "label": source.name,
                "type": "CollectorSource",
                "summary": f"{source.type.upper()} collector source",
                "confidence": 1,
                "source_count": 1,
                "published": True,
                "source_type": source.type,
                "source_url": source.url,
            }

    for gap in db.scalars(select(KnowledgeGap)):
        node_id = f"gap:{gap.id}"
        nodes[node_id] = {
            "id": node_id,
            "label": gap.title,
            "type": "ResearchGap",
            "summary": gap.reason,
            "confidence": 1,
            "source_count": gap.coverage_count,
            "published": True,
            "status": gap.status,
            "priority": gap.priority,
        }
        if gap.deep_research_id and gap.deep_research_id in item_ids:
            edge_id = f"{gap.deep_research_id}:fills:{node_id}"
            edges[edge_id] = {
                "id": edge_id,
                "source": gap.deep_research_id,
                "target": node_id,
                "type": "FILLS_GAP",
                "confidence": 1,
                "evidence_count": 0,
            }

    # A source row may have disappeared; invalid projection edges are removed before validation.
    edges = {
        edge_id: edge
        for edge_id, edge in edges.items()
        if edge["source"] in nodes and edge["target"] in nodes and edge["source"] != edge["target"]
    }
    degree: dict[str, int] = {}
    for edge in edges.values():
        degree[edge["source"]] = degree.get(edge["source"], 0) + 1
        degree[edge["target"]] = degree.get(edge["target"], 0) + 1
    for node in nodes.values():
        node["degree"] = degree.get(node["id"], 0)
    return {"nodes": list(nodes.values()), "edges": list(edges.values())}


def _reachable_ids(graph: dict, root: str, depth: int) -> set[str]:
    node_ids = {node["id"] for node in graph["nodes"]}
    if root not in node_ids:
        raise HTTPException(404, "Graph node not found")
    adjacency: dict[str, set[str]] = {}
    for edge in graph["edges"]:
        adjacency.setdefault(edge["source"], set()).add(edge["target"])
        adjacency.setdefault(edge["target"], set()).add(edge["source"])
    reached = {root}
    frontier = {root}
    for _ in range(depth):
        frontier = {neighbor for node_id in frontier for neighbor in adjacency.get(node_id, set())}
        frontier -= reached
        reached |= frontier
        if not frontier:
            break
    return reached


def filter_graph(graph: dict, query: GraphQuery, provider_name: str) -> GraphResponse:
    node_limit = min(query.limit, settings.graph_max_node_limit)
    edge_limit = settings.graph_max_edge_limit
    allowed_ids = (
        _reachable_ids(graph, query.root_node_id, query.depth) if query.root_node_id else None
    )
    needle = query.query.casefold().strip() if query.query else ""

    def comparable(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    def matches(node: dict) -> bool:
        if allowed_ids is not None and node["id"] not in allowed_ids:
            return False
        if query.node_types and node["type"] not in query.node_types:
            return False
        if query.source_types and node.get("source_type") not in query.source_types:
            return False
        if float(node.get("confidence", 1)) < query.min_confidence:
            return False
        created_at = node.get("created_at")
        if query.date_from and (
            not created_at or comparable(created_at) < comparable(query.date_from)
        ):
            return False
        if query.date_to and (
            not created_at or comparable(created_at) > comparable(query.date_to)
        ):
            return False
        searchable = f"{node.get('label', '')} {node.get('summary', '')}".casefold()
        return not needle or needle in searchable

    candidates = [node for node in graph["nodes"] if matches(node)]
    candidates.sort(
        key=lambda node: (
            node["id"] != query.root_node_id,
            -int(node.get("degree", 0)),
            node.get("label", "").casefold(),
        )
    )
    selected = candidates[:node_limit]
    selected_ids = {node["id"] for node in selected}
    edge_candidates = [
        edge
        for edge in graph["edges"]
        if edge["source"] in selected_ids
        and edge["target"] in selected_ids
        and float(edge.get("confidence", 1)) >= query.min_confidence
    ]
    selected_edges = edge_candidates[:edge_limit]
    truncated = len(candidates) > node_limit or len(edge_candidates) > edge_limit
    nodes = [GraphNode.model_validate(node) for node in selected]
    edges = [GraphEdge.model_validate(edge) for edge in selected_edges]
    return GraphResponse(
        nodes=nodes,
        edges=edges,
        meta=GraphMeta(
            node_count=len(nodes),
            edge_count=len(edges),
            query=query.query,
            truncated=truncated,
            provider=provider_name,
        ),
    )


class GraphRepository(Protocol):
    name: str

    def query(self, db: Session, query: GraphQuery) -> GraphResponse: ...


class PostgresGraphRepository:
    name = "postgres"

    def query(self, db: Session, query: GraphQuery) -> GraphResponse:
        return filter_graph(graph_projection(db), query, self.name)


class MockGraphRepository:
    name = "mock"

    def query(self, db: Session, query: GraphQuery) -> GraphResponse:
        del db
        return filter_graph({"nodes": [], "edges": []}, query, self.name)


class Neo4jGraphRepository:
    name = "neo4j"

    def query(self, db: Session, query: GraphQuery) -> GraphResponse:
        del db, query
        if not settings.neo4j_uri:
            raise HTTPException(503, "Neo4j graph provider is selected but not configured")
        raise HTTPException(501, "Neo4j projection adapter is configured but not implemented yet")


def graph_repository() -> GraphRepository:
    providers: dict[str, GraphRepository] = {
        "postgres": PostgresGraphRepository(),
        "mock": MockGraphRepository(),
        "neo4j": Neo4jGraphRepository(),
    }
    repository = providers.get(settings.graph_data_provider.casefold())
    if repository is None:
        raise HTTPException(500, f"Unsupported graph provider: {settings.graph_data_provider}")
    return repository


def graph_clusters(graph: GraphResponse | dict) -> list[dict]:
    raw = graph.model_dump() if isinstance(graph, GraphResponse) else graph
    adjacency: dict[str, set[str]] = {node["id"]: set() for node in raw["nodes"]}
    for edge in raw["edges"]:
        adjacency.setdefault(edge["source"], set()).add(edge["target"])
        adjacency.setdefault(edge["target"], set()).add(edge["source"])
    remaining = set(adjacency)
    clusters: list[dict] = []
    while remaining:
        root = remaining.pop()
        members = {root}
        queue = [root]
        while queue:
            current = queue.pop()
            unseen = adjacency.get(current, set()) & remaining
            remaining -= unseen
            members |= unseen
            queue.extend(unseen)
        clusters.append(
            {"id": len(clusters) + 1, "node_ids": sorted(members), "size": len(members)}
        )
    return sorted(clusters, key=lambda value: value["size"], reverse=True)


def ego_graph(graph: GraphResponse | dict, node_id: str) -> dict:
    raw = graph.model_dump() if isinstance(graph, GraphResponse) else graph
    if not any(node["id"] == node_id for node in raw["nodes"]):
        raise HTTPException(404, "Graph node not found")
    edges = [edge for edge in raw["edges"] if node_id in {edge["source"], edge["target"]}]
    ids = {node_id, *(edge["source"] for edge in edges), *(edge["target"] for edge in edges)}
    return {"nodes": [node for node in raw["nodes"] if node["id"] in ids], "edges": edges}


def shortest_path(graph: GraphResponse | dict, source: str, target: str) -> dict:
    raw = graph.model_dump() if isinstance(graph, GraphResponse) else graph
    adjacency: dict[str, list[tuple[str, dict]]] = {}
    for edge in raw["edges"]:
        adjacency.setdefault(edge["source"], []).append((edge["target"], edge))
        adjacency.setdefault(edge["target"], []).append((edge["source"], edge))
    queue = deque([(source, [source], [])])
    visited = {source}
    while queue:
        current, nodes, edges = queue.popleft()
        if current == target:
            return {"node_ids": nodes, "edges": edges}
        for neighbor, edge in adjacency.get(current, []):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, [*nodes, neighbor], [*edges, edge]))
    raise HTTPException(404, "No graph path found")

from collections import deque
from datetime import UTC, datetime
from typing import Protocol

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.models import (
    CollectorSource,
    ConceptAlias,
    KnowledgeEdge,
    KnowledgeGap,
    KnowledgeNode,
    ResearchItem,
    ResearchRelation,
)
from app.schemas.graph import GraphEdge, GraphMeta, GraphNode, GraphQuery, GraphResponse
from app.services.neo4j_projection import Neo4jProjectionClient
from app.services.ontology import normalize_ontology_key


def graph_key(node_type: str, label: str) -> str:
    normalized = "-".join(label.casefold().split())
    prefix = "tag" if node_type == "Concept" else node_type.casefold()
    return f"{prefix}:{normalized}"


def _classification(item: ResearchItem) -> dict:
    value = (item.metadata_json or {}).get("classification", {})
    return value if isinstance(value, dict) else {}


def canonical_node_index(db: Session) -> dict[tuple[str, str], KnowledgeNode]:
    """Index approved ontology nodes by (type, normalized key), including their aliases.

    The relationship view derives its taxonomy nodes from free-text classifier output while
    the hierarchy view reads canonical records. Without this index the same concept appears
    as two unrelated nodes — one per view — and selecting it in one view loses it in the
    other.
    """

    index: dict[tuple[str, str], KnowledgeNode] = {}
    nodes = list(
        db.scalars(select(KnowledgeNode).where(KnowledgeNode.lifecycle_status == "approved"))
    )
    by_id = {node.id: node for node in nodes}
    for node in nodes:
        index[(node.node_type, node.normalized_key)] = node
    aliases = db.scalars(select(ConceptAlias).where(ConceptAlias.lifecycle_status == "approved"))
    for alias in aliases:
        node = by_id.get(alias.knowledge_node_id)
        # An alias never overrides a canonical label that already claims the same key.
        if node is not None:
            index.setdefault((node.node_type, alias.normalized_alias), node)
    return index


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

    canonical = canonical_node_index(db)
    canonical_nodes = list(
        db.scalars(
            select(KnowledgeNode).where(
                KnowledgeNode.lifecycle_status == "approved",
                KnowledgeNode.node_type.notin_(("SystemRoot", "SystemPillar")),
            )
        )
    )
    canonical_ids = {node.id for node in canonical_nodes}
    aliases_by_node: dict[str, list[str]] = {}
    if canonical_ids:
        for alias in db.scalars(
            select(ConceptAlias).where(
                ConceptAlias.knowledge_node_id.in_(canonical_ids),
                ConceptAlias.lifecycle_status == "approved",
            )
        ):
            aliases_by_node.setdefault(alias.knowledge_node_id, []).append(alias.alias)
    for node in canonical_nodes:
        nodes[node.id] = {
            "id": node.id,
            "label": node.canonical_label,
            "type": node.node_type,
            "summary": node.description,
            "confidence": 1,
            "source_count": 0,
            "published": True,
            "canonical_node_id": node.id,
            "primary_parent_id": node.primary_parent_id,
            "aliases": aliases_by_node.get(node.id, []),
            "lifecycle_status": node.lifecycle_status,
            "provenance": {
                "created_by_type": node.created_by_type,
                "created_by_ref": node.created_by_ref or "",
            },
        }

    def add_taxonomy(item: ResearchItem, values: list[str], node_type: str, edge_type: str) -> None:
        for label in values:
            if not isinstance(label, str) or not label.strip():
                continue
            label = label.strip()
            match = canonical.get((node_type, normalize_ontology_key(label)))
            # Adopt the canonical identity when one exists so the concept is a single node
            # across both views, and keep the classifier's wording as an alias.
            node_id = match.id if match is not None else graph_key(node_type, label)
            current = nodes.setdefault(
                node_id,
                {
                    "id": node_id,
                    "label": match.canonical_label if match is not None else label,
                    "type": node_type,
                    "summary": match.description if match is not None else "",
                    "confidence": 1,
                    "source_count": 0,
                    "published": True,
                    "canonical_node_id": match.id if match is not None else None,
                    "primary_parent_id": match.primary_parent_id if match is not None else None,
                    "aliases": [],
                },
            )
            if match is not None and label != match.canonical_label:
                aliases = current.setdefault("aliases", [])
                if label not in aliases:
                    aliases.append(label)
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

    if canonical_ids:
        canonical_edges = db.scalars(
            select(KnowledgeEdge).where(
                KnowledgeEdge.lifecycle_status == "approved",
                KnowledgeEdge.source_node_id.in_(canonical_ids),
                KnowledgeEdge.target_node_id.in_(canonical_ids),
            )
        )
        for edge in canonical_edges:
            edges[edge.id] = {
                "id": edge.id,
                "source": edge.source_node_id,
                "target": edge.target_node_id,
                "type": edge.edge_type,
                "confidence": edge.confidence,
                "evidence_count": 0,
                "evidence": [],
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


def ontology_graph_projection(db: Session) -> dict[str, list[dict]]:
    """Build the canonical ontology hierarchy from approved PostgreSQL knowledge records."""
    ontology_nodes = list(
        db.scalars(
            select(KnowledgeNode)
            .where(KnowledgeNode.lifecycle_status == "approved")
            .order_by(KnowledgeNode.canonical_label)
        )
    )
    node_ids = {node.id for node in ontology_nodes}
    children: dict[str, int] = {}
    for node in ontology_nodes:
        if node.primary_parent_id in node_ids:
            children[node.primary_parent_id] = children.get(node.primary_parent_id, 0) + 1

    nodes = [
        {
            "id": node.id,
            "label": node.canonical_label,
            "type": node.node_type,
            "summary": node.description,
            "confidence": 1,
            "source_count": 0,
            "published": True,
            "primary_parent_id": node.primary_parent_id,
            "child_count": children.get(node.id, 0),
            "lifecycle_status": node.lifecycle_status,
            "provenance": {
                "created_by_type": node.created_by_type,
                "created_by_ref": node.created_by_ref or "",
            },
            "degree": children.get(node.id, 0) + (1 if node.primary_parent_id else 0),
        }
        for node in ontology_nodes
    ]
    edges: list[dict] = [
        {
            "id": f"hierarchy:{node.primary_parent_id}:{node.id}",
            "source": node.primary_parent_id,
            "target": node.id,
            "type": "PARENT_OF",
            "confidence": 1,
            "evidence_count": 0,
        }
        for node in ontology_nodes
        if node.primary_parent_id in node_ids
    ]
    secondary_edges = db.scalars(
        select(KnowledgeEdge).where(
            KnowledgeEdge.lifecycle_status == "approved",
            KnowledgeEdge.edge_type.in_(("PARENT_OF", "BROADER_THAN")),
        )
    )
    existing_edge_keys = {(edge["source"], edge["target"], edge["type"]) for edge in edges}
    for edge in secondary_edges:
        if (
            (edge.source_node_id, edge.target_node_id, edge.edge_type) in existing_edge_keys
            or edge.source_node_id not in node_ids
            or edge.target_node_id not in node_ids
        ):
            continue
        edges.append(
            {
                "id": edge.id,
                "source": edge.source_node_id,
                "target": edge.target_node_id,
                "type": edge.edge_type,
                "confidence": edge.confidence,
                "evidence_count": 0,
            }
        )
    return {"nodes": nodes, "edges": edges}


HIERARCHY_MEMBERSHIP_PRIORITY = {
    "RESEARCHES": 0,
    "IMPLEMENTS_PATTERN": 1,
    "USES_TECH": 2,
    "APPLIES_TO": 3,
    "AUTHORED_BY": 4,
    "COLLECTED_FROM": 5,
    "FILLS_GAP": 6,
}


def knowledge_hierarchy_projection(db: Session) -> dict[str, list[dict]]:
    """Render the approved relationship corpus as a deterministic hierarchy forest.

    Relationship membership runs from research -> taxonomy in the network. Hierarchy presentation
    reverses that direction so a concept/technology/pattern/domain/source becomes the parent of the
    research it describes. A node receives one deterministic display parent; non-hierarchical
    cross-relations remain available in relationship view. The node corpus is intentionally
    identical between the two views.
    """

    relationship = graph_projection(db)
    nodes = [dict(node) for node in relationship["nodes"]]
    by_id = {node["id"]: node for node in nodes}
    parent_candidates: dict[str, list[tuple[int, str, dict]]] = {}

    for node in nodes:
        parent_id = node.get("primary_parent_id")
        if parent_id in by_id:
            parent_candidates.setdefault(node["id"], []).append(
                (-1, str(parent_id), {"type": "PARENT_OF", "confidence": 1})
            )

    for edge in relationship["edges"]:
        priority = HIERARCHY_MEMBERSHIP_PRIORITY.get(str(edge.get("type")))
        if priority is None:
            continue
        child_id = edge["source"]
        parent_id = edge["target"]
        if child_id not in by_id or parent_id not in by_id or child_id == parent_id:
            continue
        parent_candidates.setdefault(child_id, []).append((priority, parent_id, edge))

    hierarchy_edges: list[dict] = []
    children: dict[str, int] = {}
    for child_id, candidates in parent_candidates.items():
        priority, parent_id, source_edge = min(
            candidates,
            key=lambda candidate: (
                candidate[0],
                by_id[candidate[1]].get("label", "").casefold(),
                candidate[1],
            ),
        )
        del priority
        by_id[child_id]["primary_parent_id"] = parent_id
        children[parent_id] = children.get(parent_id, 0) + 1
        hierarchy_edges.append(
            {
                "id": f"knowledge-hierarchy:{parent_id}:{child_id}",
                "source": parent_id,
                "target": child_id,
                "type": "PARENT_OF",
                "confidence": source_edge.get("confidence", 1),
                "evidence_count": source_edge.get("evidence_count", 0),
                "evidence": source_edge.get("evidence", []),
            }
        )

    for node in nodes:
        node["child_count"] = children.get(node["id"], 0)
        node["degree"] = children.get(node["id"], 0) + (
            1 if node.get("primary_parent_id") in by_id else 0
        )
    return {"nodes": nodes, "edges": hierarchy_edges}


def _reachable_ids(graph: dict, root: str, depth: int, *, directed: bool = False) -> set[str]:
    node_ids = {node["id"] for node in graph["nodes"]}
    if root not in node_ids:
        raise HTTPException(404, "Graph node not found")
    adjacency: dict[str, set[str]] = {}
    for edge in graph["edges"]:
        adjacency.setdefault(edge["source"], set()).add(edge["target"])
        if not directed:
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
        _reachable_ids(
            graph,
            query.root_node_id,
            query.depth,
            directed=query.view == "hierarchy",
        )
        if query.root_node_id
        else None
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
        if query.date_to and (not created_at or comparable(created_at) > comparable(query.date_to)):
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
            view=query.view,
            total_node_count=len(candidates),
            total_edge_count=len(edge_candidates),
            node_limit=node_limit,
        ),
    )


class GraphRepository(Protocol):
    name: str

    def query(self, db: Session, query: GraphQuery) -> GraphResponse: ...

    def rebuild(self, db: Session) -> dict[str, object]: ...

    def path(self, db: Session, source: str, target: str) -> dict: ...

    def clusters(self, db: Session) -> list[dict]: ...


class PostgresGraphRepository:
    name = "postgres"

    def query(self, db: Session, query: GraphQuery) -> GraphResponse:
        projection = (
            knowledge_hierarchy_projection(db)
            if query.view == "hierarchy"
            else graph_projection(db)
        )
        return filter_graph(projection, query, self.name)

    def rebuild(self, db: Session) -> dict[str, object]:
        relationship = graph_projection(db)
        hierarchy = knowledge_hierarchy_projection(db)
        return {
            "status": "rebuilt",
            "provider": self.name,
            "nodes": len(relationship["nodes"]),
            "edges": len(relationship["edges"]),
            "views": {
                "relationship": {
                    "nodes": len(relationship["nodes"]),
                    "edges": len(relationship["edges"]),
                },
                "hierarchy": {
                    "nodes": len(hierarchy["nodes"]),
                    "edges": len(hierarchy["edges"]),
                },
            },
        }

    def path(self, db: Session, source: str, target: str) -> dict:
        return shortest_path(graph_projection(db), source, target)

    def clusters(self, db: Session) -> list[dict]:
        return graph_clusters(graph_projection(db))


class MockGraphRepository:
    name = "mock"

    def query(self, db: Session, query: GraphQuery) -> GraphResponse:
        del db
        return filter_graph({"nodes": [], "edges": []}, query, self.name)

    def rebuild(self, db: Session) -> dict[str, object]:
        del db
        return {
            "status": "rebuilt",
            "provider": self.name,
            "nodes": 0,
            "edges": 0,
            "views": {
                "relationship": {"nodes": 0, "edges": 0},
                "hierarchy": {"nodes": 0, "edges": 0},
            },
        }

    def path(self, db: Session, source: str, target: str) -> dict:
        del db
        return shortest_path({"nodes": [], "edges": []}, source, target)

    def clusters(self, db: Session) -> list[dict]:
        del db
        return []


class Neo4jGraphRepository:
    name = "neo4j"

    def query(self, db: Session, query: GraphQuery) -> GraphResponse:
        del db
        return Neo4jProjectionClient.from_settings().query(query)

    def rebuild(self, db: Session) -> dict[str, object]:
        relationship = graph_projection(db)
        hierarchy = knowledge_hierarchy_projection(db)
        views = Neo4jProjectionClient.from_settings().rebuild(relationship, hierarchy)
        return {
            "status": "rebuilt",
            "provider": self.name,
            "nodes": views["relationship"]["nodes"],
            "edges": views["relationship"]["edges"],
            "views": views,
        }

    def path(self, db: Session, source: str, target: str) -> dict:
        del db
        return Neo4jProjectionClient.from_settings().shortest_path(source, target)

    def clusters(self, db: Session) -> list[dict]:
        response = self.query(
            db,
            GraphQuery(limit=settings.graph_max_node_limit),
        )
        return graph_clusters(response)


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

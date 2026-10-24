from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ConceptAlias, KnowledgeEdge, KnowledgeNode
from app.schemas.system import GraphInvariantReport
from app.services.ontology import ROOT_KEY, ontology_id


def _duplicates(values: list[tuple[str, ...]]) -> set[tuple[str, ...]]:
    seen: set[tuple[str, ...]] = set()
    duplicates: set[tuple[str, ...]] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def check_graph_invariants(db: Session) -> GraphInvariantReport:
    nodes = list(db.scalars(select(KnowledgeNode)))
    edges = list(db.scalars(select(KnowledgeEdge)))
    aliases = list(db.scalars(select(ConceptAlias)))
    node_by_id = {node.id: node for node in nodes}
    errors: list[str] = []

    expected_root = node_by_id.get(ontology_id(ROOT_KEY))
    approved_roots = [
        node
        for node in nodes
        if node.lifecycle_status == "approved"
        and node.node_type == "SystemRoot"
        and node.primary_parent_id is None
    ]
    if expected_root is None or expected_root.lifecycle_status != "approved":
        errors.append("Canonical Business AI Agents root is missing or not approved")
    if len(approved_roots) != 1:
        errors.append(f"Expected one approved SystemRoot, found {len(approved_roots)}")

    duplicate_nodes = _duplicates(
        [(node.node_type, node.normalized_key) for node in nodes]
    )
    if duplicate_nodes:
        errors.append(f"Duplicate normalized knowledge nodes: {len(duplicate_nodes)}")

    for node in nodes:
        if node.primary_parent_id is not None and node.primary_parent_id not in node_by_id:
            errors.append(f"Node {node.id} has a dangling primary parent")
        visited: set[str] = set()
        current_id: str | None = node.id
        while current_id is not None:
            if current_id in visited:
                errors.append(f"Hierarchy cycle detected from node {node.id}")
                break
            visited.add(current_id)
            current = node_by_id.get(current_id)
            current_id = current.primary_parent_id if current is not None else None

    duplicate_edges = _duplicates(
        [
            (
                edge.source_node_id,
                edge.target_node_id,
                edge.edge_type,
                edge.lifecycle_status,
            )
            for edge in edges
        ]
    )
    if duplicate_edges:
        errors.append(f"Duplicate knowledge edges: {len(duplicate_edges)}")
    for edge in edges:
        if edge.source_node_id not in node_by_id or edge.target_node_id not in node_by_id:
            errors.append(f"Edge {edge.id} has a dangling endpoint")
        if edge.source_node_id == edge.target_node_id:
            errors.append(f"Edge {edge.id} is a self-loop")
        if not 0 <= edge.confidence <= 1:
            errors.append(f"Edge {edge.id} has invalid confidence")

    duplicate_aliases = _duplicates(
        [(alias.normalized_alias, alias.language) for alias in aliases]
    )
    if duplicate_aliases:
        errors.append(f"Duplicate normalized aliases: {len(duplicate_aliases)}")
    for alias in aliases:
        if alias.knowledge_node_id not in node_by_id:
            errors.append(f"Alias {alias.id} has a dangling knowledge node")

    return GraphInvariantReport(
        valid=not errors,
        checked_nodes=len(nodes),
        checked_edges=len(edges),
        checked_aliases=len(aliases),
        errors=sorted(set(errors)),
    )

from __future__ import annotations

import json

from neo4j import GraphDatabase
from sqlalchemy import func, select

from app.core.config import settings
from app.db import SessionLocal
from app.models import KnowledgeEdge, KnowledgeNode, ResearchItem, ResearchRelation
from app.schemas.graph import GraphQuery
from app.services.graph import graph_projection, ontology_graph_projection
from app.services.neo4j_projection import Neo4jProjectionClient


def canonical_counts(db) -> tuple[int, int, int, int]:
    return (
        db.scalar(select(func.count()).select_from(ResearchItem)) or 0,
        db.scalar(select(func.count()).select_from(ResearchRelation)) or 0,
        db.scalar(select(func.count()).select_from(KnowledgeNode)) or 0,
        db.scalar(select(func.count()).select_from(KnowledgeEdge)) or 0,
    )


def scalar(driver, query: str, **parameters) -> int:
    records, _, _ = driver.execute_query(query, database_=settings.neo4j_database, **parameters)
    return int(records[0][0])


def main() -> None:
    projection_client = Neo4jProjectionClient.from_settings()
    with SessionLocal() as db:
        canonical_before = canonical_counts(db)
        relationship = graph_projection(db)
        hierarchy = ontology_graph_projection(db)

        first = projection_client.rebuild(relationship, hierarchy)
        second = projection_client.rebuild(relationship, hierarchy)
        if first != second:
            raise RuntimeError("Repeated Neo4j projection counts do not match")

        password = settings.neo4j_password
        assert password is not None
        with GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, password.get_secret_value()),
        ) as driver:
            driver.execute_query(
                """
                MERGE (node:ResearchProjectionNode {
                  projection: 'relationship',
                  graph_id: 'stale-runtime-proof'
                })
                SET node.sync_id = 'stale-runtime-proof'
                """,
                database_=settings.neo4j_database,
            )

            third = projection_client.rebuild(relationship, hierarchy)
            if third != first:
                raise RuntimeError("Neo4j stale-prune rebuild counts do not match")
            stale_count = scalar(
                driver,
                """
                MATCH (node:ResearchProjectionNode {graph_id: $graph_id})
                RETURN count(node)
                """,
                graph_id="stale-runtime-proof",
            )
            duplicate_nodes = scalar(
                driver,
                """
                MATCH (node:ResearchProjectionNode)
                WITH node.projection AS projection, node.graph_id AS graph_id, count(*) AS copies
                WHERE copies > 1
                RETURN count(*)
                """,
            )
            duplicate_edges = scalar(
                driver,
                """
                MATCH ()-[edge:RESEARCH_PROJECTION_EDGE]->()
                WITH edge.projection AS projection, edge.graph_id AS graph_id, count(*) AS copies
                WHERE copies > 1
                RETURN count(*)
                """,
            )
            constraint_count = scalar(
                driver,
                """
                SHOW CONSTRAINTS
                YIELD name
                WHERE name IN [
                  'research_projection_node_identity',
                  'research_projection_edge_identity'
                ]
                RETURN count(*)
                """,
            )

        relationship_response = projection_client.query(
            GraphQuery(limit=settings.graph_max_node_limit)
        )
        hierarchy_response = projection_client.query(
            GraphQuery(view="hierarchy", limit=settings.graph_max_node_limit)
        )
        root_id = next(
            node["id"] for node in hierarchy["nodes"] if node.get("primary_parent_id") is None
        )
        branch = projection_client.query(
            GraphQuery(
                view="hierarchy",
                limit=settings.graph_max_node_limit,
                root_node_id=root_id,
                depth=1,
            )
        )
        first_edge = relationship["edges"][0]
        path = projection_client.shortest_path(first_edge["source"], first_edge["target"])
        canonical_after = canonical_counts(db)

    if stale_count or duplicate_nodes or duplicate_edges:
        raise RuntimeError("Neo4j projection contains stale or duplicate rows")
    if constraint_count != 2:
        raise RuntimeError("Neo4j projection constraints are missing")
    if canonical_before != canonical_after:
        raise RuntimeError("Canonical PostgreSQL counts changed during projection rebuild")
    if relationship_response.meta.provider != "neo4j":
        raise RuntimeError("Relationship projection was not read from Neo4j")
    if hierarchy_response.meta.provider != "neo4j" or not branch.nodes:
        raise RuntimeError("Hierarchy projection was not read from Neo4j")
    if path["node_ids"] != [first_edge["source"], first_edge["target"]]:
        raise RuntimeError("Neo4j shortest path did not preserve the projected edge")

    print(
        "NEO4J_PROJECTION_OK",
        json.dumps(
            {
                "views": first,
                "relationship_read_nodes": relationship_response.meta.node_count,
                "hierarchy_read_nodes": hierarchy_response.meta.node_count,
                "branch_nodes": branch.meta.node_count,
                "path_nodes": len(path["node_ids"]),
                "constraints": constraint_count,
                "duplicates": duplicate_nodes + duplicate_edges,
                "canonical_unchanged": True,
            },
            sort_keys=True,
        ),
    )


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.graph import GraphEdge, GraphMeta, GraphNode, GraphQuery, GraphResponse

NODE_LABEL = "ResearchProjectionNode"
EDGE_TYPE = "RESEARCH_PROJECTION_EDGE"
PROJECTION_VIEWS = ("relationship", "hierarchy")

NODE_CONSTRAINT = f"""
CREATE CONSTRAINT research_projection_node_identity IF NOT EXISTS
FOR (node:{NODE_LABEL})
REQUIRE (node.projection, node.graph_id) IS UNIQUE
"""
EDGE_CONSTRAINT = f"""
CREATE CONSTRAINT research_projection_edge_identity IF NOT EXISTS
FOR ()-[edge:{EDGE_TYPE}]-()
REQUIRE (edge.projection, edge.graph_id) IS UNIQUE
"""
UPSERT_NODES = f"""
UNWIND $rows AS row
MERGE (node:{NODE_LABEL} {{projection: $projection, graph_id: row.graph_id}})
SET node = row.properties
"""
DELETE_MOVED_EDGES = f"""
UNWIND $rows AS row
MATCH (source:{NODE_LABEL})-[edge:{EDGE_TYPE} {{
  projection: $projection,
  graph_id: row.graph_id
}}]->(target:{NODE_LABEL})
WHERE source.graph_id <> row.source OR target.graph_id <> row.target
DELETE edge
"""
UPSERT_EDGES = f"""
UNWIND $rows AS row
MATCH (source:{NODE_LABEL} {{projection: $projection, graph_id: row.source}})
MATCH (target:{NODE_LABEL} {{projection: $projection, graph_id: row.target}})
MERGE (source)-[edge:{EDGE_TYPE} {{
  projection: $projection,
  graph_id: row.graph_id
}}]->(target)
SET edge = row.properties
"""
PRUNE_EDGES = f"""
MATCH ()-[edge:{EDGE_TYPE} {{projection: $projection}}]->()
WHERE edge.sync_id IS NULL OR edge.sync_id <> $sync_id
DELETE edge
"""
PRUNE_NODES = f"""
MATCH (node:{NODE_LABEL} {{projection: $projection}})
WHERE node.sync_id IS NULL OR node.sync_id <> $sync_id
DETACH DELETE node
"""
COUNT_PROJECTION = f"""
MATCH (node:{NODE_LABEL} {{projection: $projection}})
WITH count(node) AS node_count
OPTIONAL MATCH ()-[edge:{EDGE_TYPE} {{projection: $projection}}]->()
RETURN node_count, count(edge) AS edge_count
"""


class GraphProjectionError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 503) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


@dataclass(slots=True)
class ProjectionRows:
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]


def _batches(rows: list[dict[str, Any]], size: int) -> Iterator[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _epoch(value: datetime | None) -> float | None:
    if value is None:
        return None
    return (value if value.tzinfo else value.replace(tzinfo=UTC)).timestamp()


def _json(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def projection_rows(
    projection: str, graph: dict[str, list[dict[str, Any]]], sync_id: str
) -> ProjectionRows:
    if projection not in PROJECTION_VIEWS:
        raise GraphProjectionError(
            "NEO4J_PROJECTION_INVALID", "The graph projection view is invalid."
        )
    try:
        nodes = [GraphNode.model_validate(node) for node in graph["nodes"]]
        edges = [GraphEdge.model_validate(edge) for edge in graph["edges"]]
        GraphResponse(
            nodes=nodes,
            edges=edges,
            meta=GraphMeta(
                node_count=len(nodes),
                edge_count=len(edges),
                provider="postgres",
                view=projection,
            ),
        )
    except (KeyError, TypeError, ValidationError, ValueError) as exc:
        raise GraphProjectionError(
            "NEO4J_PROJECTION_INVALID",
            "The PostgreSQL graph projection failed validation.",
        ) from exc

    node_rows: list[dict[str, Any]] = []
    for node in nodes:
        payload = node.model_dump(mode="json")
        properties = {
            "projection": projection,
            "graph_id": node.id,
            "node_type": node.type,
            "label": node.label,
            "summary": node.summary,
            "confidence": node.confidence,
            "source_type": node.source_type,
            "created_at_epoch": _epoch(node.created_at),
            "degree": node.degree,
            "payload_json": _json(payload),
            "sync_id": sync_id,
        }
        node_rows.append({"graph_id": node.id, "properties": properties})

    edge_rows: list[dict[str, Any]] = []
    for edge in edges:
        payload = edge.model_dump(mode="json")
        properties = {
            "projection": projection,
            "graph_id": edge.id,
            "edge_type": edge.type,
            "confidence": edge.confidence,
            "payload_json": _json(payload),
            "sync_id": sync_id,
        }
        edge_rows.append(
            {
                "graph_id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "properties": properties,
            }
        )
    return ProjectionRows(nodes=node_rows, edges=edge_rows)


class Neo4jProjectionClient:
    def __init__(
        self,
        *,
        uri: str,
        username: str,
        password: str,
        database: str,
        batch_size: int,
        connection_timeout: float,
        retry_timeout: float,
        driver_factory: Callable[..., Any] = GraphDatabase.driver,
    ) -> None:
        self.uri = uri
        self.username = username
        self.password = password
        self.database = database
        self.batch_size = max(1, min(batch_size, 5_000))
        self.connection_timeout = max(0.1, min(connection_timeout, 30))
        self.retry_timeout = max(0, min(retry_timeout, 60))
        self.driver_factory = driver_factory

    @classmethod
    def from_settings(cls) -> Neo4jProjectionClient:
        secret = settings.neo4j_password
        password = secret.get_secret_value().strip() if secret else ""
        uri = (settings.neo4j_uri or "").strip()
        username = (settings.neo4j_username or "").strip()
        if not uri or not username or not password:
            raise GraphProjectionError(
                "NEO4J_NOT_CONFIGURED",
                "Neo4j graph projection is selected but not configured.",
            )
        return cls(
            uri=uri,
            username=username,
            password=password,
            database=settings.neo4j_database,
            batch_size=settings.neo4j_batch_size,
            connection_timeout=settings.neo4j_connection_timeout_seconds,
            retry_timeout=settings.neo4j_retry_timeout_seconds,
        )

    def _driver(self):
        return self.driver_factory(
            self.uri,
            auth=(self.username, self.password),
            connection_timeout=self.connection_timeout,
            max_transaction_retry_time=self.retry_timeout,
        )

    def _ensure_constraints(self, session: Any) -> None:
        session.execute_write(lambda tx: tx.run(NODE_CONSTRAINT).consume())
        session.execute_write(lambda tx: tx.run(EDGE_CONSTRAINT).consume())

    def _replace_tx(
        self, tx: Any, rows_by_view: dict[str, ProjectionRows], sync_id: str
    ) -> None:
        for projection in PROJECTION_VIEWS:
            rows = rows_by_view[projection]
            for batch in _batches(rows.nodes, self.batch_size):
                tx.run(UPSERT_NODES, projection=projection, rows=batch).consume()
            for batch in _batches(rows.edges, self.batch_size):
                tx.run(DELETE_MOVED_EDGES, projection=projection, rows=batch).consume()
                tx.run(UPSERT_EDGES, projection=projection, rows=batch).consume()
            tx.run(PRUNE_EDGES, projection=projection, sync_id=sync_id).consume()
            tx.run(PRUNE_NODES, projection=projection, sync_id=sync_id).consume()

    def _counts_tx(self, tx: Any) -> dict[str, dict[str, int]]:
        counts: dict[str, dict[str, int]] = {}
        for projection in PROJECTION_VIEWS:
            record = tx.run(COUNT_PROJECTION, projection=projection).single(strict=True)
            counts[projection] = {
                "nodes": int(record["node_count"]),
                "edges": int(record["edge_count"]),
            }
        return counts

    def rebuild(
        self,
        relationship: dict[str, list[dict[str, Any]]],
        hierarchy: dict[str, list[dict[str, Any]]],
    ) -> dict[str, dict[str, int]]:
        sync_id = str(uuid.uuid4())
        rows_by_view = {
            "relationship": projection_rows("relationship", relationship, sync_id),
            "hierarchy": projection_rows("hierarchy", hierarchy, sync_id),
        }
        expected = {
            view: {"nodes": len(rows.nodes), "edges": len(rows.edges)}
            for view, rows in rows_by_view.items()
        }
        try:
            with self._driver() as driver:
                with driver.session(database=self.database) as session:
                    self._ensure_constraints(session)
                    session.execute_write(self._replace_tx, rows_by_view, sync_id)
                    actual = session.execute_read(self._counts_tx)
        except GraphProjectionError:
            raise
        except (DriverError, Neo4jError, OSError) as exc:
            raise GraphProjectionError(
                "NEO4J_UNAVAILABLE", "The Neo4j graph projection is unavailable."
            ) from exc
        if actual != expected:
            raise GraphProjectionError(
                "NEO4J_PROJECTION_MISMATCH",
                "The Neo4j graph projection count check failed.",
            )
        return actual

    def _read_tx(self, tx: Any, query: GraphQuery) -> GraphResponse:
        projection = query.view
        if query.root_node_id:
            root_record = tx.run(
                f"""
                MATCH (root:{NODE_LABEL} {{
                  projection: $projection,
                  graph_id: $root_id
                }})
                RETURN count(root) AS root_count
                """,
                projection=projection,
                root_id=query.root_node_id,
            ).single(strict=True)
            if int(root_record["root_count"]) == 0:
                raise GraphProjectionError(
                    "GRAPH_NODE_NOT_FOUND", "Graph node not found.", status_code=404
                )

        node_limit = min(query.limit, settings.graph_max_node_limit)
        max_depth = max(1, min(settings.graph_max_depth, 10))
        depth = min(query.depth, max_depth)
        node_query = f"""
        MATCH (node:{NODE_LABEL} {{projection: $projection}})
        WHERE (
          $root_id IS NULL
          OR node.graph_id = $root_id
          OR EXISTS {{
            MATCH path=(root:{NODE_LABEL} {{
              projection: $projection,
              graph_id: $root_id
            }})-[:{EDGE_TYPE}*1..{max_depth}]-(node)
            WHERE length(path) <= $depth
              AND all(edge IN relationships(path) WHERE edge.projection = $projection)
          }}
        )
          AND (size($node_types) = 0 OR node.node_type IN $node_types)
          AND (size($source_types) = 0 OR node.source_type IN $source_types)
          AND node.confidence >= $min_confidence
          AND ($date_from IS NULL OR node.created_at_epoch >= $date_from)
          AND ($date_to IS NULL OR node.created_at_epoch <= $date_to)
          AND (
            $needle = ''
            OR toLower(node.label) CONTAINS $needle
            OR toLower(node.summary) CONTAINS $needle
          )
        RETURN node.graph_id AS graph_id, node.payload_json AS payload_json
        ORDER BY
          CASE WHEN node.graph_id = $root_id THEN 0 ELSE 1 END,
          node.degree DESC,
          toLower(node.label),
          node.graph_id
        LIMIT $fetch_limit
        """
        records = list(
            tx.run(
                node_query,
                projection=projection,
                root_id=query.root_node_id,
                depth=depth,
                node_types=sorted(query.node_types),
                source_types=sorted(query.source_types),
                min_confidence=query.min_confidence,
                date_from=_epoch(query.date_from),
                date_to=_epoch(query.date_to),
                needle=query.query.casefold().strip() if query.query else "",
                fetch_limit=node_limit + 1,
            )
        )
        node_truncated = len(records) > node_limit
        records = records[:node_limit]
        selected_ids = [str(record["graph_id"]) for record in records]

        edge_limit = settings.graph_max_edge_limit
        edge_records: list[Any] = []
        if selected_ids:
            edge_records = list(
                tx.run(
                    f"""
                    MATCH (source:{NODE_LABEL})-[edge:{EDGE_TYPE} {{
                      projection: $projection
                    }}]->(target:{NODE_LABEL})
                    WHERE source.projection = $projection
                      AND target.projection = $projection
                      AND source.graph_id IN $node_ids
                      AND target.graph_id IN $node_ids
                      AND edge.confidence >= $min_confidence
                    RETURN edge.payload_json AS payload_json
                    ORDER BY edge.graph_id
                    LIMIT $fetch_limit
                    """,
                    projection=projection,
                    node_ids=selected_ids,
                    min_confidence=query.min_confidence,
                    fetch_limit=edge_limit + 1,
                )
            )
        edge_truncated = len(edge_records) > edge_limit
        edge_records = edge_records[:edge_limit]
        try:
            nodes = [
                GraphNode.model_validate(json.loads(record["payload_json"]))
                for record in records
            ]
            edges = [
                GraphEdge.model_validate(json.loads(record["payload_json"]))
                for record in edge_records
            ]
            return GraphResponse(
                nodes=nodes,
                edges=edges,
                meta=GraphMeta(
                    node_count=len(nodes),
                    edge_count=len(edges),
                    query=query.query,
                    truncated=node_truncated or edge_truncated,
                    provider="neo4j",
                    view=query.view,
                ),
            )
        except (json.JSONDecodeError, TypeError, ValidationError, ValueError) as exc:
            raise GraphProjectionError(
                "NEO4J_PROJECTION_INVALID",
                "The Neo4j graph projection contains invalid data.",
            ) from exc

    def query(self, query: GraphQuery) -> GraphResponse:
        try:
            with self._driver() as driver:
                with driver.session(database=self.database) as session:
                    return session.execute_read(self._read_tx, query)
        except GraphProjectionError:
            raise
        except (DriverError, Neo4jError, OSError) as exc:
            raise GraphProjectionError(
                "NEO4J_UNAVAILABLE", "The Neo4j graph projection is unavailable."
            ) from exc

    def _path_tx(self, tx: Any, source: str, target: str) -> dict[str, Any]:
        max_hops = max(1, min(settings.graph_max_path_hops, 50))
        record = tx.run(
            f"""
            MATCH (source:{NODE_LABEL} {{
              projection: 'relationship',
              graph_id: $source
            }})
            MATCH (target:{NODE_LABEL} {{
              projection: 'relationship',
              graph_id: $target
            }})
            OPTIONAL MATCH path=shortestPath(
              (source)-[:{EDGE_TYPE}*1..{max_hops}]-(target)
            )
            RETURN
              CASE WHEN path IS NULL THEN NULL
                ELSE [node IN nodes(path) | node.graph_id]
              END AS node_ids,
              CASE WHEN path IS NULL THEN NULL
                ELSE [edge IN relationships(path) | edge.payload_json]
              END AS edge_payloads
            """,
            source=source,
            target=target,
        ).single()
        if record is None or record["node_ids"] is None:
            raise GraphProjectionError(
                "GRAPH_PATH_NOT_FOUND", "No graph path found.", status_code=404
            )
        try:
            edges = [
                GraphEdge.model_validate(json.loads(payload)).model_dump(mode="json")
                for payload in record["edge_payloads"]
            ]
        except (json.JSONDecodeError, TypeError, ValidationError, ValueError) as exc:
            raise GraphProjectionError(
                "NEO4J_PROJECTION_INVALID",
                "The Neo4j graph projection contains invalid data.",
            ) from exc
        return {"node_ids": list(record["node_ids"]), "edges": edges}

    def shortest_path(self, source: str, target: str) -> dict[str, Any]:
        try:
            with self._driver() as driver:
                with driver.session(database=self.database) as session:
                    return session.execute_read(self._path_tx, source, target)
        except GraphProjectionError:
            raise
        except (DriverError, Neo4jError, OSError) as exc:
            raise GraphProjectionError(
                "NEO4J_UNAVAILABLE", "The Neo4j graph projection is unavailable."
            ) from exc

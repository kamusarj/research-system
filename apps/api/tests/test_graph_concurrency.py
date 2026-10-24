from app.api.graph import GRAPH_READ_CACHE_CONTROL
from app.db import database_engine_options
from app.schemas.graph import GraphMeta, GraphNode, GraphResponse


def test_postgres_engine_uses_bounded_resilient_pool():
    options = database_engine_options("postgresql+psycopg://research@database/research")

    assert options == {
        "pool_size": 5,
        "max_overflow": 5,
        "pool_timeout": 30,
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }


def test_sqlite_keeps_thread_compatible_connection_options_only():
    assert database_engine_options("sqlite://") == {
        "connect_args": {"check_same_thread": False}
    }


def test_graph_reads_are_private_cacheable_and_compressed(client, monkeypatch):
    nodes = [
        GraphNode(
            id=f"node-{index}",
            type="Concept",
            label=f"Concurrent graph node {index}",
            summary="Bounded approved graph content " * 8,
        )
        for index in range(40)
    ]
    graph = GraphResponse(
        nodes=nodes,
        edges=[],
        meta=GraphMeta(
            node_count=len(nodes),
            edge_count=0,
            total_node_count=len(nodes),
            total_edge_count=0,
            node_limit=1000,
        ),
    )

    class Repository:
        def query(self, _db, _query):
            return graph

    monkeypatch.setattr("app.api.graph.graph_repository", lambda: Repository())
    response = client.get(
        "/api/v1/graph",
        params={"view": "relationship", "limit": 1000},
        headers={"Accept-Encoding": "gzip"},
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == GRAPH_READ_CACHE_CONTROL
    assert response.headers["vary"] == "Cookie, Authorization, Accept-Encoding"
    assert response.headers["content-encoding"] == "gzip"
    assert set(response.json()) == {"nodes", "edges", "meta"}
